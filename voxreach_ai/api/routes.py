from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from typing import List
import uuid
from voxreach_ai.api.dependencies import get_ai_service, get_data_processor_service, get_notification_service
from voxreach_ai.models.message import OutreachBatchResponse, HealthCheckResponse
from voxreach_ai.utils.logger import logger

router = APIRouter()

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    return HealthCheckResponse(status="healthy")

@router.post("/process-outreach", response_model=OutreachBatchResponse)
async def process_outreach(
    file: UploadFile = File(...),
    ai_service=Depends(get_ai_service),
    data_service=Depends(get_data_processor_service),
    notification_service=Depends(get_notification_service)
):
    """
    Upload a CSV and generate personalized outreach messages.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV.")

    try:
        content = await file.read()
        logger.info(f"Received file: {file.filename}")
        
        # 1. Parse CSV
        customers = data_service.parse_csv(content)
        
        # 2. Process with AI
        processed_results = ai_service.process_batch(customers)
        
        # 3. Send Notifications
        for result in processed_results:
            if result.generated_message:
                success, error = notification_service.send_whatsapp_message(result.phone, result.generated_message)
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
