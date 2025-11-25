"""
Supervisor Agent - Routes requests to RAG or Booking agents using LLM
Handles simple and complex (mixed intent) queries
"""

import os
import asyncio
from dotenv import load_dotenv

from azure.identity import DefaultAzureCredential
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

load_dotenv()

# =============================================================================
# Supervisor Agent
# =============================================================================

class SupervisorAgent:
    """
    Smart routing agent that uses LLM to understand user intent.
    Routes to RAG Agent (info) or Booking Agent (appointments) or both.
    """
    
    def __init__(self):
        # Import specialized agents
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from agents.rag_agent import create_rag_agent
        from agents.booking_agent import create_booking_agent
        
        print("🔧 Initializing Supervisor...")
        
        # Create specialized agents that handle specific tasks
        self.rag_agent = create_rag_agent()          # Answers info questions
        self.booking_agent = create_booking_agent()  # Handles appointments
        
        # Set up Azure authentication
        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        
        # Create OpenAI chat client connected to Azure Foundry
        chat_client = OpenAIChatClient(
            model_id=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini-deployment"),
            api_key=token.token,
            base_url=os.getenv("OPENAI_API_BASE")
        )
        
        # Create LLM-powered classifier agent that analyzes user intent
        # This agent returns JSON: {needs_info, needs_booking, is_greeting}
        self.classifier = ChatAgent(
            chat_client=chat_client,
            name="IntentClassifier",
            instructions="""Analyze user messages and respond with JSON:
{
    "needs_info": true/false,
    "needs_booking": true/false,
    "is_greeting": true/false
}

needs_info: asking about hours, doctors, insurance, services, location
needs_booking: wants to book, cancel, reschedule appointments
is_greeting: just saying hello/hi/help

Examples:
"What are your hours?" → {"needs_info": true, "needs_booking": false, "is_greeting": false}
"Book with Dr. Smith" → {"needs_info": false, "needs_booking": true, "is_greeting": false}
"Do you accept Medicare and book Monday?" → {"needs_info": true, "needs_booking": true, "is_greeting": false}
"Hello" → {"needs_info": false, "needs_booking": false, "is_greeting": true}"""
        )
        
        print("✅ Supervisor Ready (LLM-powered routing)")
        print("   RAG Agent: info queries")
        print("   Booking Agent: appointments\n")
    
    async def _classify_intent(self, user_message: str) -> dict:
        """Ask LLM to classify what the user needs."""
        result = await self.classifier.run(user_message, json_output=True)
        import json
        return json.loads(result.text)
    
    async def route(self, user_message: str) -> str:
        """
        Main routing method - decides which agent(s) to call.
        Returns the final response to send back to user.
        """
        print(f"📨 User: {user_message}")
        
        # Ask LLM to analyze what the user needs
        classification = await self._classify_intent(user_message)
        print(f"🔍 LLM Classification: {classification}")
        
        needs_info = classification["needs_info"]
        needs_booking = classification["needs_booking"]
        is_greeting = classification["is_greeting"]
        
        # Route based on what user needs:
        
        if needs_info and needs_booking:
            # Complex query: user wants BOTH info and booking
            # Example: "Do you accept Medicare and can I book Monday?"
            print("→ Calling both agents\n")
            rag_result = await self.rag_agent.run(user_message)
            booking_result = await self.booking_agent.run(user_message)
            return f"{rag_result.text}\n\n{booking_result.text}"
        
        elif needs_info:
            # Info query: questions about clinic
            # Example: "What are your hours?"
            print("→ RAG Agent\n")
            result = await self.rag_agent.run(user_message)
            return result.text
        
        elif needs_booking:
            # Booking action: appointment management
            # Example: "Book with Dr. Smith"
            print("→ Booking Agent\n")
            result = await self.booking_agent.run(user_message)
            return result.text
        
        else:
            # Just a greeting - return welcome message
            print("→ Welcome message\n")
            return (
                "Hello! I'm your clinic assistant.\n\n"
                "📋 Information: hours, doctors, insurance, services, location\n"
                "📅 Appointments: check, book, cancel, reschedule\n\n"
                "How can I help?"
            )


def create_supervisor():
    """Create the supervisor agent."""
    return SupervisorAgent()


# =============================================================================
# Test
# =============================================================================

async def test_supervisor():
    supervisor = create_supervisor()
    
    test_queries = [
        "What are your hours?",
        "Book with Dr. Smith",
        "Do you accept Medicare and book for Monday?",
        "Hello"
    ]
    
    for query in test_queries:
        print("=" * 80)
        response = await supervisor.route(query)
        print(f"\n💬 {response}\n")
        print("=" * 80)
        print()


if __name__ == "__main__":
    asyncio.run(test_supervisor())
