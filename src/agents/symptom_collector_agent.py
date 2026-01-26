"""
Symptom Collector Agent - Collects patient symptoms and finds doctors
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool

from core.memory import LivingMemory
from tools.felix_api import felix_api
from utils.symptom_mapper import map_symptom_to_specialty
from utils.date_helpers import get_today, add_days

logger = logging.getLogger("felix-hospital.symptom")


class SymptomCollectorAgent(Agent):
    """Collects symptoms and searches for doctors"""
    
    def __init__(self, memory: LivingMemory):
        self.memory = memory
        
        instructions = f"""You collect patient symptoms and find doctors.

YOUR TASK:
1. Ask: "क्या problem है? कैसे help कर सकते हैं?"
2. Listen to symptoms carefully
3. Search for doctors using the symptoms
4. Hand off to booking agent once doctor is found

MEMORY:
{self.memory.to_context_block()}

RULES:
- Be empathetic about symptoms
- ONE question at a time
- Natural Hindi-English mix"""
        
        super().__init__(instructions=instructions)
        logger.info("🩺 Symptom Collector Agent initialized")
    
    async def on_enter(self):
        """When symptom collector enters"""
        logger.info("🎬 Symptom Collector Agent ENTERED")
        await self.session.generate_reply(allow_interruptions=False)
    
    @function_tool
    async def search_doctors(
        self,
        context: RunContext,
        symptoms: str
    ):
        """Search for doctors based on symptoms.
        
        Args:
            symptoms: Patient's symptoms description
        """
        logger.info(f"🔍 search_doctors called with: {symptoms}")
        
        # Update symptoms in memory
        self.memory.update_patient_info(symptoms=symptoms)
        
        # Map symptoms to specialty
        specialty_id, specialty_name = map_symptom_to_specialty(symptoms)
        logger.info(f"  Mapped to: {specialty_name} (ID: {specialty_id})")
        
        # Get facility
        facility = self.memory.session_state.patient.facility
        
        # Search doctors
        doctors = await felix_api.search_doctors(specialty_id, facility)
        
        if not doctors:
            return f"No {specialty_name} doctors found at {facility}"
        
        doctor = doctors[0]
        logger.info(f"  Found doctor: {doctor['name']}")
        
        # Update booking info
        self.memory.update_booking_info(
            doctor_id=doctor['doctor_id'],
            doctor_name=doctor['name'],
            doctor_specialty=specialty_name,
            booking_stage="doctor_found"
        )
        
        # Get slots
        from_date = get_today()
        to_date = add_days(from_date, 3)
        slots = await felix_api.get_doctor_slots(doctor['doctor_id'], from_date, to_date)
        
        if not slots:
            return f"{doctor['name']} has no slots available"
        
        # Store slots in metadata
        self.memory.session_state.metadata.available_slots = slots[:10]
        logger.info(f"  Found {len(slots)} slots")
        
        # Ready for booking handoff
        return "HANDOFF_TO_BOOKING_AGENT"
