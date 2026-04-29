from fastapi import FastAPI, Request, File, UploadFile, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from voxreach_ai.api.routes import router as api_router
from voxreach_ai.utils.config import get_settings
from voxreach_ai.utils.logger import logger
from voxreach_ai.api.dependencies import get_ai_service, get_data_processor_service, get_notification_service, get_voice_service

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info(f"Starting {settings.APP_NAME}...")
    yield
    # Shutdown logic
    logger.info(f"Shutting down {settings.APP_NAME}...")

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-ready backend for AI-powered customer outreach.",
        version="1.0.0",
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(api_router, prefix="/api/v1")

    return app

app = create_app()

static_dir = os.path.join(os.getcwd(), "voxreach_ai", "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

audio_dir = os.path.join(os.getcwd(), "audio")
if not os.path.exists(audio_dir):
    os.makedirs(audio_dir)
app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")

templates_dir = os.path.join(os.getcwd(), "voxreach_ai", "templates")
try:
    templates = Jinja2Templates(directory=templates_dir)
except Exception as e:
    logger.error(f"Failed to initialize templates: {e}")
    templates = None

@app.get("/")
async def home(request: Request):
    try:
        if templates:
            return templates.TemplateResponse(request=request, name="index.html", context={"request": request})
        return JSONResponse(content={"status": "VoxReach AI running", "error": "Templates missing"})
    except Exception as e:
        logger.error(f"Error rendering home template: {e}")
        return JSONResponse(content={"status": "VoxReach AI running", "error": str(e)})

@app.post("/", response_class=HTMLResponse)
async def process_outreach_ui(
    request: Request,
    file: UploadFile = File(None),
    send_as_template: bool = Form(False),
    google_sheet_url: str = Form(None),
    ai_service=Depends(get_ai_service),
    data_service=Depends(get_data_processor_service),
    notification_service=Depends(get_notification_service),
    voice_service=Depends(get_voice_service)
):
    # --- Validate: need at least one input source ---
    has_file = file and file.filename
    has_sheet = bool(google_sheet_url and google_sheet_url.strip())

    if not has_file and not has_sheet:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"request": request, "error_message": "Please upload a file (.csv / .xlsx) or provide a Google Sheets URL."}
        )

    # --- Validate file extension when a file is uploaded ---
    if has_file and not has_sheet:
        lower_name = file.filename.lower()
        if not (lower_name.endswith(".csv") or lower_name.endswith(".xlsx") or lower_name.endswith(".xls")):
            return templates.TemplateResponse(
                request=request,
                name="index.html",
                context={"request": request, "error_message": "Invalid file format. Please upload a .csv or .xlsx file."}
            )

    try:
        # --- Parse input via unified dispatcher ---
        if has_sheet:
            sheet_url = google_sheet_url.strip()
            logger.info(f"UI processing Google Sheet: {sheet_url}")
            customers = data_service.parse(sheet_url=sheet_url)
        else:
            content = await file.read()
            logger.info(f"UI received file: {file.filename} ({len(content)} bytes)")
            customers = data_service.parse(file_content=content, filename=file.filename)

        if not customers:
            return templates.TemplateResponse(
                request=request,
                name="index.html",
                context={"request": request, "error_message": "No valid customer records found. Check that phone numbers are present."}
            )

        processed_results = ai_service.process_batch(customers)
        
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
                        # Use settings.BASE_URL to ensure public URLs for Cloud API (e.g., ngrok)
                        base_url = settings.BASE_URL.rstrip('/')
                        # Fallback to request if settings.BASE_URL is default localhost but request is public
                        if "localhost" in base_url or "127.0.0.1" in base_url or "ngrok" in str(request.base_url):
                            base_url = str(request.base_url).rstrip('/')
                            
                        result.audio_url = f"{base_url}/audio/{audio_filename}"
                        audio_local_path = os.path.join(os.getcwd(), "audio", audio_filename)
                        logger.info(f"Audio URL generated: {result.audio_url}")
                        
                        # Send ONLY the audio
                        logger.info(f"Sending audio-only message to {result.phone}.")
                        success, error = notification_service.send_audio_message(result.phone, result.audio_url, audio_path=audio_local_path)
                    else:
                        # Fallback: audio generation failed, send plain text
                        logger.warning(f"Audio generation failed for {result.phone}. Falling back to plain text.")
                        success, error = notification_service.send_whatsapp_message(result.phone, result.generated_message)
                        
                result.delivery_status = "sent" if success else "failed"
                result.error_message = error
            else:
                result.delivery_status = "failed"
                result.error_message = "No message generated to send"
        
        total_processed = len(processed_results)
        sent_count = sum(1 for r in processed_results if getattr(r, 'delivery_status', '') == 'sent')
        failed_count = total_processed - sent_count

        return templates.TemplateResponse(
            request=request,
            name="index.html", 
            context={
                "request": request, 
                "results": processed_results,
                "total_processed": total_processed,
                "messages_sent": sent_count,
                "messages_failed": failed_count,
                "success_message": f"Successfully processed {total_processed} customers."
            }
        )
        
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        return templates.TemplateResponse(
            request=request,
            name="index.html", 
            context={"request": request, "error_message": str(e)}
        )
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        return templates.TemplateResponse(
            request=request,
            name="index.html", 
            context={"request": request, "error_message": "An internal error occurred during processing."}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("voxreach_ai.main:app", host="0.0.0.0", port=8000, reload=True)
