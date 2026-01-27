"""
Booking Confirmation Task - Confirms and books appointment using AgentTask pattern
Uses task.complete() to return structured result
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from livekit.agents.voice import AgentTask
from livekit.agents.llm import function_tool, ChatContext

from core.memory import LivingMemory
from tools.felix_api import felix_api
from utils.date_helpers import format_date_natural

logger = logging.getLogger("felix-hospital.tasks.booking_confirmation")


class BookingConfirmationResult(BaseModel):
    """Structured output from booking confirmation task"""
    booking_id: str = Field(default="", description="Unique booking ID")
    patient_name: str = Field(default="", description="Patient name")
    doctor_name: str = Field(default="", description="Doctor name")
    appointment_date: str = Field(default="", description="Appointment date")
    appointment_time: str = Field(default="", description="Appointment time")
    facility: str = Field(default="", description="Hospital facility")
    completed: bool = Field(default=False, description="Booking confirmed")


class BookingConfirmationTask(AgentTask[BookingConfirmationResult]):
    """
    AgentTask for booking confirmation.

    This task:
    1. Summarizes booking details
    2. Gets patient confirmation
    3. Books the appointment via API
    4. Provides confirmation message
    """

    def __init__(self, memory: LivingMemory, chat_ctx: ChatContext):
        self.memory = memory
        state = memory.session_state

        # Build summary
        summary = f"""
Patient: {state.patient.name}, {state.patient.age}y
Doctor: Dr. {state.booking.doctor_name}
Time: {state.booking.selected_slot_time}
Date: {state.booking.selected_slot_date}
Facility: {state.patient.facility}
"""

        instructions = f"""You confirm appointment bookings at Felix Hospital. FEMALE voice.

BOOKING SUMMARY:
{summary}

YOUR TASK:
1. Summarize the booking details to patient (brief, natural)
2. Ask: "सब details सही हैं? Confirm कर दूँ?"
3. If yes → call confirm_booking()
4. Give final confirmation message with key details

LANGUAGE:
- Female: "हो गया", "confirm हो गई", "बहुत अच्छा"
- Warm, reassuring tone
- Natural Hindi-English mix

CONFIRMATION MESSAGE FORMAT:
"Booking confirm हो गई है। Dr. [NAME] के साथ [DAY], [DATE] को [TIME] पर [FACILITY] में।
Try कीजिएगा 15-20 minutes पहले पहुँचने की।
WhatsApp पर confirmation आ जाएगा। धन्यवाद!"

REAL CONVERSATION EXAMPLES:

Example 1 (Standard confirmation):
You: "तो confirm कर रही हूँ - Dr. Ankur Singh के साथ Monday, 27th January को eleven AM पर Noida में। सही है?"
User: "हाँ जी"
[call confirm_booking()]
You: "बहुत अच्छा! Booking confirm हो गई है। Dr. Ankur Singh के साथ Monday, 27th January को eleven AM पर Noida में।
Try कीजिएगा 15-20 minutes पहले पहुँचने की। WhatsApp पर confirmation आ जाएगा। धन्यवाद!"

Example 2 (Quick confirmation):
You: "Confirm कर दूँ Thursday eleven AM का?"
User: "हाँ"
[call confirm_booking()]
You: "हो गया! Appointment confirm है Dr. Manoj Yadav के साथ Thursday eleven AM पर Greater Noida में।
Appointment time से थोड़ा पहले आइएगा। WhatsApp पर details आएंगे। धन्यवाद!"

Example 3 (With OPD timing reminder):
You: "Dr. Anupam Das के साथ kal one forty-five PM। Confirm करूँ?"
User: "हाँ ठीक है"
[call confirm_booking()]
You: "Perfect! Appointment book हो गई। Dr. Anupam Das के साथ कल one forty-five PM पर।
Try कीजिएगा 15-20 minutes पहले विज़िट कर लेना। Confirmation WhatsApp पर आ जाएगा। धन्यवाद!"

