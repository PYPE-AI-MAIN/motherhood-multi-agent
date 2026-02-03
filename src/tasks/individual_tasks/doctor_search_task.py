"""
Doctor Search Task - Finds doctors based on symptoms using AgentTask pattern
Uses task.complete() to return structured result
"""

import logging
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from livekit.agents.voice import AgentTask
from livekit.agents.llm import function_tool, ChatContext

from core.memory import LivingMemory
from tools.felix_api import felix_api
from utils.symptom_mapper import map_symptom_to_specialty
from utils.date_helpers import get_today, add_days
from config.config_loader import config

logger = logging.getLogger("felix-hospital.tasks.doctor_search")


class DoctorSearchResult(BaseModel):
    """Structured output from doctor search task"""
    symptoms: str = Field(default="", description="Patient's symptoms")
    specialty: str = Field(default="", description="Medical specialty")
    doctor_id: str = Field(default="", description="Selected doctor ID")
    doctor_name: str = Field(default="", description="Selected doctor name")
    available_slots: List[Dict] = Field(default_factory=list, description="Available slots")
    completed: bool = Field(default=False, description="Whether search is complete")


class DoctorSearchTask(AgentTask[DoctorSearchResult]):
    """
    AgentTask for searching doctors by symptoms.

    This task:
    1. Gets symptoms from user (or uses pre-existing from memory)
    2. Maps symptoms to specialty
    3. Finds available doctors
    4. Returns doctor info and available slots
    """

    def __init__(self, memory: LivingMemory, chat_ctx: ChatContext):
        self.memory = memory

        # Check if symptoms already exist
        existing_symptoms = self.memory.session_state.patient.symptoms or "NOT COLLECTED"

        # Load instructions from YAML config with dynamic variables
        instructions = config.get_task_prompt(
            "doctor_search",
            memory_context=self.memory.to_context_block(),
            existing_symptoms=existing_symptoms
        )

        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info(f"🔍 Doctor Search Task initialized ({config.hospital_name})")

    async def on_enter(self) -> None:
        """Called when task starts"""
        existing_symptoms = self.memory.session_state.patient.symptoms

        logger.info("=" * 60)
        logger.info("🔍 DOCTOR SEARCH TASK - STARTED")
        logger.info("   Goal: Find doctor based on symptoms")
        if existing_symptoms:
            logger.info(f"   Pre-existing symptoms: {existing_symptoms}")
        logger.info("=" * 60)

    @function_tool
    async def search_doctors(self, symptoms: str) -> str:
        """Search for doctors based on patient symptoms.

        Args:
            symptoms: Patient's symptoms or medical specialty needed
        """
        logger.info("=" * 60)
        logger.info(f"🔍 SEARCHING DOCTORS")
        logger.info(f"   Symptoms: {symptoms}")
        logger.info("=" * 60)

        # Save symptoms to memory
        self.memory.update_patient_info(symptoms=symptoms)

        # Map symptoms to specialty
        specialty_name, specialty_id = map_symptom_to_specialty(symptoms)
        logger.info(f"   Mapped to: {specialty_name} (ID: {specialty_id})")

        # Get facility from memory
        facility = self.memory.session_state.patient.facility or "Noida"
        logger.info(f"   Facility: {facility}")

        # Search doctors via API
        doctors = await felix_api.search_doctors(
            location=facility,
            specialty_name=specialty_name,
            speciality_id=specialty_id
        )

        if not doctors:
            logger.warning(f"   No doctors found for {specialty_name} in {facility}")
            return f"{facility} में {specialty_name} doctor available नहीं हैं। Try another facility?"

        # Get first doctor
        doctor = doctors[0]
        logger.info(f"   Found: Dr. {doctor['name']}")

        # Save doctor info to memory
        self.memory.update_booking_info(
            doctor_id=doctor['doctor_id'],
            doctor_name=doctor['name'],
            doctor_specialty=specialty_name
        )

        # Get available slots for next 2 days
        from_date = get_today()
        to_date = add_days(from_date, 2)
        logger.info(f"   Fetching slots: {from_date} to {to_date}")

        slots = await felix_api.get_doctor_slots(doctor['doctor_id'], from_date, to_date)

        if not slots:
            logger.warning("   No slots available")
            return f"Dr. {doctor['name']} के पास अभी slots available नहीं हैं"

        # Store slots in memory
        self.memory.session_state.metadata.available_slots = slots[:10]
        logger.info(f"   Found {len(slots)} slots")

        # Format response with first 2-3 slots
        slot1 = slots[0]
        slot2 = slots[1] if len(slots) > 1 else None
        slot3 = slots[2] if len(slots) > 2 else None

        response = f"Dr. {doctor['name']} ({specialty_name}) available हैं:\n"
        response += f"1. {slot1['day_of_week']} {slot1['time']}"
        if slot2:
            response += f"\n2. {slot2['day_of_week']} {slot2['time']}"
        if slot3:
            response += f"\n3. {slot3['day_of_week']} {slot3['time']}"

        return response

    @function_tool
    async def finish_doctor_search(self) -> str:
        """Complete the doctor search task.
        Call this after presenting doctor and slot options to user.
        """
        state = self.memory.session_state

        logger.info("🔍 Completing doctor search...")
        logger.info(f"   Symptoms: {state.patient.symptoms}")
        logger.info(f"   Doctor: {state.booking.doctor_name}")
        logger.info(f"   Slots available: {len(state.metadata.available_slots)}")

        # Verify we have required data
        if not state.booking.doctor_id:
            logger.warning("   No doctor found yet!")
            return "Search for a doctor first using search_doctors()"

        if not state.metadata.available_slots:
            logger.warning("   No slots available!")
            return "No slots found. Search again or try different specialty."

        # Create result
        result = DoctorSearchResult(
            symptoms=state.patient.symptoms,
            specialty=state.booking.doctor_specialty,
            doctor_id=state.booking.doctor_id,
            doctor_name=state.booking.doctor_name,
            available_slots=state.metadata.available_slots,
            completed=True
        )

        logger.info("=" * 60)
        logger.info("✅ DOCTOR SEARCH TASK COMPLETE!")
        logger.info(f"   Doctor: Dr. {result.doctor_name}")
        logger.info(f"   Slots: {len(result.available_slots)} available")
        logger.info("=" * 60)

        # Return control to parent agent
        self.complete(result)
        return "TASK_COMPLETE"
    
    @function_tool
    async def handoff_to_emergency(self) -> str:
        """Emergency detected during doctor search! Hand off immediately to emergency team.
        Use when: Patient mentions "अभी chest pain", "साँस नहीं आ रही", emergency, severe pain + "अभी"
        """
        logger.warning("🚨 EMERGENCY DETECTED in Doctor Search Task!")
        logger.info("   Immediate handoff to Emergency Agent")
        
        from agents.emergency_agent import EmergencyAgent
        emergency_agent = EmergencyAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        
        # Force complete this task
        self.complete(DoctorSearchResult(completed=False))
        
        return "EMERGENCY_DETECTED_HANDOFF_REQUIRED"