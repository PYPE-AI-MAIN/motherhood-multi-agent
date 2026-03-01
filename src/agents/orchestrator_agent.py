"""
Orchestrator Agent - Main entry point
Classifies intent and routes to appropriate specialized agent

This is the FIRST agent that talks to every patient.
It first determines language preference, then hands off to:
- Language Agents (English, Hindi, Kannada, Tamil, Telugu)
- Specialized Agents (Appointment, Emergency, Billing, Health Package)
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import sarvam, elevenlabs

from agents.appointment_booking_agent import AppointmentBookingAgent
from agents.emergency_agent import EmergencyAgent
from agents.billing_agent import BillingAgent
from agents.health_package_agent import HealthPackageAgent

# Import language agents
from agents.languages.english_agent import EnglishAgent
from agents.languages.hindi_agent import HindiAgent
from agents.languages.kannada_agent import KannadaAgent
from agents.languages.tamil_agent import TamilAgent
from agents.languages.telugu_agent import TeluguAgent
from config.config_loader import config

logger = logging.getLogger("felix-hospital.agents.orchestrator")


class OrchestratorAgent(Agent):
    """
    Main Orchestrator - Routes patients to correct workflow

    This agent:
    1. Greets the patient and asks for language preference
    2. Confirms language selection
    3. Hands off to appropriate language agent
    4. Language agent then handles specialized routing
    """

    def __init__(self, memory, caller_number=None):
        self.memory = memory
        self.caller_number = caller_number or "Unknown"

        # Load instructions from YAML config with variable substitution
        instructions = config.get_agent_prompt("orchestrator")

        super().__init__(
            instructions=instructions,
            stt=sarvam.STT(language="en-IN")
        )
        logger.info(f"🎯 Orchestrator Agent initialized ({config.agent_name} @ {config.hospital_name})")
    
    async def on_enter(self):
        """When orchestrator enters"""
        logger.info("=" * 80)
        logger.info("🎯 ORCHESTRATOR AGENT - SESSION STARTED")
        logger.info("   Listening for patient intent...")
        logger.info("=" * 80)
        
        # DEBUG: Try to generate initial reply
        logger.info("🔊 ATTEMPTING TO GENERATE OPENING MESSAGE...")
        await self.session.generate_reply(allow_interruptions=False)
        logger.info("✅ OPENING MESSAGE GENERATED")
    
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
    
    # Language Handoff Functions
    @function_tool
    async def handoff_to_english(self, context: RunContext):
        """Hand off to English Agent.
        Use when: Patient selects English as their preferred language
        """
        logger.info("=" * 80)
        logger.info("🇬🇧 HANDOFF: Orchestrator → English Agent")
        logger.info("=" * 80)
        
        # Say only the required message
        await self.session.say("Okay, sure")
        
        # Create new agent with memory and chat_ctx
        english_agent = EnglishAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        
        # Perform the handoff
        self.session.update_agent(english_agent)
        
        return "HANDOFF_TO_ENGLISH"
    
    @function_tool
    async def handoff_to_hindi(self, context: RunContext):
        """Hand off to Hindi Agent.
        Use when: Patient selects Hindi as their preferred language
        """
        logger.info("=" * 80)
        logger.info("🇮🇳 HANDOFF: Orchestrator → Hindi Agent")
        logger.info("=" * 80)
        
        # Say only the required message
        await self.session.say("Okay please wait a minute, let me transfer your call to someone who can help")
        
        # Create new agent with memory and chat_ctx
        hindi_agent = HindiAgent(
            memory=self.memory,
            chat_ctx=self.session.history,
            caller_number=self.caller_number
        )
        
        # Perform the handoff
        self.session.update_agent(hindi_agent)
        
        return "HANDOFF_TO_HINDI"
    
    @function_tool
    async def handoff_to_kannada(self, context: RunContext):
        """Hand off to Kannada Agent.
        Use when: Patient selects Kannada as their preferred language
        """
        logger.info("=" * 80)
        logger.info("🇮🇳 HANDOFF: Orchestrator → Kannada Agent")
        logger.info("=" * 80)
        
        # Say only the required message
        await self.session.say("Okay please wait a minute, let me transfer your call to someone who can help")
        
        # Create new agent with memory and chat_ctx
        kannada_agent = KannadaAgent(
            memory=self.memory,
            chat_ctx=self.session.history,
            caller_number=self.caller_number
        )
        
        # Perform the handoff
        self.session.update_agent(kannada_agent)
        
        return "HANDOFF_TO_KANNADA"
    
    @function_tool
    async def handoff_to_tamil(self, context: RunContext):
        """Hand off to Tamil Agent.
        Use when: Patient selects Tamil as their preferred language
        """
        logger.info("=" * 80)
        logger.info("🇮🇳 HANDOFF: Orchestrator → Tamil Agent")
        logger.info("=" * 80)
        
        # Say only the required message
        await self.session.say("Okay please wait a minute, let me transfer your call to someone who can help")
        
        # Create new agent with memory and chat_ctx
        tamil_agent = TamilAgent(
            memory=self.memory,
            chat_ctx=self.session.history,
            caller_number=self.caller_number
        )
        
        # Perform the handoff
        self.session.update_agent(tamil_agent)
        
        return "HANDOFF_TO_TAMIL"
    
    @function_tool
    async def handoff_to_telugu(self, context: RunContext):
        """Hand off to Telugu Agent.
        Use when: Patient selects Telugu as their preferred language
        """
        logger.info("=" * 80)
        logger.info("🇮🇳 HANDOFF: Orchestrator → Telugu Agent")
        logger.info("=" * 80)
        
        # Say only the required message
        await self.session.say("Okay please wait a minute, let me transfer your call to someone who can help")
        
        # Create new agent with memory and chat_ctx
        telugu_agent = TeluguAgent(
            memory=self.memory,
            chat_ctx=self.session.history,
            caller_number=self.caller_number
        )
        
        # Perform the handoff
        self.session.update_agent(telugu_agent)
        
        return "HANDOFF_TO_TELUGU"
