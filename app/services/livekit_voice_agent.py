"""
LiveKit voice agent for conducting voice surveys.
Uses Deepgram for STT, Groq Llama 3.3 70B for LLM (ultra-fast), and Rime for TTS.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    function_tool,
    inference,
)
from livekit.plugins import deepgram, openai

from app.config import get_settings
from app.database import get_db

logger = logging.getLogger(__name__)
settings = get_settings()


class SurveyVoiceAgent(Agent):
    """
    Survey-specific voice agent that conducts voice surveys.

    Stores conversation transcript and responses in real-time.
    """

    def __init__(
        self,
        survey: Dict[str, Any],
        contact: Dict[str, Any],
        call_sid: str
    ):
        """
        Initialize survey voice agent.

        Args:
            survey: Survey data with questionnaire and settings
            contact: Contact information
            call_sid: Twilio call SID for tracking
        """
        self.survey = survey
        self.contact = contact
        self.call_sid = call_sid
        self.contact_id = contact.get("contact_id")
        self.survey_id = survey.get("survey_id")

        # Build system instructions from survey
        instructions = self._build_instructions(survey, contact)

        # Initialize parent Agent with instructions
        super().__init__(instructions=instructions)

        # Conversation tracking
        self.conversation_transcript = []
        self.raw_responses = []
        self.consent_given = False

        logger.info(f"Initialized SurveyVoiceAgent for survey {self.survey_id}, contact {self.contact_id}")

    def _build_instructions(self, survey: Dict[str, Any], contact: Dict[str, Any]) -> str:
        """
        Build system prompt for voice agent from survey data.

        Args:
            survey: Survey dict with questionnaire and settings
            contact: Contact dict

        Returns:
            Formatted system prompt string
        """
        tone = survey.get("voice_agent_tone", "friendly")
        title = survey.get("json_questionnaire", {}).get("title", "Survey")
        custom_instructions = survey.get("voice_agent_instructions", "")

        # Extract questions from questionnaire
        questions = survey.get("json_questionnaire", {}).get("questions", [])

        # Format questions for prompt
        formatted_questions = []
        for idx, q in enumerate(questions, 1):
            question_text = q.get("question_text", "")
            question_type = q.get("question_type", "")
            question_id = q.get("question_id", "")

            formatted_q = f"{idx}. [{question_type}] {question_text}"

            # Add options for multiple choice
            if question_type in ["multiple_choice", "checkbox", "dropdown"]:
                options = q.get("options", [])
                if options:
                    formatted_q += f"\n   Options: {', '.join(options)}"

            # Add scale info
            if question_type == "linear_scale":
                low = q.get("scale_low", 1)
                high = q.get("scale_high", 5)
                formatted_q += f"\n   Scale: {low} to {high}"

            formatted_questions.append(formatted_q)

        questions_text = "\n".join(formatted_questions)

        # Get researcher name from survey (if available)
        researcher_name = survey.get("researcher_name", "our team")
        participant_name = contact.get("participant_name", "participant")

        # Build system prompt
        prompt = f"""You are conducting a voice survey for {researcher_name} about "{title}".

QUESTIONS (ask in this exact order):
{questions_text}

INSTRUCTIONS:

1. GREETING - Say exactly:
"Hi {participant_name}! I'm {researcher_name}'s AI assistant, conducting a survey on the topic {title}. Before starting the survey, please give me your consent by saying 'Yes'."

2. WAIT FOR CONSENT:
- Listen for "yes", "yeah", "sure", "okay" or similar affirmative response
- If they consent, say "Great! Let's begin."
- If they decline, try to convince them gently to participate highlighting the value they can give to the research, if they still refuse then say "I understand. Thank you for your time. Goodbye." and end call

3. FOR EACH QUESTION:
- Ask the question clearly and briefly
- Wait for their answer
- Acknowledge with ONE word: "Thanks" or "Okay" or "Got it"
- Immediately ask the NEXT question
- Do NOT add filler words, pauses, or extra commentary
- Do NOT ask "ready for next?" or "shall we continue?"

4. AFTER LAST QUESTION:
- Say: "That's all the questions! Thank you so much for your valuable inputs. Have a great day!"
- Then call the end_survey_call function to end the call
- If participant says goodbye at any time, thank them and call end_survey_call

5. SPEAKING STYLE - Keep It Brief:
- Be warm but concise
- Use SHORT acknowledgments (1-2 words max)
- Do NOT add filler words like "um", "uh", "let's see"
- Do NOT add extra commentary or information
- Just ask questions → get answers → move on
- NEVER ramble or improvise beyond the script

6. RESPONSE STORAGE:
- After getting each answer, call the store_response function with question_id and answer
- After consent, call the store_consent function

