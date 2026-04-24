from pydantic import BaseModel, Field
from typing import Optional

class Customer(BaseModel):
    name: str = Field(..., description="Customer's full name")
    phone: str = Field(..., description="Customer's phone number")
    interaction_history: str = Field(..., description="Summary of past interactions")

class ProcessedCustomer(Customer):
    generated_message: str = Field(..., description="AI generated follow-up message")
    status: str = Field("pending", description="Processing status")
    delivery_status: str = Field("pending", description="Delivery status of the WhatsApp message")
    error_message: Optional[str] = Field(None, description="Error message if delivery failed")
    audio_url: Optional[str] = Field(None, description="URL of the generated personalized audio message")
