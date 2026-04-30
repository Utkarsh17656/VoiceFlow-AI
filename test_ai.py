import asyncio
from voxreach_ai.services.ai_service import ai_service
from voxreach_ai.models.customer import Customer

customer = Customer(
    name="Test User",
    phone="1234567890",
    interaction_history="Asked about AI services."
)

try:
    message = ai_service.generate_outreach_message(customer)
    print("SUCCESS. Generated Message:")
    print(message)
except Exception as e:
    print("ERROR:", str(e))
