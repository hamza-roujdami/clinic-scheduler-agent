"""
Clinic Supervisor - Routes user requests to the right specialist agent
"""

import os
import asyncio
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from agent_framework import HandoffBuilder, RequestInfoEvent, WorkflowEvent, WorkflowOutputEvent, WorkflowStatusEvent, FunctionCallContent, FunctionResultContent, HandoffUserInputRequest
from agent_framework.openai import OpenAIChatClient

# Import mocked tools
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.rag_tools import get_clinic_info
from tools.booking_tools import validate_emirates_id, verify_phone, check_availability, book_appointment, cancel_appointment, reschedule_appointment

load_dotenv()


class SupervisorWorkflow:
    
    def __init__(self):
        print("🔧 Initializing Supervisor Workflow...")
        
        # Track pending requests for multi-turn conversations
        # Note: This is workflow-level state tracking, separate from agent memory
        self.pending_requests = []
        
        # Connect to Azure OpenAI
        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        
        chat_client = OpenAIChatClient(
            model_id=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini-deployment"),
            api_key=token.token,
            base_url=os.getenv("OPENAI_API_BASE")
        )
        
        # Create the coordinator that triages requests
        # Memory: Uses MAF's default in-memory ChatMessageStore for conversation history
        # See: https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-memory
        self.coordinator = chat_client.create_agent(
            instructions=(
                "You are frontline clinic support triage. Read the user's request and decide whether "
                "to hand off to rag_agent or booking_agent. Provide a brief natural-language response for the user.\n\n"
                "When delegation is required, call the matching handoff tool:\n"
                "- handoff_to_rag_agent for information queries (hours, doctors, insurance, services, location)\n"
                "- handoff_to_booking_agent for appointment actions (check, book, cancel, reschedule)\n\n"
                "For simple greetings, respond directly with a warm welcome."
            ),
            name="coordinator_agent",
        )
        
        # Specialist for answering clinic info questions (with RAG tool)
        # Memory: In-memory conversation history maintained automatically by MAF
        self.rag_agent = chat_client.create_agent(
            instructions=(
                "You handle information queries about the clinic. "
                "ALWAYS call get_clinic_info tool first to retrieve accurate clinic information. "
                "Never answer from memory - you must use the tool. "
                "After getting the info from the tool, provide a friendly answer to the user."
            ),
            name="rag_agent",
            tools=[get_clinic_info]
        )
        
        # Specialist for booking appointments (with booking tools)
        self.booking_agent = chat_client.create_agent(
            instructions=(
                "You handle appointment bookings. ALWAYS use the available tools - never answer without calling tools.\n\n"
                "For NEW bookings, follow this exact sequence:\n"
                "1. Call validate_emirates_id - Ask for last 5 digits of Emirates ID\n"
                "2. Call verify_phone - Ask for UAE phone number (format: +971XXXXXXXXX)\n"
                "3. Call check_availability - Ask for preferred date (format: YYYY-MM-DD)\n"
                "4. Show available slots and ask user to choose\n"
                "5. Call book_appointment with: date, time, doctor, patient_name, reason\n"
                "6. Return confirmation code to user\n\n"
                "For cancellations: Call cancel_appointment with confirmation code\n"
                "For reschedules: Call reschedule_appointment with confirmation code, new date, new time\n\n"
                "You MUST call tools in sequence - do not skip steps or proceed without tool results."
            ),
            name="booking_agent",
            tools=[validate_emirates_id, verify_phone, check_availability, book_appointment, cancel_appointment, reschedule_appointment]
        )
        
        # Build the workflow: coordinator routes to specialists
        self.workflow = (
            HandoffBuilder(
                name="clinic_assistant_workflow",
                participants=[self.coordinator, self.rag_agent, self.booking_agent],
            )
            .set_coordinator(self.coordinator)
            .add_handoff(self.coordinator, [self.rag_agent, self.booking_agent])
            .with_termination_condition(
                # Allow longer conversations for multi-step booking flows
                # Terminate after 10 user messages OR if specialist says "confirmed"/"completed"
                lambda conv: sum(1 for msg in conv if msg.role.value == "user") >= 10
            )
            .build()
        )
        
        print("✅ Supervisor ready with coordinator + 2 specialists\n")
    
    async def route(self, user_message: str) -> str:
        """Send user message through workflow and return the response"""
        print(f"\n💬 User: {user_message}")
        
        # Check if we have pending requests (multi-turn conversation)
        if self.pending_requests:
            responses = {req.request_id: user_message for req in self.pending_requests}
            self.pending_requests = []
            events = [event async for event in self.workflow.send_responses_streaming(responses)]
        else:
            events = [event async for event in self.workflow.run_stream(user_message)]
        
        # Track routing and tools
        handoff_target = None
        tools_used = []
        
        # Process events
        for event in events:
            event_name = type(event).__name__
            
            # Capture pending requests for multi-turn conversations
            if isinstance(event, RequestInfoEvent):
                self.pending_requests.append(event)
            
            # Track agent handoffs and tool calls
            elif event_name == "AgentRunUpdateEvent":
                if hasattr(event, 'data') and hasattr(event.data, 'contents'):
                    contents = event.data.contents
                    
                    # Detect handoff calls
                    for call in [c for c in contents if isinstance(c, FunctionCallContent)]:
                        if call.name and call.name.startswith('handoff_to_'):
                            handoff_target = call.name.replace('handoff_to_', '').replace('_', ' ').title()
                        elif call.name and not call.name.startswith('('):
                            tools_used.append(call.name)
        
        # Clean output
        if handoff_target:
            print(f"🎯 Coordinator → {handoff_target}")
        
        if tools_used:
            print(f"🔧 Tools: {', '.join(tools_used)}")
        
        print()
        
        # Extract the final response
        return self._extract_response(events)
    
    def _extract_response(self, events: list[WorkflowEvent]) -> str:
        """Get the last agent message from the workflow events"""
        from agent_framework import ChatMessage, HandoffUserInputRequest
        
        # First check for RequestInfoEvent (multi-turn conversations)
        for event in reversed(events):
            if isinstance(event, RequestInfoEvent):
                if isinstance(event.data, HandoffUserInputRequest):
                    # Get the last message from the conversation
                    if event.data.conversation:
                        for message in reversed(event.data.conversation):
                            if isinstance(message, ChatMessage):
                                if message.role.value in ["assistant", "agent"] and message.text:
                                    return message.text
        
        # Then check for WorkflowOutputEvent (completed workflows)
        for event in reversed(events):
            if isinstance(event, WorkflowOutputEvent) and isinstance(event.data, list):
                # Get the last agent message
                for message in reversed(event.data):
                    if isinstance(message, ChatMessage):
                        if message.role.value in ["assistant", "agent"] and message.text:
                            return message.text
        
        # Default fallback
        return "Hello! I'm your clinic assistant. How can I help you today?"


def create_supervisor():
    return SupervisorWorkflow()


# Quick test
async def test_supervisor():
    supervisor = create_supervisor()
    
    test_queries = [
        "What are your hours?",
        "Book with Dr. Smith",
        "Hello"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}\nTEST: {query}\n{'='*60}")
        response = await supervisor.route(query)
        print(f"\n💬 Response: {response}\n")


if __name__ == "__main__":
    asyncio.run(test_supervisor())
