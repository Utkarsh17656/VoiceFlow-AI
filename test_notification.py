import os
from dotenv import load_dotenv

# Load env before importing services
load_dotenv()

from voxreach_ai.services.notification_service import notification_service

print("Testing Notification Service")
success, err = notification_service.send_whatsapp_message(
    phone="+1234567890", 
    message="Hello from VoxReach AI testing."
)
print("Success:", success)
print("Error:", err)
