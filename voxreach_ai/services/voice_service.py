import os
import uuid
import requests
import json
import hashlib
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
        self.mm_group_id = settings.MINIMAX_GROUP_ID
        self.mm_voice_id = settings.MINIMAX_VOICE_ID or "moss_audio_7b99f288-a349-11f0-ac24-56b1c4839062"
        self.mm_base_url = settings.MINIMAX_BASE_URL
        
        self.provider = settings.VOICE_PROVIDER.lower()
        
        # Ensure the local 'audio' directory exists
        self.audio_dir = os.path.join(os.getcwd(), "audio")
        if not os.path.exists(self.audio_dir):
            os.makedirs(self.audio_dir)
            logger.info(f"Created audio directory at {self.audio_dir}")

    def generate_audio(self, text: str, cache_key: Optional[str] = None) -> Optional[str]:
        """
        Converts text to speech using configured provider and saves it locally.
        Checks for cached audio using a hash of the cache_key (or text) to prevent redundant generation.
        Returns the path to the generated audio file or None if it fails.
        """
        # 1. Determine key to hash (prefer cache_key over text)
        base_key = cache_key if cache_key else text
        
        # Add provider and voice_id to cache key so changing voices busts the cache
        current_voice_id = self.mm_voice_id if self.provider == "minimax" else self.el_voice_id
        string_to_hash = f"{self.provider}_{current_voice_id}_{base_key}"
        
        # 2. Normalize to improve matching
        normalized_str = string_to_hash.strip().lower()
        
        # 3. Create deterministic filename
        file_hash = hashlib.sha256(normalized_str.encode('utf-8')).hexdigest()
        file_name = f"{file_hash}.mp3"
        file_path = os.path.join(self.audio_dir, file_name)
        
        # 4. Check cache
        if os.path.exists(file_path):
            logger.info(f"Audio Reused from cache: {file_name} (key: '{string_to_hash[:30]}...')")
            return file_name
            
        logger.info(f"Audio Generated new: {file_name} (key: '{string_to_hash[:30]}...')")
        
        if self.provider == "minimax":
            return self._generate_with_minimax(text, file_name, file_path)
        else:
            return self._generate_with_elevenlabs(text, file_name, file_path)

    def _generate_with_minimax(self, text: str, file_name: str, file_path: str) -> Optional[str]:
        if not self.mm_api_key:
            logger.warning("MINIMAX_API_KEY is missing. VoiceService will not generate audio. Running in dry-run mode.")
            return None

        logger.info(f"Generating audio with Minimax (Voice ID: {self.mm_voice_id})...")
        
        headers = {
            "Authorization": f"Bearer {self.mm_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "speech-01-hd",
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": self.mm_voice_id,
                "speed": 1.0,
                "vol": 3,
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
            # Minimax v2 requires GroupId as a query parameter
            url = f"{self.mm_base_url}?GroupId={self.mm_group_id}"
            logger.debug(f"Calling Minimax API at {url}")
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
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

    def _generate_with_elevenlabs(self, text: str, file_name: str, file_path: str) -> Optional[str]:
        if not self.el_api_key:
            logger.warning("ELEVENLABS_API_KEY is missing. VoiceService will not generate audio. Running in dry-run mode.")
            return None

        logger.info(f"Generating audio with ElevenLabs (Voice ID: {self.el_voice_id})...")

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
                "stability": 0.75,
                "similarity_boost": 0.85,
                "style": 0.5,
                "use_speaker_boost": True,
                "speed": 0.7
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
