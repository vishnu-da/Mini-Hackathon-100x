"""Quick signup script for testing"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Signup via Supabase Auth API directly
url = f"{os.getenv('SUPABASE_URL')}/auth/v1/signup"
headers = {
    "apikey": os.getenv('SUPABASE_KEY'),
    "Content-Type": "application/json"
}
data = {
    "email": "guptavishnu168@gmail.com",
    "password": "Hello123"
}

response = requests.post(url, headers=headers, json=data)
print(f"Status: {response.status_code}")
print(response.json())

if response.status_code == 200:
    token = response.json().get('access_token')
    user_id = response.json().get('user', {}).get('id')
    print(f"\nJWT Token:\nBearer {token}")
    print(f"\nUser ID: {user_id}")