Example 4 (Walk-in scenario - no booking):
You: "Dr. Bhalla की appointments full हैं। ठीक है Anjali जी। Walk-in में आ जाइए 12:30 से 1:00 के बीच। Dr. Bhalla मिल जाएंगे। धन्यवाद!"

IMPORTANT:
- Keep it natural and warm
- Always mention: Doctor name, Day/Date, Time, Facility
- Add "15-20 minutes पहले" reminder
- Mention WhatsApp confirmation
- NO robotic phrases like "booking confirmation task complete"
"""

        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info("✅ Booking Confirmation Task initialized")

    async def on_enter(self) -> None:
        """Called when task starts"""
        state = self.memory.session_state

        logger.info("=" * 60)
        logger.info("✅ BOOKING CONFIRMATION TASK - STARTED")
        logger.info("   Goal: Confirm and complete booking")
        logger.info(f"   Patient: {state.patient.name}")
        logger.info(f"   Doctor: Dr. {state.booking.doctor_name}")
        logger.info(f"   Slot: {state.booking.selected_slot_time}")
        logger.info("=" * 60)

    @function_tool
    async def confirm_booking(self) -> str:
        """Confirm and complete the appointment booking.
        Call this after patient confirms all details.
        """
        logger.info("🎯 Confirming booking...")

        patient = self.memory.session_state.patient
        booking = self.memory.session_state.booking

        # Validate required data
        if not patient.name or not patient.age:
            logger.error("   Missing patient info!")
            return "Missing patient information. Cannot book."

        if not booking.doctor_id:
            logger.error("   No doctor selected!")
            return "No doctor selected. Please search again."

        if not booking.selected_slot_id:
            logger.error("   No slot selected!")
            return "No slot selected. Please select a slot first."

        logger.info(f"   Patient: {patient.name}, {patient.age}y")
        logger.info(f"   Doctor: Dr. {booking.doctor_name}")
        logger.info(f"   Slot: {booking.selected_slot_date} {booking.selected_slot_time}")

        # Book via API
        try:
            result = await felix_api.book_appointment(
                slot_id=booking.selected_slot_id,
                patient_name=patient.name,
                patient_age=patient.age,
                gender=patient.gender or "M",
                phone=patient.phone or "0000000000",
                doctor_id=booking.doctor_id
            )

            booking_id = result['booking_id']
            logger.info(f"   API SUCCESS - Booking ID: {booking_id}")

            # Update memory
            self.memory.update_booking_info(
                booking_id=booking_id,
                booking_stage="completed"
            )

            # Find day of week
            day_of_week = "Monday"
            for slot in self.memory.session_state.metadata.available_slots:
                if slot['slot_id'] == booking.selected_slot_id:
                    day_of_week = slot['day_of_week']
                    break

            # Create result
            confirmation = BookingConfirmationResult(
                booking_id=booking_id,
                patient_name=patient.name,
                doctor_name=booking.doctor_name,
                appointment_date=f"{day_of_week}, {booking.selected_slot_date}",
                appointment_time=booking.selected_slot_time,
                facility=patient.facility,
                completed=True
            )

            logger.info("=" * 60)
            logger.info("🎉 BOOKING COMPLETE!")
            logger.info(f"   Booking ID: {booking_id}")
            logger.info(f"   Patient: {confirmation.patient_name}")
            logger.info(f"   Doctor: Dr. {confirmation.doctor_name}")
            logger.info(f"   Time: {confirmation.appointment_date} at {confirmation.appointment_time}")
            logger.info(f"   Facility: {confirmation.facility}")
            logger.info("=" * 60)

            # Complete the task
            self.complete(confirmation)

            return f"BOOKING_CONFIRMED: ID {booking_id}"

        except Exception as e:
            logger.error(f"   API FAILED: {str(e)}")
            return f"Booking failed: {str(e)}. Please try again."
