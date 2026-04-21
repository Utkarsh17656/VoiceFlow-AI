import os
import uuid
import requests
from typing import Optional
from voxreach_ai.utils.config import get_settings
from voxreach_ai.utils.logger import logger

settings = get_settings()

class VoiceService:
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
        # Using a standard ElevenLabs voice ID (Rachel) as default
        self.default_voice_id = "21m00Tcm4TlvDq8ikWAM" 
        
        # Ensure the local 'audio' directory exists
        self.audio_dir = os.path.join(os.getcwd(), "audio")
        if not os.path.exists(self.audio_dir):
            os.makedirs(self.audio_dir)
            logger.info(f"Created audio directory at {self.audio_dir}")

    def generate_audio(self, text: str) -> Optional[str]:
        """
        Converts text to speech using ElevenLabs API and saves it locally.
        Returns the path to the generated audio file or None if it fails.
        """
        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY is missing. VoiceService will not generate audio. Running in dry-run mode.")
            return None

        logger.info("Generating audio with ElevenLabs...")
        
        file_name = f"{uuid.uuid4()}.mp3"
        file_path = os.path.join(self.audio_dir, file_name)

        url = f"{self.base_url}/text-to-speech/{self.default_voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
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
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                logger.info(f"Successfully generated and saved audio file: {file_path}")
                return file_path
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
