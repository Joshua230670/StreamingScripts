import os
import obsws_python as obs
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

# ------------------- Twitch Credentials -------------------
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
access_token = os.getenv("TOKEN")
refresh_token = os.getenv("REFRESH_TOKEN")
twitch_id = os.getenv("TWITCH_ID")
reward_name = ""

# ------------------- OBS Credentials -------------------
host = os.getenv("HOST")
port = int(os.getenv("PORT"))
password = os.getenv("PASSWORD")

# Initialize OBS client
client = obs.ReqClient(host=host, port=port, password=password)

scene_name = ""
source_name = "Pet"
item_id = client.get_scene_item_id(scene_name=scene_name, source_name=source_name).scene_item_id

async def unhide_gif(item_id):
    # Enables the gif for a certain amount of time
    try:
        client.set_scene_item_enabled(scene_name=scene_name, item_id=item_id, enabled=True)
    except Exception as e:
        print(f"Could not enable the scene item: {e}")

async def hide_gif(item_id, delay=10):
    # Disables the gif after a certain amount of time
    await asyncio.sleep(delay)
    try:
        client.set_scene_item_enabled(scene_name=scene_name, item_id=item_id, enabled=False)
    except Exception as e:
        print(f"Could not disable the scene item: {e}")

class Bot:
    def __init__(self):
        self.client_id = client_id
        self.user_token = access_token.replace("oauth:", "")
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
                    params={'broadcaster_id': twitch_id},
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
                            if reward['title'].lower() == reward_name.lower():
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
            print(f"[SUCCESS] Using existing reward: '{reward_name}'")
            return True
            
        print("[INFO] Reward not found, creating new one...")
        return await self.create_reward()
    
    async def create_reward(self):
        # Create the reward using the API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'https://api.twitch.tv/helix/channel_points/custom_rewards',
                    params={'broadcaster_id': twitch_id},
                    headers={
                        'Client-ID': self.client_id,
                        'Authorization': f'Bearer {self.user_token}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'title': reward_name,
                        'cost': 50,
                        'prompt': '',
                        'is_enabled': True,
                        'background_color': "#3539FF",
                        'is_user_input_required': False,
                        'should_redemptions_skip_request_queue': False
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.reward_id = data['data'][0]['id']
                        print(f"[SUCCESS] Created new reward: '{reward_name}' (ID: {self.reward_id})")
                        return True
                    else:
                        error_text = await resp.text()
                        print(f"[ERROR] Failed to create reward: {resp.status} - {error_text}")
                        return False
        except Exception as e:
            print(f"[ERROR] Failed to create reward: {e}")
            return False
        
    async def poll_redemptions(self):
        while True:
            try:
                self.poll_count += 1

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f'https://api.twitch.tv/helix/channel_points/custom_rewards/redemptions',
                        params={
                            'broadcaster_id': twitch_id,
                            'reward_id': self.reward_id,
                            'status': 'UNFULFILLED',
                            'first': 50
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
                                
                                if self.last_redemption_id == redemption_id:
                                    continue
                                
                                await unhide_gif(item_id=item_id)
                                await hide_gif(item_id=item_id, delay=10)
                                
                                await self.fulfill_redemption(redemption_id)
                                self.last_redemption_id = redemption_id
                    

            except Exception as e:
                print(f"Polling error: {e}")

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
                        'broadcaster_id': twitch_id,
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
        print(f"Reward: '{reward_name}'")
        
        await self.poll_redemptions()

    


async def main():
    bot = Bot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Bot stopped by user")
