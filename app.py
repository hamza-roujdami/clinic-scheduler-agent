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


# Header with CCAD logo
header_html = """
<div style="text-align: center; padding: 15px; background: linear-gradient(to right, #0066b3, #009b4d); border-radius: 8px; margin-bottom: 10px;">
    <img src="https://www.clevelandclinicabudhabi.ae/-/media/images/header-images/cleveland-clinic-abu-dhabi-logo.svg" 
         alt="Cleveland Clinic Abu Dhabi" 
         style="max-width: 350px; height: auto; filter: brightness(0) invert(1);"/>
</div>
"""

demo = gr.ChatInterface(
    fn=chat_wrapper,
    title="Cleveland Clinic Abu Dhabi - AI Assistant",
    description=(
        header_html +
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
