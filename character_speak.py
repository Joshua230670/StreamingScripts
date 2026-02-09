import os
import obsws_python as obs
import aiohttp
import asyncio
import soundfile as sf
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.environment import ElevenLabsEnvironment
from elevenlabs import stream
from google import genai

load_dotenv()

# ---------------- API ----------------
gemini_key = os.getenv("GEMINI_KEY")
eleven_key = os.getenv("ELEVEN_KEY")

# ---------------- Twitch Credentials ----------------
CLIENT_ID = os.getenv("CLIENT_ID")
TOKEN = os.getenv("TOKEN")
TWITCH_ID = os.getenv("TWITCH_ID")
REWARD_NAME = ""

# ---------------- OBS Credentials ----------------
OBS_HOST = os.getenv("HOST")
OBS_PORT = int(os.getenv("PORT"))
OBS_PASSWORD = os.getenv("PASSWORD")

obs_client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)

# Initialize Gemini client
gemini_client = genai.Client(api_key=gemini_key)

# Initialize ElevenLabs client
eleven_client = ElevenLabs(
    api_key=eleven_key,
    environment=ElevenLabsEnvironment.PRODUCTION
)

prompt = ""

class CharacterBot:
    def __init__(self):
        self.client_id = CLIENT_ID
        self.user_token = TOKEN.replace("oauth:", "")
        self.reward_id = None
        self.last_redemption_id = None
        self.poll_count = 0
        
    async def debug_reward_status(self):
        # Debug function to check reward status and permissions
        print("\n=== DEBUG REWARD STATUS ===")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'https://api.twitch.tv/helix/channel_points/custom_rewards',
                    params={'broadcaster_id': TWITCH_ID},
                    headers={
                        'Client-ID': self.client_id,
                        'Authorization': f'Bearer {self.user_token}'
                    }
                ) as resp:
                    print(f"   Rewards API Status: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        rewards = data.get('data', [])
                        print(f"   Found {len(rewards)} rewards:")
                        for reward in rewards:
                            if reward['title'].lower() == REWARD_NAME.lower():
                                self.reward_id = reward['id']
                                print(f"     🎯 '{reward['title']}' (ID: {self.reward_id})")
                            else:
                                print(f"       '{reward['title']}'")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print("=== END DEBUG ===\n")
        
        return self.reward_id is not None

    async def setup_reward(self):
        # Either find existing reward or create a new one
        print("[INFO] Setting up reward...")
        
        if await self.debug_reward_status():
            print(f"[SUCCESS] Using existing reward: '{REWARD_NAME}'")
            return True
        
        print("[INFO] Reward not found, creating new one...")
        return await self.create_reward()
    
    async def create_reward(self):
        # Create the reward using the API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'https://api.twitch.tv/helix/channel_points/custom_rewards',
                    params={'broadcaster_id': TWITCH_ID},
                    headers={
                        'Client-ID': self.client_id,
                        'Authorization': f'Bearer {self.user_token}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'title': REWARD_NAME,
                        'cost': 500,
                        'prompt': '',
                        'is_enabled': True,
                        'background_color': "#FF86C5",
                        'is_user_input_required': True,
                        'should_redemptions_skip_request_queue': False
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.reward_id = data['data'][0]['id']
                        print(f"[SUCCESS] Created new reward: '{REWARD_NAME}' (ID: {self.reward_id})")
                        return True
                    else:
                        error_text = await resp.text()
                        print(f"[ERROR] Failed to create reward: {resp.status} - {error_text}")
                        return False
        except Exception as e:
            print(f"[ERROR] Failed to create reward: {e}")
            return False

    async def poll_redemptions(self):
        # Poll for new redemptions
        print(f"[INFO] Starting to poll for '{REWARD_NAME}'...")
        
        while True:
            try:
                self.poll_count += 1
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f'https://api.twitch.tv/helix/channel_points/custom_rewards/redemptions',
                        params={
                            'broadcaster_id': TWITCH_ID,
                            'reward_id': self.reward_id,
                            'status': 'UNFULFILLED',
                            'first': 20
                        },
                        headers={
                            'Client-ID': self.client_id,
                            'Authorization': f'Bearer {self.user_token}'
                        }
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            redemptions = data.get('data', [])
                            
                            for redemption in redemptions:
                                redemption_id = redemption['id']
                                user_name = redemption['user_name']
                                chatter_input = redemption['user_input']
                                user = redemption['user_name']
                                
                                if self.last_redemption_id == redemption_id:
                                    continue
                                
                                print(f"🎉 [REDEMPTION] {user_name} redeemed '{REWARD_NAME}'!")
                                await generate_response(user, chatter_input)
                                
                                await self.fulfill_redemption(redemption_id)
                                self.last_redemption_id = redemption_id
                            
            except Exception as e:
                print(f"[ERROR] Polling error: {e}")
            
            if self.poll_count % 12 == 0:
                print(f"[INFO] Still polling... ({self.poll_count} checks completed)")
            
            await asyncio.sleep(5)

    async def fulfill_redemption(self, redemption_id):
        #Mark redemption as fulfilled
        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(
                    f'https://api.twitch.tv/helix/channel_points/custom_rewards/redemptions',
                    params={
                        'broadcaster_id': TWITCH_ID,
                        'reward_id': self.reward_id,
                        'id': redemption_id
                    },
                    headers={
                        'Client-ID': self.client_id,
                        'Authorization': f'Bearer {self.user_token}'
                    },
                    json={'status': 'FULFILLED'}
                ) as resp:
                    if resp.status == 200:
                        print(f"[SUCCESS] Marked redemption as fulfilled")

        except Exception as e:
            print(f"[ERROR] Fulfillment error: {e}")

    async def run(self):
        # Main bot runner
        print("[INFO] Starting Character Bot...")
        
        if not await self.setup_reward():
            print("[ERROR] Failed to setup reward.")
            return
            
        print(f"\n[SUCCESS] Bot is ready!")
        print(f"Reward: '{REWARD_NAME}'")
        
        await self.poll_redemptions()

async def generate_response(user, chatter_input):
    # -------- Gemini --------
    gemini_resp = gemini_client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt
    )

    print(gemini_resp.text)

    # -------- ElevenLabs --------
    audio = eleven_client.text_to_speech.convert(
        text=gemini_resp.text,
        voice_id="cTnhrSbEbuGjoDHEnwfl",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )

    audio_path = ""

    with open(audio_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    # -------- Switch to talking image --------
        obs_client.set_input_settings(
            "Character",
            {"file": r""},
            overlay=True
        )

    # -------- OBS --------
    
    # Set audio file
    obs_client.set_input_settings(
        "Voice",
        {"local_file": audio_path},
        overlay=True
    )

    # Restart playback (VERY IMPORTANT)
    obs_client.trigger_media_input_action(
        "Voice",
        "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART"
    )

    # -------- Wait for audio to finish --------
    duration = sf.info(audio_path).duration
    await asyncio.sleep(duration)

    # -------- Switch back to idle image --------
    obs_client.set_input_settings(
        "Character",
        {"file": r""},
        overlay=True
    )

# -------- Clear Media Source --------
    obs_client.set_input_settings(
        "Rouge Voice",
        {"local_file": ""},
        overlay=True
    )

async def main():
    bot = CharacterBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Bot stopped by user")
