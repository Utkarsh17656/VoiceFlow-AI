from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from typing import Tuple, Optional
from voxreach_ai.utils.config import get_settings
from voxreach_ai.utils.logger import logger

import requests
import os


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

    def send_whatsapp_message(self, phone: str, message: str, is_template: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Sends a WhatsApp message using the configured provider (Twilio or pywhatkit).
        Returns a tuple of (Success: bool, ErrorMessage: Optional[str]).
        """
        if self.provider == "cloud":
            return self._send_via_cloud_api(phone, message, is_template=is_template)
        
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

    def _send_via_cloud_api(self, phone: str, message: str, is_template: bool = False) -> Tuple[bool, Optional[str]]:
        if not settings.WHATSAPP_CLOUD_API_KEY or not settings.WHATSAPP_PHONE_ID:
            logger.warning("Cannot send WhatsApp message: Cloud API credentials missing.")
            return False, "WhatsApp Cloud API credentials missing"
            
        target_phone = phone.replace("+", "").strip()
        url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_CLOUD_API_KEY}",
            "Content-Type": "application/json"
        }
        
        if is_template:
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

        else:
            # Standard dynamic text message
            payload = {
                "messaging_product": "whatsapp",
                "to": target_phone,
                "type": "text",
                "text": {"body": message}
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

    def send_audio_message(self, phone: str, audio_url: str, audio_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Sends an audio message (MP3) directly to the user via WhatsApp Cloud API.
        If audio_path is provided, it uploads the media natively to circumvent localhost restrictions.
        For PyWhatKit or Twilio, it sends the audio URL as a text message since native audio upload requires specific media endpoints.
        """
        if self.provider == "twilio":
            logger.info("Sending audio URL via Twilio as text message.")
            # Note: Twilio can support media_url for WhatsApp, but text fallback is safer if media fails.
            return self._send_via_twilio(phone, f"🎤 Please listen to your personalized message here: {audio_url}")
            
        elif self.provider == "cloud":
            if not settings.WHATSAPP_CLOUD_API_KEY or not settings.WHATSAPP_PHONE_ID:
                logger.warning("Cannot send WhatsApp audio: Cloud API credentials missing.")
                return False, "WhatsApp Cloud API credentials missing"
                
            target_phone = phone.replace("+", "").strip()
            
            media_id = None
            if audio_path and os.path.exists(audio_path):
                upload_url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_ID}/media"
                upload_headers = {"Authorization": f"Bearer {settings.WHATSAPP_CLOUD_API_KEY}"}
                
                try:
                    logger.info(f"Uploading audio file natively to Meta Cloud API: {audio_path}")
                    with open(audio_path, 'rb') as f:
                        files = {'file': (os.path.basename(audio_path), f, 'audio/mpeg')}
                        data = {'messaging_product': 'whatsapp', 'type': 'audio/mpeg'}
                        
                        upload_resp = requests.post(upload_url, headers=upload_headers, files=files, data=data)
                        upload_resp.raise_for_status()
                        media_id = upload_resp.json().get('id')
                        logger.info(f"Media uploaded successfully. Media ID: {media_id}")
                except Exception as e:
                    logger.error(f"Failed to upload media natively: {str(e)}. Falling back to link.")
            
            url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_ID}/messages"
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_CLOUD_API_KEY}",
                "Content-Type": "application/json"
            }
            
            if media_id:
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": target_phone,
                    "type": "audio",
                    "audio": {"id": media_id}
                }
            else:
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": target_phone,
                    "type": "audio",
                    "audio": {"link": audio_url}
                }
            
            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                logger.info(f"WhatsApp audio message sent successfully to {phone} via Cloud API.")
                return True, None
            except requests.exceptions.HTTPError as e:
                err_msg = response.json().get("error", {}).get("message", str(e)) if response.text else str(e)
                logger.error(f"Cloud API Error sending audio to {phone}: {err_msg}")
                return False, err_msg
            except Exception as e:
                logger.error(f"Unexpected error sending audio via Cloud API: {str(e)}")
                return False, str(e)
                
        return False, f"Unsupported provider for audio messages: {self.provider}"


notification_service = NotificationService()
