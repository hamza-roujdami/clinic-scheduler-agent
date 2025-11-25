# Clinic Scheduler Agent

> **⚠️ Demo Purpose Only**  
> This is a **proof-of-concept demonstration** showcasing multi-agent architecture with Microsoft Agent Framework and Microsoft Foundry. It is **not production-ready code** and uses mock data for testing purposes. For production deployment, replace mock implementations with real APIs, add proper error handling, security measures, and scalability considerations.

Multi-agent system for **Cleveland Clinic Abu Dhabi** appointment scheduling using **Microsoft Agent Framework** and **Azure Foundry**.

## Architecture

```
User Message → Supervisor Agent (LLM routing)
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
    RAG Agent              Booking Agent
  (Info queries)         (Appointments)
```

**3 Agents:**
- **Supervisor**: Uses LLM to classify intent and route to appropriate agent(s)
- **RAG Agent**: Answers questions about hours, doctors, insurance, services, location
- **Booking Agent**: Handles check availability, book, cancel, reschedule

## Setup

### Prerequisites
- Python 3.10+
- Azure CLI (`az login`)
- Azure Foundry with model deployment

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt --pre

# Configure .env file (see .env.example)
cp .env.example .env
# Edit .env with your Azure Foundry endpoint and model name
```

### Run Web UI

```bash
# Start Gradio web interface
python app.py

# Open http://localhost:7860 in browser
```

### Run Tests

```bash
# Test supervisor routing
python agents/supervisor.py

# Test RAG agent
python agents/rag_agent.py

# Test booking agent
python agents/booking_agent.py
```

## Demo Prompts

Try these prompts in the web UI to see the routing in action:

### Simple Info Queries (→ RAG Agent only)
```
What are your clinic hours?
Do you accept Daman insurance?
I need to see a cardiologist who speaks Arabic
What services do you offer?
Where is Cleveland Clinic Abu Dhabi located?
```

### Simple Booking Queries (→ Booking Agent only)
```
Book an appointment with Dr. Smith
Check availability for tomorrow
Cancel my appointment #CONF12345
I need to reschedule my appointment
```

### Complex Queries (→ Both agents)
```
Do you accept ADNIC insurance and can I book for Sunday?
I need a cardiologist, do you accept Daman and can I schedule this week?
What are your hours and book me with Dr. Al Blooshi for Thursday
```

### Greeting (→ Welcome message)
```
Hello
Hi there
Help
```

## Project Structure

```
agents/
  ├── supervisor.py      # LLM-powered routing
  ├── rag_agent.py       # Clinic info (5 tools)
  └── booking_agent.py   # Appointments (4 tools)
.env                     # Azure Foundry config
requirements.txt         # Dependencies
```

## How It Works

1. **User sends message** → Supervisor receives it
2. **LLM classifies intent** → `{needs_info, needs_booking, is_greeting}`
3. **Routing decision**:
   - Info only → RAG Agent
   - Booking only → Booking Agent  
   - Both → Call both agents
   - Greeting → Welcome message
4. **Agent(s) use tools** → LLM calls appropriate functions
5. **Response returned** → User gets answer

## Next Steps

- [ ] Replace mock booking tools with real API
- [ ] Add Azure AI Search for RAG
- [ ] Add conversation history/threading
- [ ] Build WhatsApp interface
- [ ] Deploy to production
