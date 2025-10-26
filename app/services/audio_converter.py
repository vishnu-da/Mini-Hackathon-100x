"""
Audio format conversion utilities for Twilio ↔ OpenAI Realtime API.

Handles:
- Format conversion: mulaw (8-bit) ↔ PCM16 (16-bit)
- Sample rate conversion: 8kHz (Twilio) ↔ 24kHz (OpenAI)
- Base64 encoding/decoding
"""
import base64
import audioop
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Audio specifications
TWILIO_SAMPLE_RATE = 8000  # Hz
OPENAI_SAMPLE_RATE = 24000  # Hz
SAMPLE_WIDTH = 2  # 16-bit = 2 bytes

# Global state for stateful resampling (maintains continuity between chunks)
_openai_to_twilio_state: Optional[Tuple] = None


def twilio_to_openai(mulaw_b64: str) -> str:
    """
    Convert Twilio audio (mulaw 8kHz) to OpenAI format (PCM16 24kHz).

    Args:
        mulaw_b64: Base64-encoded mulaw audio from Twilio

    Returns:
        Base64-encoded PCM16 audio for OpenAI
    """
    try:
        # Step 1: Decode base64 to get mulaw bytes
        mulaw_audio = base64.b64decode(mulaw_b64)

        # Step 2: Convert mulaw to linear PCM16 (still 8kHz)
        pcm16_8k = audioop.ulaw2lin(mulaw_audio, SAMPLE_WIDTH)

        # Step 3: Resample from 8kHz to 24kHz (3x upsampling)
        # audioop.ratecv(fragment, width, nchannels, inrate, outrate, state)
        pcm16_24k, _ = audioop.ratecv(
            pcm16_8k,
            SAMPLE_WIDTH,
            1,  # mono
            TWILIO_SAMPLE_RATE,
            OPENAI_SAMPLE_RATE,
            None  # no state for stateless conversion
        )

        # Step 4: Encode to base64 for transmission
        pcm16_b64 = base64.b64encode(pcm16_24k).decode('utf-8')

        return pcm16_b64

    except Exception as e:
        logger.error(f"Error converting Twilio→OpenAI audio: {e}")
        raise


def openai_to_twilio(pcm16_b64: str) -> str:
    """
    Convert OpenAI audio (PCM16 24kHz) to Twilio format (mulaw 8kHz).
    Uses stateful resampling to maintain audio continuity between chunks.

    Args:
        pcm16_b64: Base64-encoded PCM16 audio from OpenAI

    Returns:
        Base64-encoded mulaw audio for Twilio
    """
    global _openai_to_twilio_state

    try:
        # Step 1: Decode base64 to get PCM16 bytes
        pcm16_24k = base64.b64decode(pcm16_b64)

        # Step 2: Resample from 24kHz to 8kHz (3x downsampling)
        # Use stateful resampling to prevent audio cutoff at chunk boundaries
        pcm16_8k, _openai_to_twilio_state = audioop.ratecv(
            pcm16_24k,
            SAMPLE_WIDTH,
            1,  # mono
            OPENAI_SAMPLE_RATE,
            TWILIO_SAMPLE_RATE,
            _openai_to_twilio_state  # Maintain state between chunks
        )

        # Step 3: Convert linear PCM16 to mulaw
        mulaw_audio = audioop.lin2ulaw(pcm16_8k, SAMPLE_WIDTH)

        # Step 4: Encode to base64 for transmission
        mulaw_b64 = base64.b64encode(mulaw_audio).decode('utf-8')

        return mulaw_b64

    except Exception as e:
        logger.error(f"Error converting OpenAI→Twilio audio: {e}")
        raise


def reset_conversion_state():
    """
    Reset the global resampling state.
    Should be called at the start of each new call to prevent
    audio artifacts from previous calls.
    """
    global _openai_to_twilio_state
    _openai_to_twilio_state = None
    logger.debug("Audio conversion state reset for new call")
