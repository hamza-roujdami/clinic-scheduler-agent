"""
Clinic Scheduler Agent - Gradio Web UI
Run with: python app.py
"""

import asyncio
import gradio as gr
from dotenv import load_dotenv
import threading

load_dotenv()

# Lazy-load supervisor to avoid slow startup
_supervisor = None
_event_loop = None
_loop_thread = None


def get_event_loop():
    """Get or create persistent event loop running in background thread."""
    global _event_loop, _loop_thread
    if _event_loop is None:
        _event_loop = asyncio.new_event_loop()
        
        def run_loop():
            asyncio.set_event_loop(_event_loop)
            _event_loop.run_forever()
        
        _loop_thread = threading.Thread(target=run_loop, daemon=True)
        _loop_thread.start()
    
    return _event_loop


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
    """Wrapper to run async chat function in persistent event loop."""
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(chat(message, history), loop)
    return future.result()


demo = gr.ChatInterface(
    fn=chat_wrapper,
    title="🏥 Abu Dhabi Clinic - AI Assistant",
    description=(
        "**Ask me about:**\n\n"
        "📋 **Information** - hours, doctors, insurance, services, location\n\n"
        "📅 **Appointments** - check, book, cancel, reschedule"
    ),
    examples=[
        "What are your clinic hours?",
        "Who are your doctors?",
        "Do you accept Daman insurance?",
        "What services do you offer?",
        "I want to book an appointment with Dr. Ahmed",
        "Check availability for Dr. Sarah",
        "Cancel my appointment",
        "Hello"
    ]
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
