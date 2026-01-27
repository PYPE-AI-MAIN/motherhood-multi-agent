"""
Appointment Booking Agent - Workflow Coordinator using AgentTask pattern
Runs sequential tasks and each task returns control via task.complete()
"""

import logging
from livekit.agents.voice import Agent
from livekit.agents.llm import function_tool, ChatContext

from core.memory import LivingMemory
from tasks.individual_tasks.data_collection_task import DataCollectionTask, PatientData
from tasks.individual_tasks.doctor_search_task import DoctorSearchTask, DoctorSearchResult
from tasks.individual_tasks.slot_selection_task import SlotSelectionTask, SlotSelectionResult
from tasks.individual_tasks.booking_confirmation_task import BookingConfirmationTask, BookingConfirmationResult

logger = logging.getLogger("felix-hospital.agents.appointment-booking")


class AppointmentBookingAgent(Agent):
    """
    Appointment Booking Agent - Coordinates the booking workflow.

    Uses LiveKit's AgentTask pattern:
    - Tasks are awaited inline using `await task`
    - Each task calls `self.complete(result)` when done
    - Control automatically returns to this agent after each task

    Workflow:
    1. Data Collection Task → Collect patient info
    2. Doctor Search Task → Find doctor and slots
    3. Slot Selection Task → Patient selects slot
    4. Booking Confirmation Task → Confirm and book
    """

    def __init__(self, memory: LivingMemory, chat_ctx: ChatContext):
        self.memory = memory

        # Workflow state
        self.workflow_stage = "not_started"
        self.patient_data: PatientData = None
        self.doctor_result: DoctorSearchResult = None
        self.slot_result: SlotSelectionResult = None
        self.booking_result: BookingConfirmationResult = None

        instructions = """You coordinate appointment bookings at Felix Hospital. FEMALE receptionist.

YOUR ROLE:
The FULL workflow runs AUTOMATICALLY. You do NOT need to call individual task tools.
The workflow will execute all steps seamlessly: Data → Doctor → Slot → Confirm.

WORKFLOW (Auto-executes):
1. Data Collection - Get patient name, age, phone, facility
2. Doctor Search - Find doctor based on symptoms/specialty
3. Slot Selection - Patient picks appointment time
4. Booking Confirmation - Confirm and complete booking

YOUR JOB - CRITICAL RULES:
- DO NOT speak between tasks (no "data collected, now searching doctor")
- ONLY speak when tasks need user input (asking name, symptoms, slot preference, confirmation)
- Let the workflow run silently from task to task
- Tasks handle ALL conversations - you just coordinate silently

WHAT YOU SHOULD NOT SAY:
❌ "आपकी सारी जानकारी ले ली गई है"
❌ "अब मैं doctor ढूंढती हूँ"
❌ "Data collection complete"
❌ Any acknowledgment between tasks

WHAT YOU SHOULD DO:
✓ Let tasks ask questions naturally
✓ Stay silent between tasks
✓ Only speak for final confirmation

LANGUAGE (only when tasks speak):
- Female voice: "समझ गई", "ठीक है", "देख लेती हूँ"
- Natural Hindi-English mix
- Warm, helpful tone
- "Line pe rahiye" when searching
- "15-20 minutes पहले आइएगा" reminder

EXAMPLE FLOW (tasks speak, you stay silent):
User: "Appointment चाहिए"
Task: "Patient का नाम?"
User: "Rahul"
Task: "Age?"
User: "35"
[Silent transition - NO announcement]
Task: "किस लिए doctor चाहिए?"
User: "घुटने में दर्द"
Task: "Line pe rahiye, देख लेती हूँ"
[Silent transition - NO announcement]
Task: "Dr. Ankur Singh available हैं। Monday eleven AM या Tuesday ten AM?"
User: "Monday"
[Silent transition - NO announcement]  
Task: "Confirm कर दूँ?"
User: "हाँ"
Task: "हो गया! Monday eleven AM confirmed। WhatsApp पर details आएंगे।"

REMEMBER: The workflow is AUTOMATIC. Don't announce stage transitions."""

        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info("📅 Appointment Booking Agent initialized")
        logger.info("   Workflow: Data → Doctor → Slot → Confirm")

    async def on_enter(self) -> None:
        """Called when agent starts - automatically begin the workflow"""
        logger.info("=" * 60)
        logger.info("📅 APPOINTMENT BOOKING AGENT - STARTED")
        logger.info("   Auto-starting full booking workflow")
        logger.info("=" * 60)

        self.workflow_stage = "starting"

        # Check what's already collected
        state = self.memory.session_state

        # Determine starting point based on what's already done
        if not self._has_patient_data():
            logger.info("   → Starting with Data Collection")
        elif not state.booking.doctor_id:
            logger.info("   → Patient data exists, starting with Doctor Search")
        elif not state.booking.selected_slot_id:
            logger.info("   → Doctor found, starting with Slot Selection")
        elif not state.booking.booking_id:
            logger.info("   → All data ready, starting with Booking Confirmation")
        else:
            logger.info("   → Booking already complete!")
            return

        # AUTO-START THE WORKFLOW
        # The workflow will run silently, only speaking when tasks need user input
        logger.info("🚀 Auto-executing workflow...")
        await self._run_workflow_silently()

    def _has_patient_data(self) -> bool:
        """Check if we have all required patient data"""
        state = self.memory.session_state
        return bool(
            state.patient.name and
            state.patient.age and
            state.patient.phone and
            state.patient.facility
        )

    async def _run_workflow_silently(self) -> None:
        """
        Run the full workflow automatically without announcements between tasks.
        Tasks will speak when they need user input, but there are no inter-task messages.
        """
        logger.info("🔄 Starting silent workflow execution...")

        # Step 1: Data Collection (if needed)
        if not self._has_patient_data():
            logger.info("   → Executing Data Collection")
            self.workflow_stage = "data_collection"
            task = DataCollectionTask(self.memory, self.session.history)
            self.patient_data = await task
            logger.info(f"   ✅ Data collected: {self.patient_data.name}")
            self.workflow_stage = "data_collection_done"
        else:
            logger.info("   ✓ Patient data already collected, skipping")

        # Step 2: Doctor Search (if needed)
        if not self.memory.session_state.booking.doctor_id:
            logger.info("   → Executing Doctor Search")
            self.workflow_stage = "doctor_search"
            task = DoctorSearchTask(self.memory, self.session.history)
            self.doctor_result = await task
            logger.info(f"   ✅ Doctor found: Dr. {self.doctor_result.doctor_name}")
            self.workflow_stage = "doctor_search_done"
        else:
            logger.info("   ✓ Doctor already selected, skipping")

        # Step 3: Slot Selection (if needed)
        if not self.memory.session_state.booking.selected_slot_id:
            logger.info("   → Executing Slot Selection")
            self.workflow_stage = "slot_selection"
            task = SlotSelectionTask(self.memory, self.session.history)
            self.slot_result = await task
            logger.info(f"   ✅ Slot selected: {self.slot_result.day_of_week} {self.slot_result.selected_time}")
            self.workflow_stage = "slot_selection_done"
        else:
            logger.info("   ✓ Slot already selected, skipping")

        # Step 4: Booking Confirmation (if needed)
        if not self.memory.session_state.booking.booking_id:
            logger.info("   → Executing Booking Confirmation")
            self.workflow_stage = "booking_confirmation"
            task = BookingConfirmationTask(self.memory, self.session.history)
            self.booking_result = await task
            logger.info(f"   ✅ Booking complete: ID {self.booking_result.booking_id}")
            self.workflow_stage = "complete"
        else:
            logger.info("   ✓ Booking already complete, skipping")

        logger.info("=" * 60)
        logger.info("🎉 WORKFLOW EXECUTION COMPLETE!")
        if self.booking_result:
            logger.info(f"   Booking ID: {self.booking_result.booking_id}")
            logger.info(f"   Patient: {self.booking_result.patient_name}")
            logger.info(f"   Doctor: Dr. {self.booking_result.doctor_name}")
            logger.info(f"   Time: {self.booking_result.appointment_date} at {self.booking_result.appointment_time}")
        logger.info("=" * 60)

    @function_tool
    async def run_data_collection(self) -> str:
        """Run the data collection task to gather patient information.
        Collects: name, age, phone, facility.
        
        Note: Workflow runs automatically. This tool is for manual intervention only.
        """
        logger.info("=" * 60)
        logger.info("🔄 MANUAL: Data Collection Task")
        logger.info("=" * 60)

        self.workflow_stage = "data_collection"

        # Create and await the task
        task = DataCollectionTask(self.memory, self.session.history)
        self.patient_data = await task  # This awaits until task.complete() is called

        logger.info(f"✅ Data Collection Complete: {self.patient_data.name}")
        self.workflow_stage = "data_collection_done"

        return f"✓ Patient data collected: {self.patient_data.name}, {self.patient_data.age}y"

    @function_tool
    async def run_doctor_search(self) -> str:
        """Run the doctor search task to find available doctors.
        Searches by symptoms/specialty.
        
        Note: Workflow runs automatically. This tool is for manual intervention only.
        """
        if not self._has_patient_data():
            return "⚠️ Patient data required first"

        logger.info("=" * 60)
        logger.info("🔄 MANUAL: Doctor Search Task")
        logger.info("=" * 60)

        self.workflow_stage = "doctor_search"

        # Create and await the task
        task = DoctorSearchTask(self.memory, self.session.history)
        self.doctor_result = await task

        logger.info(f"✅ Doctor Search Complete: Dr. {self.doctor_result.doctor_name}")
        self.workflow_stage = "doctor_search_done"

        return f"✓ Doctor found: Dr. {self.doctor_result.doctor_name} ({len(self.doctor_result.available_slots)} slots)"

    @function_tool
    async def run_slot_selection(self) -> str:
        """Run the slot selection task to let patient pick appointment time.
        
        Note: Workflow runs automatically. This tool is for manual intervention only.
        """
        if not self.memory.session_state.booking.doctor_id:
            return "⚠️ Doctor search required first"

        logger.info("=" * 60)
        logger.info("🔄 MANUAL: Slot Selection Task")
        logger.info("=" * 60)

        self.workflow_stage = "slot_selection"

        # Create and await the task
        task = SlotSelectionTask(self.memory, self.session.history)
        self.slot_result = await task

        logger.info(f"✅ Slot Selected: {self.slot_result.day_of_week} {self.slot_result.selected_time}")
        self.workflow_stage = "slot_selection_done"

        return f"✓ Slot selected: {self.slot_result.day_of_week} at {self.slot_result.selected_time}"

    @function_tool
    async def run_booking_confirmation(self) -> str:
        """Run the booking confirmation task to complete the appointment.
        
        Note: Workflow runs automatically. This tool is for manual intervention only.
        """
        if not self.memory.session_state.booking.selected_slot_id:
            return "⚠️ Slot selection required first"

        logger.info("=" * 60)
        logger.info("🔄 MANUAL: Booking Confirmation Task")
        logger.info("=" * 60)

        self.workflow_stage = "booking_confirmation"

        # Create and await the task
        task = BookingConfirmationTask(self.memory, self.session.history)
        self.booking_result = await task

        logger.info(f"✅ Booking Complete: ID {self.booking_result.booking_id}")
        self.workflow_stage = "complete"

        logger.info("=" * 60)
        logger.info("🎉 FULL WORKFLOW COMPLETE!")
        logger.info(f"   Booking ID: {self.booking_result.booking_id}")
        logger.info(f"   Patient: {self.booking_result.patient_name}")
        logger.info(f"   Doctor: Dr. {self.booking_result.doctor_name}")
        logger.info(f"   Time: {self.booking_result.appointment_date} at {self.booking_result.appointment_time}")
        logger.info("=" * 60)

        return f"✓ BOOKING COMPLETE - ID: {self.booking_result.booking_id}"

    @function_tool
    async def run_full_workflow(self) -> str:
        """Run the entire appointment booking workflow from start to finish.
        This executes all tasks silently: Data Collection → Doctor Search → Slot Selection → Confirmation
        
        Note: This is called automatically on agent entry. Manual call only if needed.
        """
        logger.info("=" * 60)
        logger.info("🚀 MANUAL TRIGGER: Full Appointment Workflow")
        logger.info("=" * 60)

        await self._run_workflow_silently()

        return f"✓ Workflow complete! Booking ID: {self.booking_result.booking_id if self.booking_result else 'N/A'}"

    def get_workflow_status(self) -> dict:
        """Get current workflow status"""
        return {
            "stage": self.workflow_stage,
            "patient_data": self.patient_data.dict() if self.patient_data else None,
            "doctor_result": self.doctor_result.dict() if self.doctor_result else None,
            "slot_result": self.slot_result.dict() if self.slot_result else None,
            "booking_result": self.booking_result.dict() if self.booking_result else None,
        }
