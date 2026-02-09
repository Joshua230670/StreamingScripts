# StreamingScripts
This repository's main purpose is to store all the streaming scripts I have made for platform Twitch.
They utilize OBS-Websocket Python and the Twitch API to monitor for channel rewards that are redeemed. 
Once the Twitch API responds successfully, OBS sources are manipulated to act according to
the specified reward using the websocket.

### List of Scripts
* [Generate Token](https://github.com/Joshua230670/StreamingScripts/blob/main/generate_token.py)
* [Refresh Token](https://github.com/Joshua230670/StreamingScripts/blob/main/refresh_token.py)
* [Spawn Character](https://github.com/Joshua230670/StreamingScripts/blob/main/spawn_character.py)
* [Pet Head](https://github.com/Joshua230670/StreamingScripts/blob/main/pet_head.py)
* [Character Speak](https://github.com/Joshua230670/StreamingScripts/blob/main/character_speak.py)

### Dependencies
* os
* asyncio
* aiohttp
* random
* time
* dotenv,load_dotenv
* obsws_python
* google, genai
* elevenlabs.client,ElevenLabs
* elevenlabs.environment, ElevenLabsEnvironment

### This README.md is a W.I.P
