"""
Sequential Booking Agent - Multi-step verification flow
Demonstrates Sequential Orchestration pattern for booking
"""

import asyncio
import os
from typing import Annotated, cast
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from pydantic import Field

from agent_framework import ChatAgent, ChatMessage, Role, SequentialBuilder, WorkflowOutputEvent
from agent_framework.openai import OpenAIChatClient

load_dotenv()

# =============================================================================
# Step 1: Verification Agent Tools
# =============================================================================

def validate_emirates_id(
    last_5_digits: Annotated[str, Field(description="Last 5 digits of Emirates ID")]
) -> str:
    """Validates Emirates ID (mock implementation)."""
    # Mock validation - in production, call MCP tool
    if len(last_5_digits) == 5 and last_5_digits.isdigit():
        # Simulate some IDs being invalid
        if last_5_digits == "00000":
            return "✕ Emirates ID not found in system. Please verify and try again."
        return f"✓ Emirates ID verified (ending in {last_5_digits})"
    return "✕ Invalid format. Please provide exactly 5 digits."


def verify_phone_number(
    phone: Annotated[str, Field(description="Patient phone number with country code")]
) -> str:
    """Verifies phone number (mock implementation)."""
    # Mock validation - in production, call MCP tool
    if phone.startswith("+971") and len(phone) >= 12:
        return f"✓ Phone number {phone} verified. SMS confirmation will be sent."
    return "✕ Invalid UAE phone number. Format: +971XXXXXXXXX"


# =============================================================================
# Step 2: Availability Agent Tools
# =============================================================================

def check_doctor_availability(
    doctor: Annotated[str, Field(description="Doctor name")],
    date: Annotated[str, Field(description="Preferred date (YYYY-MM-DD)")]
) -> str:
    """Checks doctor availability (mock implementation)."""
    # Mock data - in production, call MCP tool
    available_slots = {
        "2025-11-26": ["09:00", "14:00", "16:30"],
        "2025-11-27": ["09:00", "11:00"],
        "2025-11-28": ["14:00", "16:30"]
    }
    
    slots = available_slots.get(date, [])
    if slots:
        slot_list = ", ".join(slots)
        return f"✓ Dr. {doctor} available on {date}: {slot_list}"
    return f"✗ Dr. {doctor} not available on {date}. Please choose another date."


# =============================================================================
# Step 3: Booking Agent Tool
# =============================================================================

def book_appointment(
    doctor: Annotated[str, Field(description="Doctor name")],
    date: Annotated[str, Field(description="Appointment date")],
    time: Annotated[str, Field(description="Appointment time")],
    patient_name: Annotated[str, Field(description="Patient full name")],
    reason: Annotated[str, Field(description="Visit reason")]
) -> str:
    """Books the appointment (mock implementation)."""
    # Mock booking - in production, call MCP tool
    import uuid
    confirmation = f"APT-{uuid.uuid4().hex[:8].upper()}"
    return (
        f"✓ Appointment confirmed!\n"
        f"Confirmation: {confirmation}\n"
        f"Patient: {patient_name}\n"
        f"Doctor: Dr. {doctor}\n"
        f"Date/Time: {date} at {time}\n"
        f"Reason: {reason}\n"
        f"SMS confirmation sent to your phone."
    )


# =============================================================================
# Create Sequential Workflow Agents
# =============================================================================

