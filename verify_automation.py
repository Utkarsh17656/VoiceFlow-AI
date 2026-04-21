
import os
from dotenv import load_dotenv

# Load env
load_dotenv()

from voxreach_ai.services.notification_service import notification_service

print("====================================================")
print("VOXREACH AI - AUTOMATION TEST")
print("====================================================")
print("WARNING: This will take control of your mouse/keyboard.")
print("1. Ensure WhatsApp Web is logged in on Microsoft Edge.")
print("2. DO NOT TOUCH the mouse/keyboard after pressing Enter.")
print("====================================================")

phone = input("Enter your phone number (with country code, e.g. +919999999999): ")
print("\nYou have 5 seconds to take your hands off the mouse...")
import time
time.sleep(5)

success, err = notification_service.send_whatsapp_message(
    phone=phone, 
    message="This is a test message from your VoiceFlow AI automation. It worked!"
)

if success:
    print("\nSUCCESS: Automation sequence completed.")
    print("If the message didn't send, ensure your browser was the active window.")
else:
    print(f"\nFAILED: {err}")
