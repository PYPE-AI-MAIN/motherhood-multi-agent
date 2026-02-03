"""
Health Package Agent - Information about health checkup packages
Provides details about preventive health packages offered by Felix Hospital
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool, ChatContext

from config.config_loader import config

logger = logging.getLogger("felix-hospital.agents.health-package")


class HealthPackageAgent(Agent):
    """Handles health package inquiries and bookings"""

    def __init__(self, memory, chat_ctx: ChatContext):
        self.memory = memory

        # Load instructions from YAML config
        instructions = config.get_agent_prompt("health_package")

        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info(f"🏥 Health Package Agent initialized ({config.hospital_name})")
    
    async def on_enter(self):
        """When health package agent enters"""
        logger.info("=" * 80)
        logger.info("🏥 HEALTH PACKAGE AGENT ACTIVATED")
        logger.info("=" * 80)
        await self.session.generate_reply(allow_interruptions=False)
    
    @function_tool
    async def get_package_details(
        self,
        context: RunContext,
        package_name: str
    ):
        """Get details of a specific health package.
        
        Args:
            package_name: Name of package (Basic, Comprehensive, Master, Senior Citizen)
        """
        logger.info(f"🏥 Getting details for package: {package_name}")
        
        packages = {
            "basic": "Basic Health Checkup - ₹1,500: CBC, Blood Sugar, Lipid Profile. Fasting required.",
            "comprehensive": "Comprehensive - ₹3,500: All Basic + Thyroid, Liver, Kidney tests. Fasting required.",
            "master": "Master - ₹7,500: All Comprehensive + ECG, X-Ray, USG. Takes 2-3 hours.",
            "senior": "Senior Citizen - ₹6,000: Age 60+ customized screening. Includes Vitamin D, B12."
        }
        
        key = package_name.lower().split()[0]
        return packages.get(key, "Package not found")
    
    @function_tool
    async def book_health_package(
        self,
        context: RunContext,
        package_name: str,
        preferred_date: str,
        facility: str
    ):
        """Book a health package appointment.
        
        Args:
            package_name: Package to book
            preferred_date: Preferred date (DD-MM-YYYY)
            facility: Noida or Greater Noida
        """
        logger.info(f"🏥 Booking {package_name} for {preferred_date} at {facility}")
        
        # Update memory
        self.memory.update_booking_info(
            booking_type="health_package",
            package_name=package_name,
            preferred_date=preferred_date,
            facility=facility
        )
        
        return f"Health package {package_name} booked for {preferred_date} at {facility}. Booking ID: HP{hash(preferred_date) % 10000}"
    
    @function_tool
    async def handoff_to_emergency(self, context: RunContext):
        """Hand off to Emergency Agent if patient mentions emergency during health package inquiry.
        Use when: Patient mentions chest pain, breathing difficulty, emergency, accident
        """
        logger.info("=" * 60)
        logger.info("🚨 HANDOFF: Health Package Agent → Emergency Agent")
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
        """Hand off to Appointment Agent if patient wants doctor appointment instead of package.
        Use when: Patient asks about seeing a specific doctor or wants consultation
        """
        logger.info("=" * 60)
        logger.info("📅 HANDOFF: Health Package Agent → Appointment Agent")
        logger.info("=" * 60)
        
        from agents.appointment_booking_agent import AppointmentBookingAgent
        appointment_agent = AppointmentBookingAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        context.session.update_agent(appointment_agent)
        return "HANDOFF_TO_APPOINTMENT"
    
    @function_tool
    async def handoff_to_billing(self, context: RunContext):
        """Hand off to Billing Agent if patient asks about payment for package.
        Use when: Patient asks about bill, payment methods, insurance coverage
        """
        logger.info("=" * 60)
        logger.info("💰 HANDOFF: Health Package Agent → Billing Agent")
        logger.info("=" * 60)
        
        from agents.billing_agent import BillingAgent
        billing_agent = BillingAgent(
            memory=self.memory,
            chat_ctx=self.session.history
        )
        context.session.update_agent(billing_agent)
        return "HANDOFF_TO_BILLING"