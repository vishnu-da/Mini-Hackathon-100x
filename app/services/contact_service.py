"""
Contact management service for uploading and managing survey participants.
"""
import logging
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, UploadFile
from io import BytesIO

from app.database import get_db
from app.services.survey_service import get_survey

logger = logging.getLogger(__name__)


async def upload_contacts(survey_id: str, user_id: str, csv_file: UploadFile) -> Dict[str, Any]:
    """
    Upload contacts from CSV file for a survey.

    Args:
        survey_id: Survey UUID
        user_id: User's UUID
        csv_file: Uploaded CSV file

    Returns:
        Dict with contacts_added count, upload_timestamp, and filename

    Raises:
        HTTPException: If validation fails or upload fails
    """
    db = get_db()

    # Step 1: Verify user owns survey
    logger.info(f"Uploading contacts for survey {survey_id}")
    await get_survey(survey_id, user_id)

    # Step 2: Delete existing contacts for this survey
    logger.info(f"Deleting existing contacts for survey {survey_id}")
    db.table("contact").delete().eq("survey_id", survey_id).execute()

    # Step 3: Parse CSV file
    try:
        contents = await csv_file.read()
        # Read phone_number as string to preserve + prefix
        df = pd.read_csv(BytesIO(contents), encoding='utf-8-sig', dtype={'phone_number': str})
    except Exception as e:
        logger.error(f"Failed to parse CSV: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {str(e)}")

    # Step 4: Validate CSV columns
    required_columns = ["phone_number"]
    optional_columns = ["participant_name", "participant_email"]

    if "phone_number" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain 'phone_number' column"
        )

    # Step 5: Validate and prepare contact data
    contacts = []
    upload_timestamp = datetime.now(timezone.utc)

    for index, row in df.iterrows():
        phone = str(row.get("phone_number", "")).strip()

        # Skip rows with empty phone numbers
        if not phone or phone == "nan":
            logger.warning(f"Skipping row {index}: empty phone number")
            continue

        participant_name = str(row.get("participant_name", "")).strip() if pd.notna(row.get("participant_name")) else None
        participant_email = str(row.get("participant_email", "")).strip() if pd.notna(row.get("participant_email")) else None

        # Make empty strings None
        if participant_name == "":
            participant_name = None
        if participant_email == "":
            participant_email = None

        contact = {
            "survey_id": survey_id,
            "phone_number": phone,
            "participant_name": participant_name,
            "participant_email": participant_email,
            "callback": "uploaded",
            "upload_filename": csv_file.filename
        }
        contacts.append(contact)

    if not contacts:
        raise HTTPException(
            status_code=400,
            detail="No valid contacts found in CSV file"
        )

    # Step 6: Bulk insert contacts
    logger.info(f"Inserting {len(contacts)} contacts for survey {survey_id}")

    try:
        response = db.table("contact").insert(contacts).execute()
    except Exception as e:
        logger.error(f"Failed to insert contacts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to insert contacts: {str(e)}")

    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to insert contacts")

    logger.info(f"Successfully uploaded {len(response.data)} contacts for survey {survey_id}")

    return {
        "contacts_added": len(contacts),
        "upload_timestamp": upload_timestamp,
        "filename": csv_file.filename
    }


async def get_contacts(survey_id: str, user_id: str) -> Dict[str, Any]:
    """
    Get all contacts for a survey.

    Args:
        survey_id: Survey UUID
        user_id: User's UUID

    Returns:
        Dict with contacts list and total count

    Raises:
        HTTPException: If survey not found or access denied
    """
    db = get_db()

    # Verify user owns survey
    await get_survey(survey_id, user_id)

    # Fetch contacts
    response = db.table("contact").select("*").eq("survey_id", survey_id).order("upload_timestamp", desc=True).execute()

    contacts = response.data if response.data else []

    return {
        "contacts": contacts,
        "total": len(contacts)
    }


async def create_callback_contact(survey_id: str, phone_number: str, name: Optional[str] = None) -> Dict[str, Any]:
    """
    Create or update callback contact for inbound "call me" requests.
    - If contact exists: update callback to "OptIn"
    - If contact doesn't exist: create new contact with callback "OptIn"

    Args:
        survey_id: Survey UUID
        phone_number: Participant's phone number
        name: Optional participant name

    Returns:
        Created or updated contact dict

    Raises:
        HTTPException: If validation fails
    """
    db = get_db()

    # Basic validation - just check not empty
    if not phone_number or not phone_number.strip():
        raise HTTPException(status_code=400, detail="Phone number is required")

    phone_number = phone_number.strip()

    # Check if contact already exists for this survey and phone number
    existing = db.table("contact").select("*").eq("survey_id", survey_id).eq("phone_number", phone_number).execute()

    if existing.data and len(existing.data) > 0:
        # Contact exists - update callback to OptIn
        contact_id = existing.data[0]["contact_id"]

        updated = db.table("contact").update({"callback": "OptIn"}).eq("contact_id", contact_id).execute()

        logger.info(f"Updated existing contact callback to OptIn for survey {survey_id}, phone {phone_number}")
        return updated.data[0] if updated.data else existing.data[0]

    # Contact doesn't exist - create new contact with OptIn
    contact_data = {
        "survey_id": survey_id,
        "phone_number": phone_number,
        "participant_name": name,
        "callback": "OptIn"
    }

    response = db.table("contact").insert(contact_data).execute()

    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create callback contact")

    logger.info(f"Created new callback contact (OptIn) for survey {survey_id}, phone {phone_number}")
    return response.data[0]
