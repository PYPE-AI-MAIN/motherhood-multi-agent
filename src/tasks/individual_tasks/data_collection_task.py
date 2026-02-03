"""
Data Collection Task - Collects patient information using AgentTask pattern
Uses task.complete() to return structured result
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from livekit.agents.voice import AgentTask
from livekit.agents.llm import function_tool, ChatContext

from core.memory import LivingMemory
from config.config_loader import config

logger = logging.getLogger("felix-hospital.tasks.data_collection")


class PatientData(BaseModel):
    """Structured output from data collection task"""
    name: str = Field(default="", description="Patient's full name")
    age: int = Field(default=0, description="Patient's age")
    phone: str = Field(default="", description="Patient's phone number")
    facility: str = Field(default="", description="Noida or Greater Noida")
    completed: bool = Field(default=False, description="Whether collection is complete")


class DataCollectionTask(AgentTask[PatientData]):
    """
    AgentTask for collecting patient data.

    This task collects: name, age, phone, facility
    When complete, it calls self.complete(PatientData) to return control.
    """

    def __init__(self, memory: LivingMemory, chat_ctx: ChatContext):
        self.memory = memory

        # Load instructions from YAML config with memory context
        instructions = config.get_task_prompt(
            "data_collection",
            memory_context=self.memory.to_context_block()
        )

        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info(f"📋 Data Collection Task initialized ({config.hospital_name})")

    async def on_enter(self) -> None:
        """Called when task starts"""
        logger.info("=" * 60)
        logger.info("🎬 DATA COLLECTION TASK - STARTED")
        logger.info("   Goal: Collect name, age, phone, facility")
        logger.info("=" * 60)

        # Check what's already collected
        state = self.memory.session_state
        collected = []
        missing = []

        if state.patient.name:
            collected.append(f"name={state.patient.name}")
        else:
            missing.append("name")

        if state.patient.age:
            collected.append(f"age={state.patient.age}")
        else:
            missing.append("age")

        if state.patient.phone:
            collected.append(f"phone={state.patient.phone}")
        else:
            missing.append("phone")

        if state.patient.facility:
            collected.append(f"facility={state.patient.facility}")
        else:
            missing.append("facility")

        if collected:
            logger.info(f"   Already have: {', '.join(collected)}")
        if missing:
            logger.info(f"   Need to collect: {', '.join(missing)}")

        # If all collected, complete immediately
        if not missing:
            logger.info("   All data already collected! Completing task.")
            self._complete_task()
            return

    @function_tool
    async def save_patient_field(
        self,
        name: Optional[str] = None,
        age: Optional[int] = None,
        phone: Optional[str] = None,
        facility: Optional[str] = None
    ) -> str:
        """Save a patient data field to memory.
        Call this after collecting each piece of information.

        Args:
            name: Patient's full name
            age: Patient's age in years
            phone: 10-digit phone number
            facility: "Noida" or "Greater Noida"
        """
        updates = {}
        if name:
            updates['name'] = name
            logger.info(f"   📝 Saved name: {name}")
        if age:
            updates['age'] = age
            logger.info(f"   📝 Saved age: {age}")
        if phone:
            updates['phone'] = phone
            logger.info(f"   📝 Saved phone: {phone}")
        if facility:
            updates['facility'] = facility
            logger.info(f"   📝 Saved facility: {facility}")

        if updates:
            self.memory.update_patient_info(**updates)
            return f"Saved: {', '.join(updates.keys())}"

        return "No fields to save"

    @function_tool
    async def confirm_specialty(
        self,
        confirmed: bool = True,
        new_specialty: Optional[str] = None
    ) -> str:
        """Confirm or change the specialty after data collection.
        
        Args:
            confirmed: True if user confirms the specialty, False if they want to change
            new_specialty: If changing, the new specialty name
        """
        state = self.memory.session_state
        
        if confirmed:
            logger.info(f"   ✓ User confirmed specialty: {state.patient.symptoms or 'general'}")
            # Complete the task
            self._complete_task()
            return "CONFIRMED_AND_COMPLETE"
        else:
            if new_specialty:
                logger.info(f"   🔄 User changed specialty to: {new_specialty}")
                self.memory.update_patient_info(symptoms=new_specialty)
                # Complete the task with new specialty
                self._complete_task()
                return f"CHANGED_TO_{new_specialty}_AND_COMPLETE"
            else:
                return "Please specify the new specialty you want"

    @function_tool
    async def handoff_to_emergency(self) -> str:
        """Emergency detected during data collection! Hand off immediately to emergency team.
        Use when: Patient mentions "अभी chest pain", "साँस नहीं आ रही", emergency, severe pain + "अभी"
        """
        logger.warning("🚨 EMERGENCY DETECTED in Data Collection Task!")
        logger.info("   Immediate handoff to Emergency Agent")
        
        from agents.emergency_agent import EmergencyAgent
        emergency_agent = EmergencyAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        
        # Force complete this task and handoff
        self.complete(PatientData(completed=False))
        
        # Note: The session update needs to happen at agent level
        return "EMERGENCY_DETECTED_HANDOFF_REQUIRED"

    @function_tool
    async def finish_data_collection(self) -> str:
        """Mark data collection as complete.
        Call this ONLY when you have collected ALL: name, age, phone, facility
        
        This will ask confirmation about symptom/specialty before proceeding.
        """
        state = self.memory.session_state

        logger.info("🔍 Checking completion...")
        logger.info(f"   Name: {state.patient.name or 'MISSING'}")
        logger.info(f"   Age: {state.patient.age or 'MISSING'}")
        logger.info(f"   Phone: {state.patient.phone or 'MISSING'}")
        logger.info(f"   Facility: {state.patient.facility or 'MISSING'}")

        # Check all required fields
        missing = []
        if not state.patient.name:
            missing.append("name")
        if not state.patient.age:
            missing.append("age")
        if not state.patient.phone:
            missing.append("phone")
        if not state.patient.facility:
            missing.append("facility")

        if missing:
            logger.warning(f"⚠️ Cannot complete - missing: {', '.join(missing)}")
            return f"Cannot complete yet. Still need: {', '.join(missing)}"

        # All collected - DON'T complete yet, ask for confirmation
        # Check if symptom is in memory
        symptom = state.patient.symptoms or state.metadata.current_intent
        
        if symptom:
            logger.info(f"   Symptom/specialty from memory: {symptom}")
            # Return confirmation message with symptom context
            return f"ASK_SYMPTOM_CONFIRMATION:{symptom}"
        else:
            # No symptom yet, just complete
            self._complete_task()
            return "TASK_COMPLETE"

    def _complete_task(self) -> None:
        """Internal method to complete the task with result"""
        state = self.memory.session_state

        result = PatientData(
            name=state.patient.name,
            age=state.patient.age,
            phone=state.patient.phone,
            facility=state.patient.facility,
            completed=True
        )

        logger.info("=" * 60)
        logger.info("✅ DATA COLLECTION TASK COMPLETE!")
        logger.info(f"   Patient: {result.name}, {result.age}y, {result.facility}")
        logger.info("=" * 60)

        # This returns control to the parent agent
        self.complete(result)
