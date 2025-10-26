"""
Simple script to initiate a test call without interactive prompts.
"""
import asyncio
from app.config import get_settings
from app.services.twilio_client import initiate_call
from app.database import get_db

settings = get_settings()

async def main():
    print("\n" + "=" * 60)
    print("INITIATING TEST CALL")
    print("=" * 60)

    # Fetch first contact from database
    db = get_db()
    result = db.table("contact").select("*").limit(1).execute()

    if not result.data:
        print("[ERROR] No contacts found in database")
        print("\nPlease create a contact first using:")
        print("POST /surveys/{survey_id}/contacts")
        return

    contact = result.data[0]
    phone = contact.get('phone_number')
    survey_id = contact.get('survey_id')
    contact_id = contact.get('contact_id')

    print(f"\nContact found:")
    print(f"  Name: {contact.get('name', 'Unknown')}")
    print(f"  Phone: {phone}")
    print(f"  Survey ID: {survey_id}")
    print(f"  Contact ID: {contact_id}")
    print()

    print("Initiating call...")
    print()

    try:
        call_sid = initiate_call(
            to_phone=phone,
            survey_id=survey_id,
            contact_id=contact_id
        )

        print("=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"Call SID: {call_sid}")
        print(f"\nYour phone ({phone}) should ring shortly!")
        print()
        print("Webhook URL that Twilio will call:")
        print(f"  {settings.callback_base_url}/webhooks/twilio/voice/{contact_id}")
        print()
        print("=" * 60)
        print("IMPORTANT: Make sure your FastAPI server is running!")
        print("=" * 60)
        print("1. Start your server: python app/main.py")
        print("2. Make sure ngrok is running: ngrok http 8000")
        print(f"3. ngrok URL should be: {settings.callback_base_url}")
        print()
        print("Check Twilio logs:")
        print("  https://console.twilio.com/us1/monitor/logs/calls")
        print()

    except Exception as e:
        print("=" * 60)
        print("CALL FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Possible reasons:")
        print("1. Invalid phone number format (must be E.164 format)")
        print("2. Twilio credentials are incorrect")
        print("3. Insufficient Twilio account balance")
        print("4. Phone number not verified (if using trial account)")
        print("5. Twilio service is down")
        print()

if __name__ == "__main__":
    asyncio.run(main())
