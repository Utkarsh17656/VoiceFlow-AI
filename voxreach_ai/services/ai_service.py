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

    def _g4f_call(self, prompt: str, system_message: str) -> str:
        import g4f
        response = g4f.ChatCompletion.create(
            model=g4f.models.default,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
        )
        return response.strip()

    def _openrouter_call(self, prompt: str, system_message: str) -> str:
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
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=15
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenRouter API Error: {response.status_code} - {response.text}")

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    def _execute_ai_call(self, prompt: str, system_message: str) -> str:
        if self.provider.lower() == "g4f":
            return self._g4f_call(prompt, system_message)
        else:
            return self._openrouter_call(prompt, system_message)

    def generate_outreach_message(self, customer: Customer) -> str:
        """
        Generates a personalized follow-up message with fallback logic.
        """
        prompt = f"""
        Generate a highly professional, personalized outreach voice note transcript for WhatsApp.
        Interaction History: {customer.interaction_history}
        
        CRITICAL SCRIPT RULES (STRICTLY ENFORCED):
        - ABSOLUTELY NO ROMANIZED HINDI OR HINGLISH SCRIPT. You are STRICTLY FORBIDDEN from using Roman letters for Hindi words.
        - Hindi words MUST be written ONLY in Devanagari script (e.g., "देखिए, अगर आप").
        - FORBIDDEN WORDS (Do NOT use): "mein", "hain", "aapke", "humare", "kya", "kaise", "hai", "nahi", "liye", "sakte". 
        - YOU MUST USE INSTEAD: "में", "हैं", "आपके", "हमारे", "क्या", "कैसे", "है", "नहीं", "लिए", "सकते".
        - Business/Tech terms MUST stay in English Latin script (e.g., "processes", "AI solutions", "boost").
        - DO NOT translate English business terms into pure Hindi (Avoid: "चर्चा", "समाधान").
        - DO NOT use any exclamation marks (!). They make the voice engine sound unnatural. Use double dashes (--) or periods (.) instead.
        
        MESSAGE STRUCTURE, TONE, AND VARIATION:
        - Hook: Start with a natural, varied greeting (e.g., "नमस्कार --", "Hello --", "Hi --") followed immediately by a catchy question based on their Interaction History. Do NOT always use the same exact opening.
        - Core Value: Explain how your AI solutions can help them.
        - Call to Action: End by directly asking for their availability so they reply instantly (e.g., "आज किस time बात करना सही रहेगा?", "आप free होकर कोई time बता दीजिये?", "What time works best for you?").
        - Do NOT include structural labels like "[Hook]" or "[Core Value]".
        - The message MUST be UNDER 35 WORDS total.
        
        PACING AND AUDIO RULES (FOR REALISTIC VOICE):
        - Add frequent commas (,) and double dashes (--) to force the voice engine to take natural pauses and speak slowly. This prevents the voice from sounding rushed.
        - STRICTLY AVOID ending every sentence with "है" or "हैं". Vary the endings so it sounds conversational and not like a robotic broadcast.
        
        CORRECT EXAMPLE OF EXPECTED STYLE (Use as inspiration, but vary the exact words):
        "नमस्कार -- क्या आप अपने कस्टमर सपोर्ट processes को revolutionize करना चाहते हैं, वो भी AI की power से? मैं आपके लिए बिलकुल सही AI solutions लेकर आया हूँ, जो आपके support operations को dramatically boost करेंगे -- आज किस time बात कर सकते हैं?"
        
        Now, generate a unique, highly natural message for the interaction history above. Make it sound like a spontaneous, thoughtful voice note from Sanjeev Jain Sir, taking natural pauses, and NOT like a static, repetitive template.
        """
        
        try:
            message = self._execute_ai_call(
                prompt=prompt, 
                system_message="You are a professional outreach assistant."
            )
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
        - ABSOLUTELY NO ROMANIZED HINDI OR HINGLISH SCRIPT. You are STRICTLY FORBIDDEN from using Roman letters for Hindi words.
        - FORBIDDEN WORDS (Do NOT use): "mein", "hain", "aapke", "humare", "kya", "kaise", "hai", "nahi", "liye", "sakte".
        - Do NOT write Hindi words in Roman letters (so "bilkul" is WRONG, "बिल्कुल" is CORRECT).
        - Do NOT write English words in Devanagari.
        - It will be spoken by Sanjeev Jain Sir via Text-to-Speech — write it exactly how HE would casually speak, warm but authoritative.
        - Keep it brief (under 30 words). No greeting needed — go straight to the reply.
        - Sound like a real voice note, NOT a formal message or AI response.
        """
        
        try:
            message = self._execute_ai_call(
                prompt=prompt,
                system_message="You are a friendly voice assistant for VoxReach."
            )
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
            f"Hello {customer.name}, मैंने देखा कि आप '{customer.interaction_history}' के बारे में enquire कर रहे थे। "
            f"मैं इसके बारे में आपसे detail में discuss करना चाहता हूँ। चलिए connect करते हैं!"
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
