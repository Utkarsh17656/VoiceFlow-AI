import os
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Query, Response, BackgroundTasks, Form
from typing import List, Dict, Any
import uuid
from voxreach_ai.api.dependencies import get_ai_service, get_data_processor_service, get_notification_service, get_voice_service
from fastapi import Request
from voxreach_ai.models.message import OutreachBatchResponse, HealthCheckResponse
from voxreach_ai.utils.config import get_settings

settings = get_settings()
from voxreach_ai.utils.logger import logger

router = APIRouter()

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    return HealthCheckResponse(status="healthy")

@router.post("/process-outreach", response_model=OutreachBatchResponse)
async def process_outreach(
    request: Request,
    file: UploadFile = File(None),
    send_as_template: bool = Form(False),
    google_sheet_url: str = Form(None),
    ai_service=Depends(get_ai_service),
    data_service=Depends(get_data_processor_service),
    notification_service=Depends(get_notification_service),
    voice_service=Depends(get_voice_service)
):
    """
    Generate personalized outreach messages from multiple input sources:
      - CSV file  (.csv)
      - Excel file (.xlsx)
      - Google Sheets public CSV export URL (via google_sheet_url form field)

    When google_sheet_url is supplied it takes precedence over an uploaded file.
    """
    # --- Validate that at least one input source was provided ---
    if not google_sheet_url and (file is None or not file.filename):
        raise HTTPException(
            status_code=400,
            detail="Provide either a file (.csv / .xlsx) or a google_sheet_url.",
        )

    # --- Validate uploaded file extension when no Sheet URL given ---
    if not google_sheet_url and file and file.filename:
        lower_name = file.filename.lower()
        if not (lower_name.endswith(".csv") or lower_name.endswith(".xlsx") or lower_name.endswith(".xls")):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Please upload a .csv or .xlsx file.",
            )

    try:
        # 1. Parse input — dispatch to correct reader
        if google_sheet_url:
            logger.info(f"Processing Google Sheet URL: {google_sheet_url}")
            customers = data_service.parse(sheet_url=google_sheet_url)
        else:
            content = await file.read()
            logger.info(f"Received file: {file.filename} ({len(content)} bytes)")
            customers = data_service.parse(file_content=content, filename=file.filename)

        if not customers:
            raise HTTPException(
                status_code=422,
                detail="No valid customer records found in the provided input.",
            )
        
        # 2. Process with AI
        processed_results = ai_service.process_batch(customers)
        
        # 3. Send Notifications
        for result in processed_results:
            if result.generated_message:
                if send_as_template:
                    logger.info(f"Sending as template to {result.phone}, skipping audio.")
                    result.audio_url = None
                    success, error = notification_service.send_whatsapp_message(
                        result.phone, 
                        result.generated_message, 
                        is_template=True
                    )
                else:
                    audio_filename = voice_service.generate_audio(result.generated_message, cache_key=result.interaction_history)
                    if audio_filename:
                        # Use settings.BASE_URL to ensure public URLs for Cloud API
                        base_url = settings.BASE_URL.rstrip('/')
                        if "localhost" in base_url and "127.0.0.1" in base_url and "ngrok" in str(request.base_url):
                            base_url = str(request.base_url).rstrip('/')
                            
                        result.audio_url = f"{base_url}/audio/{audio_filename}"
                        audio_local_path = os.path.join(os.getcwd(), "audio", audio_filename)
                        logger.info(f"Audio URL generated: {result.audio_url}")
                        
                        # 1. Send the text message first
                        message_to_send = f"Hello {result.name},\n\n{result.generated_message}"
                        success_text, error_text = notification_service.send_whatsapp_message(result.phone, message_to_send)
                        
                        # 2. Send the native audio message
                        success_audio, error_audio = notification_service.send_audio_message(result.phone, result.audio_url, audio_path=audio_local_path)
                        
                        # Check overall success
                        success = success_text and success_audio
                        error = error_audio if not success_audio else error_text
                    else:
                        message_to_send = result.generated_message
                        logger.info(f"Final outreach message for {result.phone}: {message_to_send}")
                        success, error = notification_service.send_whatsapp_message(result.phone, message_to_send)

                result.delivery_status = "sent" if success else "failed"
                result.error_message = error
            else:
                result.delivery_status = "failed"
                result.error_message = "No message generated to send"
        
        # 4. Prepare response
        return OutreachBatchResponse(
            batch_id=str(uuid.uuid4()),
            total_processed=len(processed_results),
            results=processed_results
        )
        
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal error occurred during processing.")

@router.get("/webhook")
async def verify_webhook(
    request: Request,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Webhook verification endpoint for Meta API.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully!")
        return Response(content=hub_challenge, status_code=200)
    logger.warning("Failed webhook verification attempt.")
    raise HTTPException(status_code=403, detail="Invalid verify token")

def process_incoming_message(
    sender_phone: str, 
    message_text: str, 
    sender_name: str, 
    ai_service, 
    voice_service, 
    notification_service
):
    """
    Background task to process the incoming message, generate AI reply, 
    synthesize speech, and send it as an audio message.
    """
    logger.info(f"Processing background reply for {sender_phone}: '{message_text}'")
    
    # 1. Generate text reply
    reply_text = ai_service.generate_reply_message(message_text, sender_name)
    logger.info(f"AI generated text reply: {reply_text}")
    
    # 2. Generate audio
    audio_filename = voice_service.generate_audio(reply_text)
    
    if audio_filename:
        # Use settings.BASE_URL to construct the absolute public URL for the audio file
        base_url = settings.BASE_URL.rstrip('/')
        audio_url = f"{base_url}/audio/{audio_filename}"
        
        # 3. Send back to user via audio payload
        logger.info(f"Sending audio response via WhatsApp API: {audio_url}")
        success, error = notification_service.send_audio_message(sender_phone, audio_url)
        
        if success:
            logger.info(f"Successfully auto-replied with audio to {sender_phone}")
        else:
            logger.error(f"Failed to auto-reply to {sender_phone}: {error}")
    else:
        logger.error("Audio generation failed for auto-reply. Falling back to nothing.")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    ai_service=Depends(get_ai_service),
    notification_service=Depends(get_notification_service),
    voice_service=Depends(get_voice_service)
):
    """
    Receive incoming messages from WhatsApp Cloud API.
    """
    try:
        body = await request.json()
        
        # Parse Meta's webhook payload
        if body.get("object") == "whatsapp_business_account":
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Only process messages, ignore statuses
                    if "messages" in value:
                        msg = value["messages"][0]
                        sender_phone = msg.get("from")
                        
                        # Extract sender name
                        contacts = value.get("contacts", [{}])
                        sender_name = contacts[0].get("profile", {}).get("name", "there")
                        
                        if msg.get("type") == "text":
                            message_text = msg.get("text", {}).get("body", "")
                            
                            logger.info(f"Received webhook message from {sender_name} ({sender_phone}): {message_text}")
                            
                            # Offload to background task to instantly 200 OK Meta's webhook
                            background_tasks.add_task(
                                process_incoming_message,
                                sender_phone,
                                message_text,
                                sender_name,
                                ai_service,
                                voice_service,
                                notification_service
                            )
                        else:
                            logger.info(f"Received non-text message type: {msg.get('type')}")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        # Even on parsing error, return 200 so Meta doesn't retry endlessly
        return {"status": "success"}
