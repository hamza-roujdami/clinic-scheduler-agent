"""
RAG Agent - Clinic Information Retrieval
Handles questions about doctors, hours, insurance, services, and location
"""

import os
from typing import Annotated
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from pydantic import Field

load_dotenv()


# =============================================================================
# Mock Clinic Database
# TODO: Replace with Azure AI Search or real database in production
# =============================================================================

CLINIC_INFO_DB = {
    "hours": {
        "weekday": "Monday - Friday: 8:00 AM - 6:00 PM",
        "weekend": "Saturday: 9:00 AM - 2:00 PM, Sunday: Closed",
        "holidays": "Closed on major holidays"
    },
    "insurance": [
        "Blue Cross Blue Shield",
        "Aetna",
        "UnitedHealthcare", 
        "Cigna",
        "Medicare",
        "Medicaid"
    ],
    "doctors": [
        {
            "name": "Dr. Sarah Smith",
            "specialty": "Cardiology",
            "experience": "15 years",
            "languages": ["English", "Spanish"],
            "accepting_new_patients": True
        },
        {
            "name": "Dr. John Chen",
            "specialty": "Pediatrics",
            "experience": "12 years",
            "languages": ["English", "Mandarin"],
            "accepting_new_patients": True
        },
        {
            "name": "Dr. Maria Garcia",
            "specialty": "Family Medicine",
            "experience": "20 years",
            "languages": ["English", "Spanish", "Portuguese"],
            "accepting_new_patients": True
        },
        {
            "name": "Dr. Ahmed Hassan",
            "specialty": "Internal Medicine",
            "experience": "8 years",
            "languages": ["English", "Arabic"],
            "accepting_new_patients": False
        }
    ],
    "services": [
        "Primary Care",
        "Cardiology Consultations",
        "Pediatric Care",
        "Annual Physical Exams",
        "Lab Work & Blood Tests",
        "Vaccinations & Immunizations",
        "Chronic Disease Management",
        "Preventive Care",
        "Minor Procedures"
    ],
    "location": {
        "address": "123 Medical Plaza, Suite 400",
        "city": "Downtown",
        "state": "CA",
        "zip": "90001",
        "parking": "Free parking in building garage",
        "accessibility": "Wheelchair accessible, elevator available"
    },
    "contact": {
        "phone": "(555) 123-0123",
        "fax": "(555) 123-0124",
        "email": "info@clinic.example.com",
        "emergency": "Call 911 or go to nearest ER"
    }
}


# =============================================================================
# Tools - Functions that the LLM can call to retrieve information
# TODO: Replace with Azure AI Search queries in production
# =============================================================================

def get_clinic_hours(
    day_type: Annotated[str, Field(description="Type of day: weekday, weekend, or holiday")] = "weekday"
) -> str:
    """Returns clinic hours for weekdays, weekends, or holidays."""
    day_type_lower = day_type.lower()
    
    if "weekend" in day_type_lower or "saturday" in day_type_lower or "sunday" in day_type_lower:
        return CLINIC_INFO_DB['hours']['weekend']
    elif "holiday" in day_type_lower:
        return CLINIC_INFO_DB['hours']['holidays']
    else:
        return CLINIC_INFO_DB['hours']['weekday']


def search_doctors(
    specialty: Annotated[str, Field(description="Medical specialty")] = None,
    language: Annotated[str, Field(description="Preferred language")] = None
) -> str:
    """Search for doctors by specialty or language."""
    results = []
    
    for doc in CLINIC_INFO_DB['doctors']:
        # Check if doctor matches filters
        if specialty and specialty.lower() not in doc['specialty'].lower():
            continue
        if language and language.lower() not in [l.lower() for l in doc['languages']]:
            continue
        
        # Format doctor info
        status = "✓ Accepting" if doc['accepting_new_patients'] else "✗ Not accepting"
        results.append(
            f"{doc['name']} - {doc['specialty']}\n"
            f"  {doc['experience']} experience | Languages: {', '.join(doc['languages'])}\n"
            f"  {status} new patients"
        )
    
    return "\n\n".join(results) if results else "No doctors found. Call (555) 123-0123 for help."


