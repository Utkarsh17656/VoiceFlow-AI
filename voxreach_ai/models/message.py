from pydantic import BaseModel
from typing import List
from .customer import ProcessedCustomer

class OutreachBatchResponse(BaseModel):
    batch_id: str
    total_processed: int
    results: List[ProcessedCustomer]

class HealthCheckResponse(BaseModel):
    status: str
    version: str = "1.0.0"
