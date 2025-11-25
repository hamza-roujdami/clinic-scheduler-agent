"""
Booking Agent - Manages clinic appointments
Handles: check availability, book, cancel, reschedule
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from pydantic import Field

load_dotenv()


# =============================================================================
# Tools - Functions that the LLM can call to manage appointments
# =============================================================================

DEFAULT_TIME_SLOTS = ("09:00", "14:00", "16:30")
BOOKING_STORE = Path(__file__).with_name("booking_store.json")


def _normalize_doctor(doctor: str) -> str:
    return "-".join(doctor.strip().lower().split())


def _doctor_label(doctor_key: str) -> str:
    return " ".join(doctor_key.split("-")).title()


def _slot_key(date: str, doctor_key: str, time_str: str) -> str:
    return f"{doctor_key}:{date}:{time_str}"


def _format_slot_id(date: str, doctor_key: str, time_str: str) -> str:
    return f"{date}:{doctor_key}:{time_str.replace(':', '')}"


def _load_store() -> dict:
    if BOOKING_STORE.exists():
        try:
            return json.loads(BOOKING_STORE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"bookings": {}, "booked_slots": {}}


def _persist_store(store: dict) -> None:
    BOOKING_STORE.write_text(json.dumps(store))


def _parse_slot_id(slot_id: str):
    parts = slot_id.split(":")
    if len(parts) == 3:
        date, doctor_key, time_token = parts
    else:
        trimmed = slot_id.replace(" ", "")
        if len(trimmed) >= 13 and trimmed[10] in "-_":
            date, time_token = trimmed[:10], trimmed[11:]
            doctor_key = "any"
        else:
            return None
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return None
    time_token = time_token.replace("-", "").replace("_", "")
    if len(time_token) not in (3, 4) or not time_token.isdigit():
        return None
    time_str = f"{int(time_token):04d}"
    normalized_time = f"{time_str[:2]}:{time_str[2:]}"
    return date, doctor_key, normalized_time


def check_availability(
    date: Annotated[str, Field(description="Date in YYYY-MM-DD format")],
    doctor: Annotated[str, Field(description="Doctor name or specialty")]
) -> str:
    """Returns available appointment slots for given date and doctor."""
    doctor_key = _normalize_doctor(doctor or "clinic")
    store = _load_store()
    open_slots = []
    for time_str in DEFAULT_TIME_SLOTS:
        slot_key = _slot_key(date, doctor_key, time_str)
        if slot_key not in store["booked_slots"]:
            slot_id = _format_slot_id(date, doctor_key, time_str)
            open_slots.append(f"{time_str} (slot {slot_id})")
    if not open_slots:
        return f"No open slots for Dr. {doctor} on {date}."
    slots_text = ", ".join(open_slots)
    return f"Available slots for Dr. {doctor} on {date}: {slots_text}"


def book_appointment(
    slot_id: Annotated[str, Field(description="Slot identifier (e.g., '2025-01-15-0900')")],
    patient_name: Annotated[str, Field(description="Patient full name")],
    reason: Annotated[str, Field(description="Visit reason")]
) -> str:
    """Book a new appointment."""
    parsed = _parse_slot_id(slot_id)
    if not parsed:
        return "✕ Invalid slot identifier. Please use the provided slot id format."
    date, doctor_key, time_str = parsed
    slot_key = _slot_key(date, doctor_key, time_str)

    store = _load_store()
    if slot_key in store["booked_slots"]:
        return "✕ That slot is no longer available. Please choose another time."

    confirmation = f"APT-{uuid4().hex[:8].upper()}"
    store["booked_slots"][slot_key] = confirmation
    store["bookings"][confirmation] = {
        "patient": patient_name,
        "reason": reason,
        "slot_id": slot_id,
        "slot_key": slot_key,
        "doctor": _doctor_label(doctor_key),
        "date": date,
        "time": time_str,
    }
    _persist_store(store)
    doctor_label = store["bookings"][confirmation]["doctor"]
    return (
        f"✓ Appointment booked for {patient_name} with {doctor_label} on {date} at {time_str}. "
        f"Confirmation: {confirmation}"
    )


def cancel_appointment(
    appointment_id: Annotated[str, Field(description="Appointment confirmation number")]
) -> str:
    """Cancel an existing appointment."""
    store = _load_store()
    booking = store["bookings"].pop(appointment_id, None)
    if not booking:
        return "✕ Appointment not found."
    store["booked_slots"].pop(booking.get("slot_key"), None)
    _persist_store(store)
    return f"✓ Appointment {appointment_id} cancelled successfully."


def reschedule_appointment(
    appointment_id: Annotated[str, Field(description="Existing appointment ID")],
    new_slot_id: Annotated[str, Field(description="New slot identifier")]
) -> str:
    """Reschedule an existing appointment."""
    store = _load_store()
    booking = store["bookings"].get(appointment_id)
    if not booking:
        return "✕ Appointment not found."

    parsed = _parse_slot_id(new_slot_id)
    if not parsed:
        return "✕ Invalid new slot identifier. Please use the provided slot id format."
    date, doctor_key, time_str = parsed
    slot_key = _slot_key(date, doctor_key, time_str)

    if slot_key in store["booked_slots"]:
        return "✕ That new slot is no longer available. Please choose another time."

    old_slot_key = booking.get("slot_key")
    if old_slot_key:
        store["booked_slots"].pop(old_slot_key, None)
    confirmation = appointment_id
    store["booked_slots"][slot_key] = confirmation
    booking.update(
        {
            "slot_id": new_slot_id,
            "slot_key": slot_key,
            "doctor": _doctor_label(doctor_key),
            "date": date,
            "time": time_str,
        }
    )
    _persist_store(store)
    return f"✓ Appointment {appointment_id} rescheduled to {date} at {time_str}."


# =============================================================================
# Create Booking Agent
# =============================================================================

def create_booking_agent():
    """
    Creates the Booking Agent that manages appointments.
    This agent has 4 tools for appointment operations.
    """
    # Get Azure Foundry configuration from .env
    api_base = os.environ.get("OPENAI_API_BASE", "")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini-deployment")
    
    # If no API key (or placeholder), use Azure authentication
    if not api_key or api_key.startswith("__"):
        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        api_key = token.token
    
    # Create OpenAI client connected to Azure Foundry
    chat_client = OpenAIChatClient(
        model_id=model,
        api_key=api_key,
        base_url=api_base if api_base else None
    )
    
    # Create ChatAgent with 4 appointment management tools
    # The LLM will automatically choose which tool to call
    agent = ChatAgent(
        chat_client=chat_client,
        name="ClinicBookingAgent",
        instructions=(
            "You manage clinic appointments. You can:\n"
            "• Check availability (date + doctor needed)\n"
            "• Book appointments (date, patient name, reason needed)\n"
            "• Cancel appointments (confirmation number needed)\n"
            "• Reschedule appointments (confirmation + new date needed)\n\n"
            "Always confirm details before booking. Be friendly."
        ),
        tools=[check_availability, book_appointment, cancel_appointment, reschedule_appointment]
    )
    
    return agent
