import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock environment variables for testing fallback
os.environ["AI_API_KEY"] = "dummy_key"
os.environ["AI_PROVIDER"] = "openrouter"

from voxreach_ai.services.ai_service import ai_service
from voxreach_ai.models.customer import Customer

def test_ai_fallback():
    print("Testing AI Service Fallback...")
    customer = Customer(
        name="John Doe",
        phone="1234567890",
        interaction_history="Interested in AI automation"
    )
    
    # This should trigger fallback because we used a dummy key
    message = ai_service.generate_outreach_message(customer)
    print(f"Resulting Message:\n{message}")
    
    if "Hi John Doe" in message:
        print("\nSUCCESS: Fallback logic working correctly.")
    else:
        print("\nFAILURE: Fallback logic did not return expected message.")

if __name__ == "__main__":
    test_ai_fallback()
