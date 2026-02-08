import requests
import os
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
token = os.getenv("TOKEN")
refresh_token = os.getenv("REFRESH_TOKEN")
code = os.getenv("CODE")
redirect_url = "http://localhost"

def check_token():
    global client_id
    global client_secret
    token_url = "https://id.twitch.tv/oauth2/token"
    data_auth = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_url
    }

    # Response of auth request w/ auth data
    response = requests.post(token_url,data=data_auth)

    if response.status_code == 200:
        print("The current access token is still valid!")
        return
    else:
        data_refresh = {
        'client_id':client_id,
        'client_secret':client_secret,
        'grant_type':'refresh_token',
        'refresh_token':refresh_token
        }

        # Response of auth request w/ refresh data
        response = requests.post(token_url,data=data_refresh)

        if response.status_code == 200:
            token_data = response.json()
            print("✅ TOKEN SUCCESSFULLY REFRESHED!")
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
                        f.write(f'REFRESH_TOKEN={token_data["refresh_token"]}\n')
                    else:
                        f.write(line)
            
            print("\n✅ .env file updated with new token!")
        else:
            print(f"❌ ERROR GETTING TOKEN: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    check_token()