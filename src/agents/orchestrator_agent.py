"""
Orchestrator Agent - Main entry point
Classifies intent and routes to appropriate specialized agent

This is the FIRST agent that talks to every patient.
It determines what the patient needs and hands off to:
- AppointmentBookingAgent (for doctor appointments)
- EmergencyAgent (for emergencies)
- BillingAgent (for billing questions)
- HealthPackageAgent (for health checkup packages)
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool

from agents.appointment_booking_agent import AppointmentBookingAgent
from agents.emergency_agent import EmergencyAgent
from agents.billing_agent import BillingAgent
from agents.health_package_agent import HealthPackageAgent
from config.config_loader import config

logger = logging.getLogger("felix-hospital.agents.orchestrator")


class OrchestratorAgent(Agent):
    """
    Main Orchestrator - Routes patients to correct workflow

    This agent:
    1. Greets the patient
    2. Asks what they need help with
    3. Classifies intent
    4. Hands off to specialized agent
    """

    def __init__(self, memory):
        self.memory = memory

        # Load instructions from YAML config with variable substitution
        instructions = config.get_agent_prompt("orchestrator")

        super().__init__(instructions=instructions)
        logger.info(f"🎯 Orchestrator Agent initialized ({config.agent_name} @ {config.hospital_name})")
    
    async def on_enter(self):
        """When orchestrator enters"""
        logger.info("=" * 80)
        logger.info("🎯 ORCHESTRATOR AGENT - SESSION STARTED")
        logger.info("   Listening for patient intent...")
        logger.info("=" * 80)
        await self.session.generate_reply(allow_interruptions=False)
    
    @function_tool
    async def handoff_to_emergency(self, context: RunContext):
        """Hand off to Emergency Agent.
        Use when: Patient reports emergency, urgent care, severe pain, accident, life-threatening situation
        """
        logger.info("=" * 80)
        logger.info("🚨 HANDOFF: Orchestrator → Emergency Agent")
        logger.info("=" * 80)
        
        # Create new agent with memory and chat_ctx
        emergency_agent = EmergencyAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        
        # Perform the handoff
        self.session.update_agent(emergency_agent)
        
        return "HANDOFF_TO_EMERGENCY"
    
    @function_tool
    async def handoff_to_appointment(
        self,
        context: RunContext,
        specialty_or_symptoms: str = ""
    ):
        """Hand off to Appointment Booking Agent.
        Use when: Patient wants to book doctor appointment, consultation, or see a doctor

        Args:
            specialty_or_symptoms: If user mentions specialty (cardiology, orthopedics) or symptoms, pass it here
        """
        logger.info("=" * 80)
        logger.info("📅 HANDOFF: Orchestrator → Appointment Booking Agent")
        if specialty_or_symptoms:
            logger.info(f"   Initial intent/symptoms: {specialty_or_symptoms}")
            # Save to memory so doctor search can use it
            self.memory.update_patient_info(symptoms=specialty_or_symptoms)
            self.memory.session_state.metadata.current_intent = specialty_or_symptoms
        logger.info("=" * 80)
        
        # Create new agent with memory and chat_ctx
        appointment_agent = AppointmentBookingAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )

        # Perform the handoff
        self.session.update_agent(appointment_agent)

        return "HANDOFF_TO_APPOINTMENT"
    
    @function_tool
    async def handoff_to_billing(self, context: RunContext):
        """Hand off to Billing Agent.
        Use when: Patient asks about bills, payments, insurance, refunds
        """
        logger.info("=" * 80)
        logger.info("💰 HANDOFF: Orchestrator → Billing Agent")
        logger.info("=" * 80)
        
        # Create new agent with memory and chat_ctx
        billing_agent = BillingAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        
        # Perform the handoff
        self.session.update_agent(billing_agent)
        
        return "HANDOFF_TO_BILLING"
    
    @function_tool
    async def handoff_to_health_package(self, context: RunContext):
        """Hand off to Health Package Agent.
        Use when: Patient asks about health checkup packages, preventive screening, full body checkup
        """
        logger.info("=" * 80)
        logger.info("🏥 HANDOFF: Orchestrator → Health Package Agent")
        logger.info("=" * 80)
        
        # Create new agent with memory and chat_ctx
        health_package_agent = HealthPackageAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        
        # Perform the handoff
        self.session.update_agent(health_package_agent)
        
        return "HANDOFF_TO_HEALTH_PACKAGE"
