import requests
import g4f
from voxreach_ai.models.customer import Customer, ProcessedCustomer
from voxreach_ai.utils.config import get_settings
from voxreach_ai.utils.logger import logger
from typing import List

settings = get_settings()

class AIService:
    def __init__(self):
        self.base_url = settings.AI_BASE_URL
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL
        self.provider = settings.AI_PROVIDER

    def generate_outreach_message(self, customer: Customer) -> str:
        """
        Generates a personalized follow-up message with fallback logic.
        """
        prompt = f"""
        Generate a personalized, conversational outreach message for WhatsApp for:
        Name: {customer.name}
        History: {customer.interaction_history}
        
        Rules for WhatsApp:
        - Very conversational and friendly.
        - Under 60 words.
        - NO subject lines.
        - NO signature placeholders like [Your Name] or [Company Name]. Just end with a simple closing question or call-to-action.
        """
        
        try:
            if self.provider.lower() == "g4f":
                import g4f
                response = g4f.ChatCompletion.create(
                    model=g4f.models.gpt_4,
                    messages=[
                        {"role": "system", "content": "You are a professional outreach assistant."},
                        {"role": "user", "content": prompt}
                    ]
                )
                message = response.strip()
                logger.info(f"Generated message for {customer.name} via {self.provider}")
                return message

            # PRO Structure: Using requests for maximum control over headers (OpenRouter compliance)
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "VoxReach AI"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a professional outreach assistant."},
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=15
            )
            
            if response.status_code != 200:
                logger.error(f"AI API Error: {response.status_code} - {response.text}")
                return self._generate_fallback_message(customer)

            data = response.json()
            message = data["choices"][0]["message"]["content"].strip()
            logger.info(f"Generated message for {customer.name} via {self.provider}")
            return message

        except Exception as e:
            logger.error(f"Processing Error for {customer.name}: {str(e)}")
            return self._generate_fallback_message(customer)

    def _generate_fallback_message(self, customer: Customer) -> str:
        """
        Fault-tolerant fallback: Returns a high-quality standard message if AI fails.
        """
        return (
            f"Hi {customer.name}, we've been following your recent interest in our services. "
            f"We'd love to discuss how we can help you scale based on your history with us. "
            f"Are you available for a quick chat this week?"
        )

    def process_batch(self, customers: List[Customer]) -> List[ProcessedCustomer]:
        """
        Processes a list of customers and generates messages for each.
        """
        results = []
        for customer in customers:
            message = self.generate_outreach_message(customer)
            processed = ProcessedCustomer(
                **customer.model_dump(),
                generated_message=message,
                status="completed" if "fallback" not in message else "fallback"
            )
            results.append(processed)
        return results

ai_service = AIService()
