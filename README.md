# Felix Hospital - LiveKit Voice AI Agent

A production-ready voice AI appointment booking agent for Felix Hospital built with LiveKit Agents framework.

## Features

- 🎙️ Natural Hindi-English voice conversations
- 🏥 Appointment booking workflow
- 🧠 Living Memory system (never forgets patient info)
- 🔄 Multi-agent architecture with handoffs
- 📋 Mock Felix Hospital API with sample doctors/slots
- 🧪 Fully testable via LiveKit playground

## Quick Start

### 1. Install Dependencies

```bash
cd livekit_workflows
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your LiveKit credentials and OpenAI API key
```

### 3. Run the Agent

```bash
# Development mode
python src/main.py dev

# Production mode
python src/main.py start
```

### 4. Test the Agent

**Option 1: LiveKit Playground**
- Go to https://agents-playground.livekit.io/
- Enter your LiveKit credentials
- Connect and start talking!

**Option 2: Console Mode**
```bash
python src/main.py dev
```

## Mock Data

The agent includes mock Felix Hospital data:
- **5 Doctors**: Cardiology, Orthopedics, General Medicine specialists
- **Available Slots**: Next 7 days, 9 AM - 5 PM
- **Facilities**: Noida (Sector 137), Greater Noida (Gamma 1)

## Example Conversation

```
Agent: नमस्ते! Felix Hospital से बात हो रही है। बताइए, क्या help चाहिए?
You: Appointment book karni hai

Agent: ठीक है। किस problem के लिए appointment चाहिए?
You: Chest pain hai

Agent: समझ गई। Patient का नाम?
You: Rohit Kumar

Agent: Age?
You: 35

Agent: Noida आएंगे या Greater Noida?
You: Noida

Agent: एक second, मैं Cardiology doctor की availability check कर रही हूँ...

Agent: Dr. Rajesh Sharma Tuesday को available हैं। Ten AM या eleven AM, book कर दूं?
You: Ten AM

Agent: Perfect! Rohit Kumar की appointment confirm हो गई।
```

## Environment Variables

```bash
# Required
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
OPENAI_API_KEY=sk-your-key
```

---

Built by Pype AI for Felix Hospital
