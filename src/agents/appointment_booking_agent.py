"""
Appointment Booking Agent - Workflow Coordinator using TaskGroup pattern
Uses LiveKit's TaskGroup for ordered, multi-step workflow with regression support
"""

import logging
from livekit.agents.voice import Agent
from livekit.agents.llm import function_tool, ChatContext
from livekit.agents.beta.workflows import TaskGroup

from core.memory import LivingMemory
from tasks.individual_tasks.data_collection_task import DataCollectionTask, PatientData
from tasks.individual_tasks.doctor_search_task import DoctorSearchTask, DoctorSearchResult
from tasks.individual_tasks.slot_selection_task import SlotSelectionTask, SlotSelectionResult
from tasks.individual_tasks.booking_confirmation_task import BookingConfirmationTask, BookingConfirmationResult
from config.config_loader import config

logger = logging.getLogger("felix-hospital.agents.appointment-booking")


class AppointmentBookingAgent(Agent):
    """
    Appointment Booking Agent - Coordinates the booking workflow using TaskGroup.

    Uses LiveKit's TaskGroup pattern for ordered, multi-step workflows:
    - Tasks execute in sequence automatically
    - Users can return to previous steps if needed
    - All tasks share conversation context
    - Automatic progression between tasks

    Workflow:
    1. Data Collection Task → Collect patient info
    2. Doctor Search Task → Find doctor and slots
    3. Slot Selection Task → Patient selects slot
    4. Booking Confirmation Task → Confirm and book
    """

    def __init__(self, memory: LivingMemory, chat_ctx: ChatContext):
        self.memory = memory
        self.task_group_results = None

        # Load instructions from YAML config
        instructions = config.get_agent_prompt("appointment_booking")

        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info(f"📅 Appointment Booking Agent initialized ({config.hospital_name})")
        logger.info("   Workflow: Data → Doctor → Slot → Confirm (with regression support)")

    async def on_enter(self) -> None:
        """Called when agent starts - automatically begin the TaskGroup workflow"""
        logger.info("=" * 60)
        logger.info("📅 APPOINTMENT BOOKING AGENT - STARTED")
        logger.info("   Starting TaskGroup workflow")
        logger.info("=" * 60)

        # Create and configure TaskGroup with shared chat context
        task_group = TaskGroup(
            chat_ctx=self.session.history,
            summarize_chat_ctx=True  # Summarize interactions when group finishes
        )

        # Add tasks in order using lambda factories
        # This allows tasks to be reinitialized if user wants to revisit them
        task_group.add(
            lambda: DataCollectionTask(self.memory, self.session.history),
            id="data_collection",
            description="Collects patient name, age, phone, and facility"
        )

        task_group.add(
            lambda: DoctorSearchTask(self.memory, self.session.history),
            id="doctor_search",
            description="Finds doctor based on symptoms and shows available slots"
        )

        task_group.add(
            lambda: SlotSelectionTask(self.memory, self.session.history),
            id="slot_selection",
            description="Patient selects preferred appointment time"
        )

        task_group.add(
            lambda: BookingConfirmationTask(self.memory, self.session.history),
            id="booking_confirmation",
            description="Confirms and completes the appointment booking"
        )

        logger.info("🚀 Executing TaskGroup workflow...")
        
        # Execute the task group - this runs all tasks in sequence
        # Users can go back to previous tasks if needed
        results = await task_group
        
        # Store results
        self.task_group_results = results.task_results

        logger.info("=" * 60)
        logger.info("🎉 TASKGROUP WORKFLOW COMPLETE!")
        logger.info(f"   Results: {list(self.task_group_results.keys())}")
        
        # Extract individual results
        if "booking_confirmation" in self.task_group_results:
            booking_result = self.task_group_results["booking_confirmation"]
            logger.info(f"   Booking ID: {booking_result.booking_id}")
            logger.info(f"   Patient: {booking_result.patient_name}")
            logger.info(f"   Doctor: Dr. {booking_result.doctor_name}")
            logger.info(f"   Time: {booking_result.appointment_date} at {booking_result.appointment_time}")
        logger.info("=" * 60)

    @function_tool
    async def handoff_to_emergency(self) -> str:
        """Hand off to Emergency Agent if patient mentions emergency during appointment booking.
        Use when: Patient mentions chest pain, breathing difficulty, severe pain + "अभी", accident, emergency
        """
        logger.info("=" * 60)
        logger.info("🚨 HANDOFF: Appointment Agent → Emergency Agent")
        logger.info("=" * 60)
        
        from agents.emergency_agent import EmergencyAgent
        emergency_agent = EmergencyAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        self.session.update_agent(emergency_agent)
        return "HANDOFF_TO_EMERGENCY"
    
    @function_tool
    async def handoff_to_billing(self) -> str:
        """Hand off to Billing Agent if patient asks about payment/billing during appointment booking.
        Use when: Patient asks about bill, payment, cost, insurance, refund
        """
        logger.info("=" * 60)
        logger.info("💰 HANDOFF: Appointment Agent → Billing Agent")
        logger.info("=" * 60)
        
        from agents.billing_agent import BillingAgent
        billing_agent = BillingAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        self.session.update_agent(billing_agent)
        return "HANDOFF_TO_BILLING"
    
    @function_tool
    async def handoff_to_health_package(self) -> str:
        """Hand off to Health Package Agent if patient asks about health checkup packages.
        Use when: Patient asks about health checkup, package, full body checkup, screening
        """
        logger.info("=" * 60)
        logger.info("🏥 HANDOFF: Appointment Agent → Health Package Agent")
        logger.info("=" * 60)
        
        from agents.health_package_agent import HealthPackageAgent
        health_package_agent = HealthPackageAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        self.session.update_agent(health_package_agent)
        return "HANDOFF_TO_HEALTH_PACKAGE"

    def get_workflow_status(self) -> dict:
        """Get current workflow status from TaskGroup results"""
        if not self.task_group_results:
            return {"status": "not_started"}
        
        return {
            "status": "completed",
            "results": {
                task_id: result.dict() if hasattr(result, 'dict') else str(result)
                for task_id, result in self.task_group_results.items()
            }
        }
