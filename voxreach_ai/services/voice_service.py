import os
import uuid
import requests
import json
from typing import Optional
from voxreach_ai.utils.config import get_settings
from voxreach_ai.utils.logger import logger

settings = get_settings()

class VoiceService:
    def __init__(self):
        # ElevenLabs Settings
        self.el_api_key = settings.ELEVENLABS_API_KEY
        self.el_base_url = "https://api.elevenlabs.io/v1"
        self.el_voice_id = settings.ELEVENLABS_VOICE_ID or "XW7cPdbFKaf5OwuwzCWH"
        
        # Minimax Settings
        self.mm_api_key = settings.MINIMAX_API_KEY
        self.mm_voice_id = settings.MINIMAX_VOICE_ID or "moss_audio_7b99f288-a349-11f0-ac24-56b1c4839062"
        self.mm_base_url = settings.MINIMAX_BASE_URL
        
        self.provider = settings.VOICE_PROVIDER.lower()
        
        # Ensure the local 'audio' directory exists
        self.audio_dir = os.path.join(os.getcwd(), "audio")
        if not os.path.exists(self.audio_dir):
            os.makedirs(self.audio_dir)
            logger.info(f"Created audio directory at {self.audio_dir}")

    def generate_audio(self, text: str) -> Optional[str]:
        """
        Converts text to speech using configured provider and saves it locally.
        Returns the path to the generated audio file or None if it fails.
        """
        if self.provider == "minimax":
            return self._generate_with_minimax(text)
        else:
            return self._generate_with_elevenlabs(text)

    def _generate_with_minimax(self, text: str) -> Optional[str]:
        if not self.mm_api_key:
            logger.warning("MINIMAX_API_KEY is missing. VoiceService will not generate audio. Running in dry-run mode.")
            return None

        logger.info(f"Generating audio with Minimax (Voice ID: {self.mm_voice_id})...")
        
        file_name = f"{uuid.uuid4()}.mp3"
        file_path = os.path.join(self.audio_dir, file_name)
        
        headers = {
            "Authorization": f"Bearer {self.mm_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "speech-01-turbo",
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": self.mm_voice_id,
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1
            },
            "output_format": "hex"
        }
        
        try:
            logger.debug(f"Calling Minimax API at {self.mm_base_url}")
            response = requests.post(self.mm_base_url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if "data" in result and "audio" in result["data"]:
                    hex_audio = result["data"]["audio"]
                    audio_bytes = bytes.fromhex(hex_audio)
                    with open(file_path, 'wb') as f:
                        f.write(audio_bytes)
                    
                    if os.path.exists(file_path):
                        logger.info(f"Audio generated at: {file_path}")
                        return file_name
                    else:
                        logger.error(f"File was not saved correctly at {file_path}")
                        return None
                else:
                    logger.error(f"Minimax API Error: Invalid response format: {result}")
                    return None
            else:
                logger.error(f"Minimax API Error [{response.status_code}]: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error communicating with Minimax: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating audio with Minimax: {str(e)}")
            return None

    def _generate_with_elevenlabs(self, text: str) -> Optional[str]:
        if not self.el_api_key:
            logger.warning("ELEVENLABS_API_KEY is missing. VoiceService will not generate audio. Running in dry-run mode.")
            return None

        logger.info(f"Generating audio with ElevenLabs (Voice ID: {self.el_voice_id})...")
        
        file_name = f"{uuid.uuid4()}.mp3"
        file_path = os.path.join(self.audio_dir, file_name)

        url = f"{self.el_base_url}/text-to-speech/{self.el_voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.el_api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        try:
            logger.debug(f"Calling ElevenLabs API at {url}")
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                
                if os.path.exists(file_path):
                    logger.info(f"Audio generated at: {file_path}")
                    return file_name
                else:
                    logger.error(f"File was not saved correctly at {file_path}")
                    return None
            else:
                logger.error(f"ElevenLabs API Error [{response.status_code}]: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error communicating with ElevenLabs: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating audio: {str(e)}")
            return None

voice_service = VoiceService()
