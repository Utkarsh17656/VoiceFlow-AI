from fastapi import FastAPI, Request, File, UploadFile, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from voxreach_ai.api.routes import router as api_router
from voxreach_ai.utils.config import get_settings
from voxreach_ai.utils.logger import logger
from voxreach_ai.api.dependencies import get_ai_service, get_data_processor_service, get_notification_service

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

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def process_outreach_ui(
    request: Request,
    file: UploadFile = File(...),
    ai_service=Depends(get_ai_service),
    data_service=Depends(get_data_processor_service),
    notification_service=Depends(get_notification_service)
):
    if not file.filename.endswith('.csv'):
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error_message": "Invalid file format. Please upload a CSV."}
        )

    try:
        content = await file.read()
        logger.info(f"UI received file: {file.filename}")
        
        customers = data_service.parse_csv(content)
        processed_results = ai_service.process_batch(customers)
        
        for result in processed_results:
            if result.generated_message:
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
            "index.html", 
            {
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
            "index.html", 
            {"request": request, "error_message": str(e)}
        )
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error_message": "An internal error occurred during processing."}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("voxreach_ai.main:app", host="0.0.0.0", port=8000, reload=True)