{"CUSTOM INSTRUCTIONS:\n" + custom_instructions if custom_instructions else ""}"""

        return prompt

    @function_tool
    async def store_consent(self, context: RunContext, consent: bool) -> str:
        """
        Store participant consent.

        Args:
            context: Run context
            consent: Whether consent was given

        Returns:
            Confirmation message
        """
        self.consent_given = consent
        logger.info(f"Consent stored: {consent} for call {self.call_sid}")

        # Update database with consent
        db = get_db()
        try:
            db.table("call_logs").update({
                "consent": consent
            }).eq("twilio_call_sid", self.call_sid).execute()
        except Exception as e:
            logger.error(f"Failed to update consent in DB: {e}")

        return f"Consent recorded: {consent}"

    @function_tool
    async def store_response(
        self,
        context: RunContext,
        question_id: str,
        question_text: str,
        answer: str
    ) -> str:
        """
        Store participant's response to a question.

        Args:
            context: Run context
            question_id: Question identifier
            question_text: Question text
            answer: Participant's answer

        Returns:
            Confirmation message
        """
        response_data = {
            "question_id": question_id,
            "question_text": question_text,
            "answer": answer,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.raw_responses.append(response_data)
        logger.info(f"Response stored for question {question_id}: {answer[:50]}...")

        # Update database with responses
        db = get_db()
        try:
            db.table("call_logs").update({
                "raw_responses": [
                    {"question_id": r["question_id"], "raw_response": r["answer"]}
                    for r in self.raw_responses
                ]
            }).eq("twilio_call_sid", self.call_sid).execute()
        except Exception as e:
            logger.error(f"Failed to update responses in DB: {e}")

        return f"Response recorded for question {question_id}"

    @function_tool
    async def end_survey_call(
        self,
        context: RunContext
    ) -> str:
        """
        Mark survey as complete. Agent will say goodbye and call will end naturally.

        Use this when:
        - All survey questions have been answered
        - Participant says goodbye or wants to end the call
        - Survey is complete

        Args:
            context: Run context

        Returns:
            Confirmation message for LLM (agent says this)
        """
        logger.info(f"Survey marked complete for {self.call_sid}")

        # Update call status to completed
        db = get_db()
        try:
            db.table("call_logs").update({
                "status": "completed"
            }).eq("twilio_call_sid", self.call_sid).execute()
        except Exception as e:
            logger.error(f"Failed to update call status: {e}")

        # Return message that LLM will speak, then session ends naturally
        return "Say: 'That's all the questions! Thank you so much for your valuable inputs in our research. We promise to keep them anonymous. I wish the very best and have a great day!' Then disconnect."

    async def on_enter(self):
        """Called when agent session starts."""
        logger.info(f"Agent session started for call {self.call_sid}")

        # Create initial call log entry if doesn't exist
        db = get_db()
        try:
            existing = db.table("call_logs").select("twilio_call_sid").eq("twilio_call_sid", self.call_sid).execute()

            if not existing.data:
                db.table("call_logs").insert({
                    "twilio_call_sid": self.call_sid,
                    "contact_id": self.contact_id,
                    "status": "in_progress",
                    "call_duration": 0,
                    "consent": False,
                    "raw_transcript": "",
                    "raw_responses": [],
                    "mapped_responses": []
                }).execute()
                logger.info(f"Created call log for {self.call_sid}")
        except Exception as e:
            logger.warning(f"Could not create call log: {e}")

        # Generate initial greeting
        await self.session.generate_reply(
            instructions="Greet the user and ask for consent exactly as instructed."
        )

    async def on_exit(self):
        """Called when agent session ends."""
        logger.info(f"Agent session ended for call {self.call_sid}")

        # Store final transcript
        db = get_db()
        try:
            # Build full transcript from conversation
            transcript_text = self._build_transcript()

            db.table("call_logs").update({
                "raw_transcript": transcript_text,
                "status": "completed"
            }).eq("twilio_call_sid", self.call_sid).execute()

            logger.info(f"Stored final transcript for {self.call_sid}")
        except Exception as e:
            logger.error(f"Failed to store final transcript: {e}")

        # Map raw responses to structured format using LLM
        if self.raw_responses:
            try:
                mapped_responses = await self._map_responses_with_llm()

                # Store mapped responses in database
                db.table("call_logs").update({
                    "mapped_responses": mapped_responses
                }).eq("twilio_call_sid", self.call_sid).execute()

                logger.info(f"Stored {len(mapped_responses)} mapped responses for {self.call_sid}")
            except Exception as e:
                logger.error(f"Failed to map responses: {e}")

    def _build_transcript(self) -> str:
        """Build full transcript from conversation history."""
        if not self.conversation_transcript:
            return ""

        transcript_lines = []
        for item in self.conversation_transcript:
            role = item.get("role", "unknown")
            content = item.get("content", "")
            transcript_lines.append(f"{role.upper()}: {content}")

        return "\n".join(transcript_lines)

    async def _map_responses_with_llm(self) -> List[Dict[str, Any]]:
        """
        Map raw voice responses to structured format using LLM.

        Uses OpenAI GPT to intelligently map conversational responses
        to the expected format based on question type.

        Returns:
            List of mapped responses with question_id and mapped_response
        """
        from openai import AsyncOpenAI

        # Get questions from survey
        questions = self.survey.get("json_questionnaire", {}).get("questions", [])

        # Build question reference for LLM
        question_context = []
        for q in questions:
            q_info = {
                "question_id": q.get("question_id"),
                "question_text": q.get("question_text"),
                "question_type": q.get("question_type"),
            }

            # Add type-specific info
            if q.get("question_type") in ["multiple_choice", "checkbox", "dropdown"]:
                q_info["options"] = q.get("options", [])
            elif q.get("question_type") == "linear_scale":
                q_info["scale_low"] = q.get("scale_low", 1)
                q_info["scale_high"] = q.get("scale_high", 5)

            question_context.append(q_info)

        # Build mapping prompt
        mapping_prompt = f"""You are a survey response analyst. Map raw voice responses to structured formats.

