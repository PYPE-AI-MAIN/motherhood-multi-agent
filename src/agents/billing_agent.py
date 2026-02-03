"""
Billing Agent - Handles billing inquiries
Provides information about bills, payments, insurance
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool, ChatContext

from config.config_loader import config

logger = logging.getLogger("felix-hospital.agents.billing")


class BillingAgent(Agent):
    """Handles billing and payment inquiries"""

    def __init__(self, memory, chat_ctx: ChatContext):
        self.memory = memory

        # Load instructions from YAML config
        instructions = config.get_agent_prompt("billing")

        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info(f"💰 Billing Agent initialized ({config.hospital_name})")
    
    async def on_enter(self):
        """When billing agent enters"""
        logger.info("=" * 80)
        logger.info("💰 BILLING AGENT ACTIVATED")
        logger.info("=" * 80)
        await self.session.generate_reply(allow_interruptions=False)
    
    @function_tool
    async def check_bill_status(
        self,
        context: RunContext,
        phone: str
    ):
        """Check billing status for patient.
        
        Args:
            phone: Patient's phone number
        """
        logger.info(f"💰 Checking bill status for: {phone}")
        
        # In production, would query billing system
        # Mock response
        return f"No pending bills found for {phone}. Last payment received on 15-Jan-2026."
    
    @function_tool
    async def transfer_to_accounts(self, context: RunContext):
        """Transfer to accounts department"""
        logger.info("💰 Transferring to accounts department")
        return "TRANSFER_TO_ACCOUNTS"
    
    @function_tool
    async def handoff_to_emergency(self, context: RunContext):
        """Hand off to Emergency Agent if patient mentions emergency during billing inquiry.
        Use when: Patient mentions chest pain, breathing difficulty, emergency, accident
        """
        logger.info("=" * 60)
        logger.info("🚨 HANDOFF: Billing Agent → Emergency Agent")
        logger.info("=" * 60)
        
        from agents.emergency_agent import EmergencyAgent
        emergency_agent = EmergencyAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        context.session.update_agent(emergency_agent)
        return "HANDOFF_TO_EMERGENCY"
    
    @function_tool
    async def handoff_to_appointment(self, context: RunContext):
        """Hand off to Appointment Agent if patient wants to book appointment after billing inquiry.
        Use when: Patient asks about booking doctor appointment
        """
        logger.info("=" * 60)
        logger.info("📅 HANDOFF: Billing Agent → Appointment Agent")
        logger.info("=" * 60)
        
        from agents.appointment_booking_agent import AppointmentBookingAgent
        appointment_agent = AppointmentBookingAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        context.session.update_agent(appointment_agent)
        return "HANDOFF_TO_APPOINTMENT"
    
    @function_tool
    async def handoff_to_health_package(self, context: RunContext):
        """Hand off to Health Package Agent if patient asks about health packages.
        Use when: Patient asks about health checkup packages
        """
        logger.info("=" * 60)
        logger.info("🏥 HANDOFF: Billing Agent → Health Package Agent")
        logger.info("=" * 60)
        
        from agents.health_package_agent import HealthPackageAgent
        health_package_agent = HealthPackageAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        context.session.update_agent(health_package_agent)
        return "HANDOFF_TO_HEALTH_PACKAGE"