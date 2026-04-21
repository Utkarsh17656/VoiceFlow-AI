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
    NOTIFICATION_PROVIDER: str = "cloud" # options: "twilio", "pywhatkit", "cloud"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""
    WHATSAPP_CLOUD_API_KEY: str = ""
    WHATSAPP_PHONE_ID: str = ""

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings():
    return Settings()