QUESTIONS:
{json.dumps(question_context, indent=2)}

RAW RESPONSES:
{json.dumps(self.raw_responses, indent=2)}

MAPPING RULES:
1. **multiple_choice/dropdown**: Extract EXACT option from list. If not in list, find closest match.

2. **checkbox**: Extract ALL mentioned options as comma-separated list.

3. **linear_scale**: Extract numeric rating only.

4. **text/long_text/paragraph**: Return EXACTLY as spoken, NO summarization, NO changes.

5. **yes_no**: Return "Yes" or "No".

OUTPUT:
Return JSON array matching EXACTLY the number of raw responses. Use the EXACT question_id from the questions list.

[
  {{
    "question_id": "use exact ID from questions",
    "mapped_response": "mapped value"
  }}
]

CRITICAL:
- Output array length MUST equal raw responses length ({len(self.raw_responses)} items)
- Use EXACT question_id from questions list (not q1, q2, etc)
- For text/long_text: NO summarization, return verbatim
- Return ONLY JSON array, no markdown"""

        try:
            # Call OpenAI API for mapping
            client = AsyncOpenAI(api_key=settings.openai_api_key)

            response = await client.chat.completions.create(
                model=settings.llm_choice,  # Use same model as voice agent
                messages=[
                    {"role": "system", "content": mapping_prompt},
                    {"role": "user", "content": "Please map these responses."}
                ],
                temperature=0.3,  # Low temperature for consistent mapping
                max_tokens=1000
            )

            # Parse LLM response
            mapped_json = response.choices[0].message.content.strip()

            # Remove markdown code blocks if present
            if mapped_json.startswith("```"):
                mapped_json = mapped_json.split("```")[1]
                if mapped_json.startswith("json"):
                    mapped_json = mapped_json[4:]
                mapped_json = mapped_json.strip()

            mapped_responses = json.loads(mapped_json)

            logger.info(f"Successfully mapped {len(mapped_responses)} responses using LLM")
            return mapped_responses

        except Exception as e:
            logger.error(f"LLM mapping failed: {e}", exc_info=True)
            # Fallback: return raw responses as mapped
            return [
                {"question_id": r["question_id"], "mapped_response": r["answer"]}
                for r in self.raw_responses
            ]


def create_agent_session(
    survey: Dict[str, Any],
    contact: Dict[str, Any],
    call_sid: str
) -> tuple[SurveyVoiceAgent, AgentSession]:
    """
    Create LiveKit agent session for survey call.

    Args:
        survey: Survey data
        contact: Contact data
        call_sid: Twilio call SID

    Returns:
        Tuple of (agent, session)
    """
    # Create survey agent
    agent = SurveyVoiceAgent(survey=survey, contact=contact, call_sid=call_sid)

    # Get preferred voice from survey settings (or use default Rime voice)
    # Rime voices: celeste, astra, orion, nova, zenith, andromeda, phoenix
    preferred_voice = survey.get("voice_agent_voice", "astra")

    # Create agent session optimized for ultra-low latency with streaming
    # Using Groq's Llama 3.3 70B via OpenAI-compatible API (10x faster than GPT-4o-mini)
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-2",  # Nova-2 for best transcription quality
            detect_language=False,  # Disable language detection for speed
            interim_results=True,  # Enable interim results for responsiveness
            punctuate=True,  # Punctuation works better with turn detection than smart_format
            smart_format=False,  # Disable smart_format to reduce latency
            endpointing_ms=250,  # Optimized turn detection: 250ms silence = end of speech (more natural)
            no_delay=True,  # No buffering delay
        ),
        llm=openai.LLM(
            model=settings.groq_llm,  # Llama 3.3 70B from Groq
            base_url="https://api.groq.com/openai/v1",  # Groq's OpenAI-compatible endpoint
            api_key=settings.groq_api_key,  # Use Groq API key
            temperature=0.4,  # Lower temp for consistency, reduce hallucinations
            max_completion_tokens=200,  # Brief responses, prevent rambling
        ),
        tts=inference.TTS(
            model="rime/arcana",  # Rime Arcana - natural-sounding, low latency
            voice=preferred_voice,  # Rime voice (celeste, astra, orion, nova, etc.)
            language="en",
        ),
    )

    logger.info(f"Created agent session for survey {survey.get('survey_id')}")

    return agent, session