def create_sequential_booking_workflow():
    """
    Creates a sequential booking workflow with 3 steps:
    1. Verification Agent (Emirates ID + Phone)
    2. Availability Agent (Check doctor schedule)
    3. Booking Agent (Execute booking)
    """
    # Get Azure Foundry configuration
    api_base = os.environ.get("OPENAI_API_BASE", "")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini-deployment")
    
    # Azure authentication fallback
    if not api_key or api_key.startswith("__"):
        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        api_key = token.token
    
    # Create OpenAI client
    chat_client = OpenAIChatClient(
        model_id=model,
        api_key=api_key,
        base_url=api_base if api_base else None
    )
    
    # Step 1: Verification Agent
    verification_agent = ChatAgent(
        chat_client=chat_client,
        name="VerificationAgent",
        instructions=(
            "You are the Identity Verification Agent (Step 1 of 3).\n\n"
            "Your job:\n"
            "1. Ask for Emirates ID last 5 digits\n"
            "2. Call validate_emirates_id(last_5_digits)\n"
            "3. If valid, ask for phone number\n"
            "4. Call verify_phone_number(phone)\n"
            "5. Once both verified, say 'Verification complete. Moving to availability check.'\n\n"
            "Be friendly but professional. If validation fails, ask again."
        ),
        tools=[validate_emirates_id, verify_phone_number]
    )
    
    # Step 2: Availability Agent
    availability_agent = ChatAgent(
        chat_client=chat_client,
        name="AvailabilityAgent",
        instructions=(
            "You are the Availability Agent (Step 2 of 3).\n\n"
            "Your job:\n"
            "1. Ask which doctor they want to see\n"
            "2. Ask for preferred date (YYYY-MM-DD format)\n"
            "3. Call check_doctor_availability(doctor, date)\n"
            "4. Show available time slots\n"
            "5. Ask patient to choose a time slot\n"
            "6. Once confirmed, say 'Availability confirmed. Moving to booking.'\n\n"
            "Be helpful. If no slots available, suggest alternative dates."
        ),
        tools=[check_doctor_availability]
    )
    
    # Step 3: Booking Agent
    booking_agent = ChatAgent(
        chat_client=chat_client,
        name="BookingAgent",
        instructions=(
            "You are the Booking Agent (Step 3 of 3 - Final).\n\n"
            "Your job:\n"
            "1. Ask for patient's full name\n"
            "2. Ask for reason for visit\n"
            "3. Confirm all details with patient\n"
            "4. Call book_appointment(doctor, date, time, patient_name, reason)\n"
            "5. Display the confirmation details\n\n"
            "Always confirm details before finalizing booking."
        ),
        tools=[book_appointment]
    )
    
    # Build sequential workflow: Verification → Availability → Booking
    workflow = SequentialBuilder().participants([
        verification_agent,
        availability_agent,
        booking_agent
    ]).build()
    
    return workflow


# =============================================================================
# Test Sequential Workflow
# =============================================================================

async def test_sequential_booking():
    """Test the sequential booking workflow with a sample prompt."""
    
    print("=" * 70)
    print("SEQUENTIAL BOOKING WORKFLOW TEST")
    print("=" * 70)
    print("\nThis workflow enforces a 3-step booking process:")
    print("  Step 1: Verify Emirates ID + Phone Number")
    print("  Step 2: Check Doctor Availability")
    print("  Step 3: Book Appointment")
    print("\n" + "=" * 70 + "\n")
    
    # Create workflow
    workflow = create_sequential_booking_workflow()
    
    # Test prompt - simulate user wanting to book
    test_prompt = (
        "I want to book an appointment. "
        "My Emirates ID ends in 12345, phone is +971501234567. "
        "I need to see Dr. Ahmed on 2025-11-26 at 14:00 for a checkup. "
        "My name is Hamza Al-Mansouri."
    )
    
    print(f"USER INPUT:\n{test_prompt}\n")
    print("=" * 70)
    print("WORKFLOW EXECUTION:\n")
    
    # Run workflow and collect outputs
    outputs: list[list[ChatMessage]] = []
    async for event in workflow.run_stream(test_prompt):
        if isinstance(event, WorkflowOutputEvent):
            outputs.append(cast(list[ChatMessage], event.data))
    
    # Display conversation flow
    if outputs:
        print("\n" + "=" * 70)
        print("FINAL CONVERSATION (All 3 Steps):")
        print("=" * 70 + "\n")
        
        for i, msg in enumerate(outputs[-1], start=1):
            role_name = msg.author_name or ("assistant" if msg.role == Role.ASSISTANT else "user")
            print(f"{'-' * 70}")
            print(f"Message {i:02d} [{role_name}]")
            print(f"{'-' * 70}")
            print(msg.text)
            print()


async def interactive_booking():
    """Interactive mode - chat with the sequential workflow."""
    
    print("=" * 70)
    print("INTERACTIVE SEQUENTIAL BOOKING")
    print("=" * 70)
    print("\nThe workflow will guide you through 3 steps:")
    print("  1. Identity Verification (Emirates ID + Phone)")
    print("  2. Availability Check (Doctor + Date)")
    print("  3. Booking Confirmation (Name + Reason)")
    print("\nType 'quit' to exit\n")
    print("=" * 70 + "\n")
    
    workflow = create_sequential_booking_workflow()
    
    user_input = input("You: ").strip()
    if user_input.lower() == 'quit':
        return
    
    outputs: list[list[ChatMessage]] = []
    async for event in workflow.run_stream(user_input):
        if isinstance(event, WorkflowOutputEvent):
            outputs.append(cast(list[ChatMessage], event.data))
    
    if outputs:
        # Show only the last assistant message (latest agent response)
        conversation = outputs[-1]
        for msg in reversed(conversation):
            if msg.role == Role.ASSISTANT:
                agent_name = msg.author_name or "Agent"
                print(f"\n[{agent_name}]: {msg.text}\n")
                break


async def main():
    """Run tests."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        await interactive_booking()
    else:
        await test_sequential_booking()


if __name__ == "__main__":
    asyncio.run(main())
