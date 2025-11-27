"""
Booking Tools - Mocked appointment management
TODO: Replace with real Booking API MCP Server and Emirates ID Verification MCP Server
"""

import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4
from pydantic import Field


BOOKING_STORE = Path(__file__).parent / "bookings.json"


def _load_bookings():
    if BOOKING_STORE.exists():
        return json.loads(BOOKING_STORE.read_text())
    return {"bookings": {}, "slots": {}}


def _save_bookings(data):
    BOOKING_STORE.write_text(json.dumps(data, indent=2))


def validate_emirates_id(
    last_5_digits: Annotated[str, Field(description="Last 5 digits of Emirates ID")]
) -> str:
    """Validate Emirates ID (Mock - will use MCP Server)"""
    if len(last_5_digits) == 5 and last_5_digits.isdigit():
        return f"✓ Emirates ID verified (ending in {last_5_digits})"
    return "✗ Invalid format. Provide 5 digits"


def verify_phone(
    phone: Annotated[str, Field(description="UAE phone number with country code")]
) -> str:
    """Verify phone number (Mock - will use MCP Server)"""
    if phone.startswith("+971"):
        return f"✓ Phone {phone} verified"
    return "✗ Invalid UAE number. Format: +971XXXXXXXXX"


def check_availability(
    date: Annotated[str, Field(description="Date YYYY-MM-DD")],
    doctor: Annotated[str, Field(description="Doctor name")]
) -> str:
    """Check available appointment slots (Mock - will use Booking API MCP Server)"""
    # Mock available slots
    slots = ["09:00", "14:00", "16:30"]
    return f"Available slots for {doctor} on {date}:\n• " + "\n• ".join(slots)


def book_appointment(
    date: Annotated[str, Field(description="Date YYYY-MM-DD")],
    time: Annotated[str, Field(description="Time HH:MM")],
    doctor: Annotated[str, Field(description="Doctor name")],
    patient_name: Annotated[str, Field(description="Patient name")],
    reason: Annotated[str, Field(description="Reason for visit")]
) -> str:
    """Book appointment (Mock - will use Booking API MCP Server)"""
    data = _load_bookings()
    confirmation = f"APT-{uuid4().hex[:8].upper()}"
    
    data["bookings"][confirmation] = {
        "date": date,
        "time": time,
        "doctor": doctor,
        "patient": patient_name,
        "reason": reason
    }
    _save_bookings(data)
    
    return f"✓ Appointment booked!\nConfirmation: {confirmation}\n{doctor} on {date} at {time}"


def cancel_appointment(
    confirmation_code: Annotated[str, Field(description="Appointment confirmation code")]
) -> str:
    """Cancel appointment (Mock - will use Booking API MCP Server)"""
    data = _load_bookings()
    if confirmation_code in data["bookings"]:
        del data["bookings"][confirmation_code]
        _save_bookings(data)
        return f"✓ Appointment {confirmation_code} cancelled"
    return "✗ Appointment not found"


def reschedule_appointment(
    confirmation_code: Annotated[str, Field(description="Appointment confirmation code")],
    new_date: Annotated[str, Field(description="New date YYYY-MM-DD")],
    new_time: Annotated[str, Field(description="New time HH:MM")]
) -> str:
    """Reschedule appointment (Mock - will use Booking API MCP Server)"""
    data = _load_bookings()
    if confirmation_code in data["bookings"]:
        data["bookings"][confirmation_code]["date"] = new_date
        data["bookings"][confirmation_code]["time"] = new_time
        _save_bookings(data)
        return f"✓ Appointment {confirmation_code} rescheduled to {new_date} at {new_time}"
    return "✗ Appointment not found"
