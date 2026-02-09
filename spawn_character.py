import os
import asyncio
import random
import aiohttp
import time
from dotenv import load_dotenv
import obsws_python as obs

# Load .env
load_dotenv()

# ---------------- Twitch Credentials ----------------
CLIENT_ID = os.getenv("CLIENT_ID")
TOKEN = os.getenv("TOKEN")
TWITCH_ID = os.getenv("TWITCH_ID")
REWARD_NAME = "Add a Character"

# ---------------- OBS Credentials ----------------
OBS_HOST = os.getenv("HOST")
OBS_PORT = int(os.getenv("PORT"))
OBS_PASSWORD = os.getenv("PASSWORD")

# ---------------- Character Images ----------------
CHARACTER_IMAGES = [
    "",
    ""
]

character_counter = 0
obs_client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)

async def remove_character_after_delay(source_name, delay=60):
    # Remove the character image after specified delay
    await asyncio.sleep(delay)
    try:
        obs_client.remove_input(source_name)
        print(f"[CLEANUP] Removed {source_name} after {delay} seconds")
    except Exception as e:
        print(f"[CLEANUP] Failed to remove {source_name}: {e}")

def spawn_character():
    # Spawns a random character image in OBS at a random location.
    global character_counter
    try:
        # Force different random values each time
        random.seed(time.time() + character_counter + random.randint(1, 1000))
        
        image_path = random.choice(CHARACTER_IMAGES)
        
        # Generate truly random positions
        x_pos = random.randint(-30, 1600)  # More margin for larger images
        y_pos = random.randint(-30, 800)   # More margin for larger images
        
        # Random scale
        scale = random.uniform(0.3, 1.2)

        character_counter += 1
        source_name = f"Character{character_counter}"

        print(f"[OBS] Creating image: {os.path.basename(image_path)}")
        print(f"[OBS] Random position: ({x_pos}, {y_pos})")
        print(f"[OBS] Random scale: {scale:.2f}")
        
        # Create image source
        obs_client.create_input(
            sceneName="Splatoon Overlay Upgraded",
            inputName=source_name,
            inputKind="image_source",
            inputSettings={"file": image_path},
            sceneItemEnabled=True,
        )

        # Get the scene item ID - wait a moment for it to be created
        time.sleep(0.1)
        
        try:
            item = obs_client.get_scene_item_id(scene_name="Splatoon Overlay Upgraded", source_name=source_name)
            print(f"[OBS] Got scene item ID: {item.scene_item_id}")
            
            # Set position using set_scene_item_properties instead of transform
            obs_client.set_scene_item_transform(
                scene_name="Splatoon Overlay Upgraded",
                item_id=item.scene_item_id,
                transform={
                    "positionX": float(x_pos),
                    "positionY": float(y_pos),
                    "scaleX": float(scale),
                    "scaleY": float(scale)
                }
            )
            
            print(f"[SUCCESS] Spawned {source_name} at ({x_pos},{y_pos}) scale {scale:.2f}")
            
        except Exception as e:
            print(f"[ERROR] Failed to set position for {source_name}: {e}")
            # Try alternative method
            try:
                print("[OBS] Trying alternative position setting method...")
                # Sometimes we need to use set_scene_item_properties
                obs_client.call(
                    "SetSceneItemTransform",
                    {
                        "sceneName": "Splatoon Overlay Upgraded",
                        "sceneItemId": item.scene_item_id,
                        "sceneItemTransform": {
                            "positionX": float(x_pos),
                            "positionY": float(y_pos),
                            "scaleX": float(scale),
                            "scaleY": float(scale)
                        }
                    }
                )
                print(f"[SUCCESS] Alternative method worked for {source_name}")
            except Exception as alt_e:
                print(f"[ERROR] Alternative method also failed: {alt_e}")
        
        # Return the source name so we can track it for removal
        return source_name
        
    except Exception as e:
        print("[ERROR] Failed to spawn character:", e)
        return None


async def spawn_character_async():
    # Async wrapper for spawn_character to run in executor.
    loop = asyncio.get_event_loop()
    source_name = await loop.run_in_executor(None, spawn_character)
    
    # If the character was successfully created, schedule its removal
    if source_name:
        asyncio.create_task(remove_character_after_delay(source_name, 60))

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
                        'cost': 10,
                        'prompt': 'Add a character to the scene for 5 seconds!',
                        'is_enabled': True,
                        'background_color': "#765566",
                        'is_user_input_required': False,
                        'should_redemptions_skip_request_queue': False,
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
                            'first': 10
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
                                
                                if self.last_redemption_id == redemption_id:
                                    continue
                                
                                print(f"🎉 [REDEMPTION] {user_name} redeemed '{REWARD_NAME}'!")
                                await spawn_character_async()
                                
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

async def main():
    bot = CharacterBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Bot stopped by user")
