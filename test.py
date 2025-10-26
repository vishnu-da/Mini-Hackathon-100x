from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

# Use anon key (not service key) for auth
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")  # Anon key for client auth
)

# Sign in to get user JWT
try:
    response = supabase.auth.sign_in_with_password({
        "email": "guptavishnu168@gmail.com",
        "password": "Hello123"
    })
    print("JWT Token (copy this):")
    print(f"Bearer {response.session.access_token}")
    print(f"\nUser ID: {response.user.id}")
except Exception as e:
    print(f"Auth failed: {e}")
    print("\nUsing service role key instead:")
    print(f"Bearer {os.getenv('SUPABASE_SERVICE_KEY')}")