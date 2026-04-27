# VoxReach AI 🚀

VoxReach AI is a production-ready, highly automated outreach platform that combines AI text generation, voice cloning, and WhatsApp delivery to create hyper-personalized, conversational voice notes at scale.

## 🌟 Key Features

*   **Multi-Source Data Ingestion:** Upload `.csv` or `.xlsx` files, or simply paste a public **Google Sheets URL** directly into the dashboard.
*   **Hyper-Personalized AI Engine:** Generates natural, code-mixed (Hindi + English) conversational messages based on a prospect's specific interaction history.
*   **Premium Voice Cloning:** Integrates with **ElevenLabs Multilingual v2** (and Minimax) to generate lifelike audio using a custom cloned voice.
*   **Smart Audio Caching:** Automatically hashes the AI-generated message text to deduplicate audio generation. If multiple users require the exact same message, the audio is reused, drastically cutting down on API costs.
*   **Native WhatsApp Delivery:** Uses the **Meta Cloud API** (with fallbacks to Twilio and PyWhatKit) to silently open 24-hour windows (via templates) and deliver native audio messages.

## 🛠️ Architecture

The backend is built with **FastAPI** for high performance and modularity, divided into specialized services:
*   `DataProcessorService`: Standardizes inputs from CSV, Excel, and Google Sheets.
*   `AIService`: Prompts the LLM (via OpenRouter/g4f) to generate contextual outreach text.
*   `VoiceService`: Interfaces with TTS providers (ElevenLabs/Minimax) and handles local caching.
*   `NotificationService`: Manages Meta Graph API authentication and native media uploads.

## 🚀 Getting Started

### Prerequisites
*   Python 3.12+
*   Meta Developer Account (for WhatsApp Cloud API credentials)
*   ElevenLabs Account (for Voice Generation)
*   OpenRouter Account (for AI text generation)

### Installation

1.  **Clone the repository** and navigate to the project folder.
2.  **Create a virtual environment** and activate it:
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

Create a `.env` file in the root directory based on the following structure:

```env
APP_NAME="VoxReach AI"
DEBUG=True

# AI Configuration
AI_PROVIDER="openrouter"
AI_API_KEY="your_openrouter_api_key"
AI_BASE_URL="https://openrouter.ai/api/v1"
AI_MODEL="google/gemini-2.0-flash-lite-preview-02-05:free"

# Voice Generation
VOICE_PROVIDER="elevenlabs"
ELEVENLABS_API_KEY="your_elevenlabs_api_key"
ELEVENLABS_VOICE_ID="your_custom_voice_id"

# WhatsApp Cloud API
NOTIFICATION_PROVIDER="cloud"
WHATSAPP_CLOUD_API_KEY="your_meta_system_user_access_token"
WHATSAPP_PHONE_ID="your_whatsapp_phone_id"
```
*(Note: Meta temporary tokens expire every 24 hours. For production, generate a permanent System User token).*

### Running the Application

Start the FastAPI server:
```bash
uvicorn voxreach_ai.main:app --host 0.0.0.0 --port 8000 --reload
```
Then, open your browser and navigate to `http://localhost:8000` to access the Smart Outreach Dashboard.

## 💡 Usage Guide

1.  **Prepare your Data:** Ensure your data source has the columns `name`, `phone` (with country code), and `interaction_history`.
2.  **Select Source:** Drag & drop your file or paste a Google Sheets link.
3.  **24-Hour Window Rule:** 
    *   If you have *not* interacted with the user in the last 24 hours, check **"Send as Initial Template"** to open the session.
    *   If the user *has* replied recently, leave it unchecked to send only the personalized audio.
4.  **Process:** Click "Process Outreach". The system will generate AI text, convert it to speech (or reuse cache), upload the media to Meta, and send it directly to the customer's WhatsApp.

## 🛡️ License & Security
Do not commit your `.env` file containing API keys to version control. Ensure your WhatsApp Cloud API keys are kept secure and rotated if compromised.
