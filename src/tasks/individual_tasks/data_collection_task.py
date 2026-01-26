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

        instructions = f"""You collect patient info for Felix Hospital. FEMALE voice.

MEMORY (check BEFORE asking - skip if already collected):
{self.memory.to_context_block()}

YOUR QUESTIONS (natural style, ONE at a time):
1. "Patient का नाम क्या रहेगा?" (if name not in memory)
2. "Age क्या है?" (if age not in memory)
3. "Phone number क्या होगा?" (if phone not in memory)
4. "Noida आएंगे या Greater Noida?" (if facility not in memory)

LANGUAGE:
- Female voice: "समझ गई", "ठीक है", "अच्छा"
- Natural Hindi-English mix
- ONE question at a time
- Warm, conversational tone

CRITICAL RULES:
1. Check memory FIRST - skip fields already collected
2. After collecting each field, call save_patient_field() immediately
3. Once ALL 4 fields collected → call finish_data_collection()
4. Don't ask for fields that are already in memory

FLOW EXAMPLE:
You: "Patient का नाम क्या रहेगा?"
User: "Ashish"
[call save_patient_field(name="Ashish")]
You: "Age क्या है?"
User: "32"
[call save_patient_field(age=32)]
You: "Phone number बताइए"
User: "9538703029"
[call save_patient_field(phone="9538703029")]
You: "Noida आएंगे या Greater Noida?"
User: "Noida"
[call save_patient_field(facility="Noida")]
[call finish_data_collection()]"""

        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info("📋 Data Collection Task initialized")

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
    async def finish_data_collection(self) -> str:
        """Mark data collection as complete.
        Call this ONLY when you have collected ALL: name, age, phone, facility
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

        # All collected - complete the task
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
