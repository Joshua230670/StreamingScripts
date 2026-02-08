import webbrowser
import requests
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TOKEN = os.getenv("TOKEN")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
REDIRECT_URI = "http://localhost"

def generate_token():
    global CLIENT_ID
    global CLIENT_SECRET
    
    SCOPES = "channel:read:redemptions channel:manage:redemptions"
    
    # Step 1: Generate authorization URL
    auth_url = (
        f"https://id.twitch.tv/oauth2/authorize?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={SCOPES}&"
        f"force_verify=false"
    )
    
    print("Step 1: Open this URL in your browser and authorize the app:")
    print(auth_url)
    print("\nAfter authorizing, you'll be redirected to a blank page.")
    print("Copy the ENTIRE URL from your browser address bar and paste it below.")
    
    webbrowser.open(auth_url)
    
    # Step 2: Get the authorization code from the user
    redirect_url = input("\nPaste the redirect URL here: ").strip()
    
    # Extract the code from the URL
    if "code=" in redirect_url:
        code = redirect_url.split("code=")[1].split("&")[0]
        print(f"Extracted code: {code}")
        with open('.env', 'r') as f:
            lines = f.readlines()
        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith("CODE="):
                    f.write(f'CODE={code}\n')
                else:
                    f.write(line)

    else:
        print("Error: No code found in the URL")
        return
    
    # Step 3: Exchange code for token
    token_url = "https://id.twitch.tv/oauth2/token"
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI
    }
    
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        token_data = response.json()
        print("\n✅ TOKEN GENERATED SUCCESSFULLY!")
        print(f"Access Token: {token_data['access_token']}")
        print(f"Refresh Token: {token_data.get('refresh_token', 'None')}")
        print(f"Expires In: {token_data['expires_in']} seconds")
        
        # Update .env file
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('TOKEN='):
                    f.write(f'TOKEN=oauth:{token_data["access_token"]}\n')
                elif line.startswith('REFRESH_TOKEN='):
                    f.write(f"REFRESH_TOKEN={token_data["refresh_token"]}\n")
                else:
                    f.write(line)

        print("\n✅ .env file updated with new token!")
        
    else:
        print(f"❌ ERROR GETTING TOKEN: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    generate_token()