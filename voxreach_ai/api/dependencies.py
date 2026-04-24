from voxreach_ai.services.ai_service import ai_service
from voxreach_ai.services.data_processor import data_processor_service
from voxreach_ai.services.notification_service import notification_service
from voxreach_ai.services.voice_service import voice_service

def get_ai_service():
    return ai_service

def get_data_processor_service():
    return data_processor_service

def get_notification_service():
    return notification_service

def get_voice_service():
    return voice_service
