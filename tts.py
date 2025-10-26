import asyncio
from livekit.plugins.cartesia import TTS

async def test_tts():
    tts = TTS(
        api_key="your_cartesia_api_key",  # Replace with your actual key
        model="sonic-2",
        voice="79a125e8-cd45-4c13-8a67-188112f4dd22"  # Valid British Lady voice
    )
    async for frame in tts.synthesize("Hello world"):
        print("Audio frame received:", len(frame.audio))  # Should print frame lengths > 0
    await tts.aclose()

asyncio.run(test_tts())
