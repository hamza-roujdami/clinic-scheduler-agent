"""
Clinic Scheduler Agent - Gradio Web UI
Run with: python app.py
"""

import asyncio
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

# Lazy-load supervisor to avoid slow startup
_supervisor = None


def get_supervisor():
    """Get or create supervisor instance."""
    global _supervisor
    if _supervisor is None:
        print("🚀 Initializing agents...")
        from agents.supervisor import create_supervisor
        _supervisor = create_supervisor()
    return _supervisor


async def chat(message: str, history: list) -> str:
    """Handle chat messages through supervisor."""
    supervisor = get_supervisor()
    response = await supervisor.route(message)
    return response


def chat_wrapper(message: str, history: list) -> str:
    """Wrapper to run async chat function in sync context."""
    return asyncio.run(chat(message, history))


demo = gr.ChatInterface(
    fn=chat_wrapper,
    title="🏥 Cleveland Clinic Abu Dhabi - AI Assistant",
    description=(
        "**Ask me about:**\n\n"
        "📋 **Information** - hours, doctors, insurance, services, location\n\n"
        "📅 **Appointments** - check, book, cancel, reschedule"
    ),
    examples=[
        "What are your clinic hours?",
        "Do you accept Daman insurance?",
        "I need to see a cardiologist who speaks Arabic",
        "Book an appointment with Dr. Al Blooshi",
        "Do you accept ADNIC and can I book for Sunday?"
    ]
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
