from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from typing import Tuple, Optional
from voxreach_ai.utils.config import get_settings
from voxreach_ai.utils.logger import logger

import requests

try:
    import pywhatkit
except ImportError:
    pywhatkit = None

settings = get_settings()

class NotificationService:
    def __init__(self):
        self.provider = settings.NOTIFICATION_PROVIDER.lower()
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_NUMBER
        
        self.client = None
        if self.provider == "twilio":
            if self.account_sid and self.auth_token:
                try:
                    self.client = Client(self.account_sid, self.auth_token)
                    logger.info("Twilio client initialized successfully.")
                except Exception as e:
                    logger.error(f"Failed to initialize Twilio client: {e}")
            else:
                logger.warning("Twilio credentials missing. NotificationService will not send messages via Twilio.")
        elif self.provider == "cloud":
            if settings.WHATSAPP_CLOUD_API_KEY and settings.WHATSAPP_PHONE_ID:
                logger.info("WhatsApp Cloud API provider initialized.")
            else:
                logger.warning("WhatsApp Cloud API credentials missing.")
        elif self.provider == "pywhatkit":
            if pywhatkit:
                logger.info("PyWhatKit provider initialized for browser automation.")
            else:
                logger.error("pywhatkit library not found. Please run 'pip install pywhatkit'.")

    def send_whatsapp_message(self, phone: str, message: str) -> Tuple[bool, Optional[str]]:
        """
        Sends a WhatsApp message using the configured provider (Twilio or pywhatkit).
        Returns a tuple of (Success: bool, ErrorMessage: Optional[str]).
        """
        if self.provider == "cloud":
            return self._send_via_cloud_api(phone, message)
        elif self.provider == "pywhatkit":
            return self._send_via_pywhatkit(phone, message)
        
        return self._send_via_twilio(phone, message)

    def _send_via_twilio(self, phone: str, message: str) -> Tuple[bool, Optional[str]]:
        if not self.client:
            logger.warning("Cannot send WhatsApp message: Twilio client missing or misconfigured.")
            return False, "Twilio configuration missing"

        try:
            to_number = f"whatsapp:{phone}" if not phone.startswith("whatsapp:") else phone
            from_whatsapp = f"whatsapp:{self.from_number}" if not self.from_number.startswith("whatsapp:") else self.from_number

            msg = self.client.messages.create(
                body=message,
                from_=from_whatsapp,
                to=to_number
            )
            logger.info(f"WhatsApp message sent successfully to {phone} via Twilio. SID: {msg.sid}")
            return True, None
            
        except TwilioRestException as e:
            logger.error(f"Twilio API Error sending WhatsApp to {phone}: {e.msg}")
            return False, e.msg
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp to {phone}: {str(e)}")
            return False, str(e)

    def _send_via_cloud_api(self, phone: str, message: str) -> Tuple[bool, Optional[str]]:
        if not settings.WHATSAPP_CLOUD_API_KEY or not settings.WHATSAPP_PHONE_ID:
            logger.warning("Cannot send WhatsApp message: Cloud API credentials missing.")
            return False, "WhatsApp Cloud API credentials missing"
            
        target_phone = phone.replace("+", "").strip()
        url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_CLOUD_API_KEY}",
            "Content-Type": "application/json"
        }
        # Standard dynamic text message (use this once conversation is open/approved)
        # payload = {
        #     "messaging_product": "whatsapp",
        #     "to": target_phone,
        #     "type": "text",
        #     "text": {"body": message}
        # }
        
        # Test Template message "test123" to circumvent 24-hour window restrictions
        payload = {
            "messaging_product": "whatsapp",
            "to": target_phone,
            "type": "template",
            "template": {
                "name": "test123",
                "language": {
                    "code": "en"
                }
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"WhatsApp message sent successfully to {phone} via Cloud API.")
            return True, None
        except requests.exceptions.HTTPError as e:
            err_msg = response.json().get("error", {}).get("message", str(e)) if response.text else str(e)
            logger.error(f"Cloud API Error sending WhatsApp to {phone}: {err_msg}")
            return False, err_msg
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp via Cloud API: {str(e)}")
            return False, str(e)

    def _send_via_pywhatkit(self, phone: str, message: str) -> Tuple[bool, Optional[str]]:
        if not pywhatkit:
            return False, "pywhatkit library not installed"
    
        try:
            # Normalize phone number (ensure it starts with +)
            target_phone = phone if phone.startswith("+") else f"+{phone.strip()}"
            
            logger.info(f"Preparing to send WhatsApp message to {target_phone} via pywhatkit (Edge/Browser)...")
            
            # sendwhatmsg_instantly(phone_no, message, wait_time=15, tab_close=True, close_time=10)
            # - wait_time: seconds to wait before typing the message (allows browser to load)
            # - tab_close: close the tab after sending
            # - close_time: seconds to wait before closing the tab
            pywhatkit.sendwhatmsg_instantly(
                phone_no=target_phone,
                message=message,
                wait_time=15,
                tab_close=True,
                close_time=10
            )
            
            logger.info(f"Success: Automation completed for {target_phone}. Tab will close in 10s.")
            return True, None
            
        except Exception as e:
            logger.error(f"PyWhatKit error for {phone}: {str(e)}")
            return False, str(e)

notification_service = NotificationService()