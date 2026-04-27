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
        Generate a personalized outreach message for WhatsApp for:
        Name: {customer.name}
        Interaction History: {customer.interaction_history}
        
        Rules for the message:
        - Write in CODE-MIXED script: Hindi words MUST be written in Devanagari (e.g., यार, देखो, बात, तुमने, करते हैं, कब, बताओ), and English words MUST stay in English Latin script (e.g., demo, AI, connect, solution, support, request, follow up).
        - Do NOT write Hindi words in Roman/English letters (so "yaar" is WRONG, "यार" is CORRECT).
        - Do NOT write English words in Devanagari (so "डेमो" is WRONG, "demo" is CORRECT).
        - The tone should be warm, confident, and personal — exactly like Sanjeev Jain Sir personally reaching out to a prospect.
        - The message MUST reference the Interaction History above — base it on what the customer actually asked or did.
        - Under 50 words. Keep it conversational and punchy.
        - Do NOT start with a generic greeting like "नमस्ते" or "Hello". Get to the point naturally.
        - Do NOT use any signature, placeholder, or closing like [Your Name] or [Company Name].
        - Sound like a real WhatsApp voice note from a trusted senior professional.
        
        Example format: "यार, तुमने AI customer support के बारे में बात की थी — demo भी request किया था। तो connect करते हैं और मैं exactly show करूँगा कैसे काम करता है। बताओ कब free हो?"
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
        - Write in CODE-MIXED script: Hindi words MUST be written in Devanagari (e.g., बिल्कुल, हाँ, देखो, अच्छा, ठीक है, ज़रूर), and English words MUST stay in English Latin script (e.g., absolutely, sure, connect, team, let me know).
        - Do NOT write Hindi words in Roman letters (so "bilkul" is WRONG, "बिल्कुल" is CORRECT).
        - Do NOT write English words in Devanagari.
        - It will be spoken by Sanjeev Jain Sir via Text-to-Speech — write it exactly how HE would casually speak, warm but authoritative.
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
