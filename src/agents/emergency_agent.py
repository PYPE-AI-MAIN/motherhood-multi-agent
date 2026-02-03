"""
Emergency Agent - Handles emergency cases
Immediately transfers to hospital emergency line
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool, ChatContext

from config.config_loader import config

logger = logging.getLogger("felix-hospital.agents.emergency")


class EmergencyAgent(Agent):
    """Handles emergency situations"""

    def __init__(self, memory, chat_ctx: ChatContext):
        self.memory = memory

        # Load instructions from YAML config
        instructions = config.get_agent_prompt("emergency")

        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info(f"🚨 Emergency Agent initialized ({config.hospital_name})")
    
    async def on_enter(self):
        """When emergency agent enters"""
        logger.info("=" * 80)
        logger.info("🚨 EMERGENCY AGENT ACTIVATED")
        logger.info("=" * 80)
        await self.session.generate_reply(allow_interruptions=False)
    
    @function_tool
    async def transfer_to_emergency(self, context: RunContext):
        """Transfer call to emergency line"""
        logger.info("=" * 80)
        logger.info("🚨 TRANSFERRING TO EMERGENCY LINE")
        logger.info("   Emergency hotline: +91-XXXX-XXXXXX")
        logger.info("=" * 80)
        
        # In production, this would trigger actual call transfer
        return "EMERGENCY_TRANSFER_INITIATED"
    
    @function_tool
    async def handoff_to_appointment(self, context: RunContext):
        """Hand off back to appointment booking if it's not actually an emergency.
        Use when: Patient says false alarm, wants regular appointment instead
        """
        logger.info("=" * 60)
        logger.info("📅 HANDOFF: Emergency Agent → Appointment Agent")
        logger.info("=" * 60)
        
        from agents.appointment_booking_agent import AppointmentBookingAgent
        appointment_agent = AppointmentBookingAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        context.session.update_agent(appointment_agent)
        return "HANDOFF_TO_APPOINTMENT"