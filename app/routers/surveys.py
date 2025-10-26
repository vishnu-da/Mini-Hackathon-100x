"""
Survey management endpoints.
"""
import logging
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional

from app.auth import get_current_user_id
from app.schemas.survey import (
    CreateSurveyRequest,
    UpdateSurveyRequest,
    VoiceConfigUpdate,
    SurveyResponse,
    SurveyListResponse
)
from app.services import survey_service
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=SurveyResponse, status_code=201)
async def create_survey(
    request: CreateSurveyRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Create a new survey from Google Form.

    Requires user to have Google OAuth connected.
    Fetches form structure and creates survey in draft status.
    """
    survey = await survey_service.create_survey(user_id, request)
    return survey


@router.get("", response_model=SurveyListResponse)
async def list_surveys(
    status: Optional[str] = Query(None, description="Filter by status (draft, active, closed)"),
    user_id: str = Depends(get_current_user_id)
):
    """
    List all surveys for the authenticated user.

    Optional status filter to show only surveys with specific status.
    """
    result = await survey_service.list_surveys(user_id, status)
    return result


@router.get("/{survey_id}", response_model=SurveyResponse)
async def get_survey(
    survey_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get a single survey by ID.

    Returns full survey data including questionnaire.
    User must own the survey.
    """
    survey = await survey_service.get_survey(survey_id, user_id)
    return survey


@router.put("/{survey_id}", response_model=SurveyResponse)
async def update_survey(
    survey_id: str,
    request: UpdateSurveyRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update survey details.

    Can update form URL, terms, voice config, etc.
    If form_url changes, will re-fetch form from Google Forms API.
    """
    survey = await survey_service.update_survey(survey_id, user_id, request)
    return survey


@router.put("/{survey_id}/voice-config", response_model=SurveyResponse)
async def update_voice_config(
    survey_id: str,
    config: VoiceConfigUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update voice agent configuration only.

    Updates tone, instructions, call duration, and retry attempts.
    """
    survey = await survey_service.update_voice_config(survey_id, user_id, config)
    return survey


@router.post("/{survey_id}/activate", response_model=SurveyResponse)
async def activate_survey(
    survey_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Activate a survey (change status from draft to active).

    Survey must have valid questionnaire and be in draft status.
    """
    survey = await survey_service.activate_survey(survey_id, user_id)
    return survey


@router.post("/{survey_id}/deactivate", response_model=SurveyResponse)
async def deactivate_survey(
    survey_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Deactivate a survey (change status to closed).

    Stops accepting new responses for this survey.
    """
    survey = await survey_service.deactivate_survey(survey_id, user_id)
    return survey


@router.delete("/{survey_id}")
async def delete_survey(
    survey_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Delete a survey and all related data.

    This action cannot be undone.
    CASCADE deletes will remove contacts and call logs.
    """
    success = await survey_service.delete_survey(survey_id, user_id)
    return {"success": success}


@router.get("/{survey_id}/export/csv")
async def export_survey_responses_csv(
    survey_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Export survey responses as CSV file.

    Generates a CSV file with all mapped responses from completed calls.
    Each row represents one participant, columns are questions.

    Args:
        survey_id: Survey ID to export
        user_id: Authenticated user ID

    Returns:
        CSV file download with survey responses
    """
    db = get_db()

    try:
        # 1. Verify survey exists and belongs to user
        survey_result = db.table("surveys").select("*").eq("survey_id", survey_id).eq("user_id", user_id).execute()

        if not survey_result.data:
            raise HTTPException(status_code=404, detail="Survey not found")

        survey = survey_result.data[0]
        survey_title = survey.get("json_questionnaire", {}).get("title", "Survey")

        # 2. Get all questions from survey
        questions = survey.get("json_questionnaire", {}).get("questions", [])

        if not questions:
            raise HTTPException(status_code=400, detail="Survey has no questions")

        # 3. Get all call logs with mapped responses
        call_logs_result = db.table("call_logs").select(
            "twilio_call_sid, contact_id, mapped_responses, created_at, call_duration, consent"
        ).eq("survey_id", survey_id).eq("status", "completed").execute()

        if not call_logs_result.data:
            raise HTTPException(status_code=404, detail="No completed responses found for this survey")

        call_logs = call_logs_result.data

        # 4. Get contact information
        contact_ids = [log["contact_id"] for log in call_logs]
        contacts_result = db.table("contacts").select("contact_id, participant_name, phone_number, email").in_(
            "contact_id", contact_ids
        ).execute()

        contacts_map = {c["contact_id"]: c for c in contacts_result.data}

        # 5. Build CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # CSV Headers: Participant Name, Phone, Email, Consent, Call Duration, Questions...
        headers = ["Participant Name", "Phone Number", "Email", "Consent", "Call Duration (s)", "Completed At"]
        headers.extend([q.get("question_text", f"Question {i+1}") for i, q in enumerate(questions)])
        writer.writerow(headers)

        # CSV Rows: One row per participant
        for log in call_logs:
            contact = contacts_map.get(log["contact_id"], {})
            mapped_responses = log.get("mapped_responses", [])

            # Create a map of question_id -> mapped_response
            response_map = {r.get("question_id"): r.get("mapped_response", "") for r in mapped_responses}

            # Build row
            row = [
                contact.get("participant_name", "Unknown"),
                contact.get("phone_number", ""),
                contact.get("email", ""),
                "Yes" if log.get("consent") else "No",
                log.get("call_duration", 0),
                log.get("created_at", "")
            ]

            # Add responses in question order
            for q in questions:
                q_id = q.get("question_id")
                row.append(response_map.get(q_id, ""))

            writer.writerow(row)

        # 6. Return CSV as downloadable file
        output.seek(0)

        filename = f"{survey_title.replace(' ', '_')}_responses.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting survey responses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export responses: {str(e)}")
