from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "VoxReach AI"
    DEBUG: bool = False
    
    # AI Configuration (OpenRouter/OpenAI)
    AI_PROVIDER: str = "openrouter"
    AI_API_KEY: str
    AI_BASE_URL: str = "https://openrouter.ai/api/v1"
    AI_MODEL: str = "google/gemini-2.0-flash-lite-preview-02-05:free"
    
    UPLOAD_DIR: str = "uploads"
    
    # Notifications Configuration
    NOTIFICATION_PROVIDER: str = "cloud" # options: "twilio", "cloud"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""
    WHATSAPP_CLOUD_API_KEY: str = ""
    WHATSAPP_PHONE_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "my_secure_webhook_token"
    BASE_URL: str = "http://localhost:8000"
    
    # ElevenLabs Configuration
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = ""
    
    # Voice Provider Choice ("elevenlabs" or "minimax")
    VOICE_PROVIDER: str = "elevenlabs"
    
    # Minimax Configuration
    MINIMAX_API_KEY: str = ""
    MINIMAX_GROUP_ID: str = ""
    MINIMAX_VOICE_ID: str = ""
    MINIMAX_BASE_URL: str = "https://api.minimax.io/v1/t2a_v2"


    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings():
    return Settings()
