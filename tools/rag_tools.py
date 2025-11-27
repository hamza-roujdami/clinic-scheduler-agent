"""
RAG Tools - Mocked clinic information retrieval
TODO: Replace with Azure AI Search or MCP Server
"""

from typing import Annotated
from pydantic import Field


# Mock clinic database
CLINIC_INFO = """
**Abu Dhabi Clinic**

📍 Location: Al Maryah Island, Abu Dhabi, UAE

⏰ Hours:
• Sunday - Thursday: 8:00 AM - 8:00 PM
• Friday: 8:00 AM - 6:00 PM
• Saturday: 8:00 AM - 4:00 PM

👨‍⚕️ Doctors:
• Dr. Khalid Al Blooshi - Cardiology (English, Arabic)
• Dr. Sarah Williams - Pediatrics (English, French)
• Dr. Mohammed Ahmed - Internal Medicine (English, Arabic, Urdu)

🏥 Services:
• Cardiology
• Pediatrics
• Internal Medicine
• Emergency (24/7)
• Laboratory
• Imaging

💳 Accepted Insurance:
ADNIC, Daman, AXA Gulf, Oman Insurance, MetLife Alico, Neuron, Nextcare, Cigna

📞 Contact: +971 2 501 9999
"""


def get_clinic_info(
    query: Annotated[str, Field(description="What information the user is asking about")]
) -> str:
    """Get clinic information - hours, doctors, insurance, services, location, contact"""
    return CLINIC_INFO