def get_insurance_info(
    insurance_name: Annotated[str, Field(description="Insurance provider name")] = None
) -> str:
    """Check insurance acceptance."""
    if insurance_name:
        # Check specific insurance
        for ins in CLINIC_INFO_DB['insurance']:
            if insurance_name.lower() in ins.lower():
                return f"✓ Yes, we accept {ins}."
        return f"✗ We do not accept {insurance_name}. Call us for alternatives."
    else:
        # List all insurances
        return "Accepted insurance:\n• " + "\n• ".join(CLINIC_INFO_DB['insurance'])


def get_services_info(
    service_keyword: Annotated[str, Field(description="Service keyword")] = None
) -> str:
    """Get information about clinic services."""
    if service_keyword:
        # Search for matching services
        matches = [s for s in CLINIC_INFO_DB['services'] if service_keyword.lower() in s.lower()]
        if matches:
            return "Matching services:\n• " + "\n• ".join(matches)
        else:
            return "All services:\n• " + "\n• ".join(CLINIC_INFO_DB['services'])
    else:
        return "Services offered:\n• " + "\n• ".join(CLINIC_INFO_DB['services'])


def get_location_info(
    info_type: Annotated[str, Field(description="Type: address, parking, accessibility, contact")] = "address"
) -> str:
    """Get clinic location and contact information."""
    info_type_lower = info_type.lower()
    
    if "parking" in info_type_lower:
        return CLINIC_INFO_DB['location']['parking']
    elif "access" in info_type_lower:
        return CLINIC_INFO_DB['location']['accessibility']
    elif "contact" in info_type_lower or "phone" in info_type_lower:
        c = CLINIC_INFO_DB['contact']
        return f"Phone: {c['phone']}\nEmail: {c['email']}"
    else:
        loc = CLINIC_INFO_DB['location']
        return f"{loc['address']}, {loc['city']}, {loc['state']} {loc['zip']}\n{loc['parking']}"


# =============================================================================
# Create RAG Agent
# =============================================================================

def create_rag_agent():
    """
    Creates the RAG (Retrieval Augmented Generation) Agent.
    This agent answers questions about clinic info using 5 tools.
    """
    # Authenticate with Azure using DefaultAzureCredential (from Azure CLI login)
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    
    # Create OpenAI client connected to Azure Foundry
    chat_client = OpenAIChatClient(
        model_id=os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini-deployment"),
        api_key=token.token,
        base_url=os.environ.get("OPENAI_API_BASE")
    )
    
    # Create ChatAgent with 5 information retrieval tools
    # The LLM will automatically choose which tool to call based on user query
    agent = ChatAgent(
        chat_client=chat_client,
        name="ClinicRAGAgent",
        instructions=(
            "You provide information about the clinic:\n"
            "• Hours (weekday, weekend, holidays)\n"
            "• Doctors (by specialty or language)\n"
            "• Insurance acceptance\n"
            "• Available services\n"
            "• Location and contact info\n\n"
            "Be friendly and concise. If user wants to book, direct to booking."
        ),
        tools=[get_clinic_hours, search_doctors, get_insurance_info, get_services_info, get_location_info]
    )
    
    return agent


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_rag_agent():
        print("🔧 Creating RAG Agent...\n")
        agent = create_rag_agent()
        
        test_queries = [
            "What are your hours?",
            "Do you accept Medicare?",
            "I need a cardiologist",
            "Where are you located?"
        ]
        
        for query in test_queries:
            print("=" * 80)
            print(f"USER: {query}")
            print("=" * 80)
            
            result = await agent.run(query)
            print(f"AGENT: {result.text}\n")
    
    asyncio.run(test_rag_agent())
