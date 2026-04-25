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
        Generate a strict and angry message for WhatsApp for a team member:
        Name: {customer.name}
        
        Core Message: "Please come on time to the team meetings."
        
        Rules for the message:
        - Write in natural HINGLISH — a casual, realistic mix of Hindi and English the way educated Indian professionals actually speak and text.
        - Use Hindi (in Roman script, NOT Devanagari) for emotions, everyday words, and connecting phrases. Example: "yaar", "bhai", "ek baar", "kab se", "seedha baat".
        - Use English naturally for technical or formal terms. Example: "meeting", "time", "professional", "seriously", "expectations".
        - The tone must be ANGRY and STRICT — like Sanjeev Jain Sir who is genuinely frustrated and upset about lateness.
        - Under 40 words. Keep it punchy and direct.
        - Do NOT start with "Hello" or any greeting. Go straight to the point.
        - Do NOT use any signature, placeholder, or closing like [Your Name].
        - Sound like a real WhatsApp voice note from a senior — NOT like a formal letter or an AI chatbot.
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

    def generate_reply_message(self, incoming_msg: str, sender_name: str = "there") -> str:
        """
        Generates a quick, conversational audio-native response to an incoming user message.
        """
        prompt = f"""
        A user named {sender_name} just sent the following message to our AI agent:
        ---
        {incoming_msg}
        ---
        
        Generate a friendly, natural, and concise reply.
        Rules:
        - Write in natural HINGLISH — a mix of casual Hindi (Roman script, NOT Devanagari) and English, exactly how an educated Indian professional speaks in real life.
        - Use Hindi for warmth and emotion: words like "bilkul", "haan", "dekho", "acha", "theek hai", "zaroor".
        - Use English naturally for context and clarity: "absolutely", "sure", "let me know", "connect", "team".
        - It will be spoken by Sanjeev Jain Sir via Text-to-Speech — write it like how HE would casually speak, warm but authoritative.
        - Keep it brief (under 30 words). No greeting needed — go straight to the reply.
        - Sound like a real voice note, NOT a formal message or AI response.
        """
        
        try:
            if self.provider.lower() == "g4f":
                import g4f
                response = g4f.ChatCompletion.create(
                    model=g4f.models.gpt_4,
                    messages=[
                        {"role": "system", "content": "You are a friendly voice assistant for VoxReach."},
                        {"role": "user", "content": prompt}
                    ]
                )
                message = response.strip()
                logger.info(f"Generated voice reply via g4f")
                return message

            # OpenRouter / Standard OpenAI payload
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
                        {"role": "system", "content": "You are a friendly voice assistant for VoxReach."},
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=15
            )
            
            if response.status_code != 200:
                logger.error(f"AI API Error on reply: {response.status_code} - {response.text}")
                return "I'm sorry, I'm having a little trouble thinking of what to say right now!"

            data = response.json()
            message = data["choices"][0]["message"]["content"].strip()
            logger.info(f"Generated voice reply via {self.provider}")
            return message

        except Exception as e:
            logger.error(f"Processing Error generating reply: {str(e)}")
            return "Thanks for your message! I'll get back to you shortly."

    def _generate_fallback_message(self, customer: Customer) -> str:
        """
        Fault-tolerant fallback: Returns a high-quality standard message if AI fails.
        """
        return (
            f"{customer.name}, मीटिंग में समय पर आना सीखो! "
            f"देरी अब बर्दाश्त नहीं की जाएगी। अगली बार से वक्त का ध्यान रखो।"
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
