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
        Generate a highly professional, personalized outreach message for WhatsApp.
        Interaction History: {customer.interaction_history}
        
        Rules for the message:
        - Write in CODE-MIXED script (Corporate Hinglish): Keep business terms in English Latin script (e.g., demo, AI solutions, support). 
        - Use Hindi (Devanagari) only for conversational grammar (e.g., आपने, के लिए, कैसे, तो, देखिए).
        - DO NOT translate tech/business terms into pure Hindi (Avoid: चर्चा, समाधान, आवश्यकताएं).
        - Use rich vocabulary but STRICTLY AVOID repeating words.
        - The tone should be highly professional, warm, and confident — exactly like Sanjeev Jain Sir speaking naturally on a voice note.
        
        CRITICAL RULES FOR PACING AND ANNOTATIONS (For Text-to-Speech Engine):
        - STRICTLY AVOID ending every sentence with "है" or "हैं". Vary the sentence endings naturally (e.g., end with "करते हैं", "बताओ", "ना", "सही रहेगा?").
        - DO NOT use ellipses (...) right after a word (e.g. avoid "hai..."). The voice engine will drag the sound out (like "haiiiii").
        - To create pauses, use commas (,) frequently. 
        - Use em-dashes with spaces around them ( — ) to show a slight shift in thought.
        - End sentences with standard full stops (.) or question marks (?) to ensure a clean cut-off and natural pause.        
        
        MESSAGE STRUCTURE (CRITICAL FOR RETENTION):
        - 1. THE HOOK (First 3-4 Seconds): Start with a very catchy, direct question or bold statement to grab immediate attention. (e.g., "देखिए — अगर आप अपने बिज़नेस को scale करना चाहते हैं, तो यह मैसेज आपके लिए है।")
        - 2. THE CORE VALUE (Next 10 Seconds): Explain exactly how you can help them based on their Interaction History.
        - Do NOT include the customer's name. Start directly with the hook.
        - Under 40 words. Keep it incredibly concise, high-energy, and punchy.
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
            f"Hello {customer.name}, I noticed your interest in '{customer.interaction_history}'. "
            f"I'd love to connect and discuss how we can help. Let's chat!"
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
