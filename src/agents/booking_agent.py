"""
Booking Agent - Handles slot selection and confirms appointment
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool

from core.memory import LivingMemory
from tools.felix_api import felix_api
from utils.date_helpers import format_date_natural

logger = logging.getLogger("felix-hospital.booking")


class BookingAgent(Agent):
    """Handles appointment booking and confirmation"""
    
    def __init__(self, memory: LivingMemory):
        self.memory = memory
        
        instructions = f"""You handle appointment booking.

YOUR TASK:
1. Show available slots to patient
2. Ask which slot they prefer
3. Confirm the booking
4. Give final confirmation with details

MEMORY:
{self.memory.to_context_block()}

RULES:
- Show 2-3 slot options clearly
- Say times in English: "ten AM", not "10:00"
- After booking, give WhatsApp confirmation message"""
        
        super().__init__(instructions=instructions)
        logger.info("📅 Booking Agent initialized")
    
    async def on_enter(self):
        """When booking agent enters"""
        logger.info("🎬 Booking Agent ENTERED")
        await self.session.generate_reply(allow_interruptions=False)
    
    @function_tool
    async def confirm_booking(
        self,
        context: RunContext,
        slot_time: str
    ):
        """Confirm and book the appointment.
        
        Args:
            slot_time: Time like "10:00 AM" or "ten AM"
        """
        logger.info(f"✅ confirm_booking called with: {slot_time}")
        
        patient = self.memory.session_state.patient
        booking = self.memory.session_state.booking
        
        # Validation
        if not patient.name or not patient.age or not booking.doctor_id:
            logger.error("  ❌ Missing required info")
            return "Missing patient details"
        
        slots = self.memory.session_state.metadata.available_slots
        if not slots:
            logger.error("  ❌ No slots available")
            return "No slots available"
        
        # Find matching slot
        selected = None
        for slot in slots:
            if slot_time.lower() in slot['time'].lower():
                selected = slot
                break
        
        if not selected:
            logger.warning(f"  ⚠️ Slot not found: {slot_time}")
            return f"Could not find slot for {slot_time}"
        
        logger.info(f"  📍 Selected slot: {selected['date']} {selected['time']}")
        
        # Book appointment
        result = await felix_api.book_appointment(
            slot_id=selected['slot_id'],
            patient_name=patient.name,
            patient_age=patient.age,
            gender=patient.gender or "M",
            phone=patient.phone or "0000000000",
            doctor_id=booking.doctor_id
        )
        
        # Update memory
        self.memory.update_booking_info(
            booking_id=result['booking_id'],
            selected_slot_id=selected['slot_id'],
            selected_slot_time=selected['time'],
            selected_slot_date=selected['date'],
            booking_stage="completed"
        )
        
        logger.info(f"  🎉 Booking confirmed: {result['booking_id']}")
        
        day_name = selected['day_of_week']
        date_formatted = format_date_natural(selected['date'])
        
        return f"BOOKING_COMPLETE: {patient.name} with {booking.doctor_name} on {day_name}, {date_formatted} at {selected['time']}"
