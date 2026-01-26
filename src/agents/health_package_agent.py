"""
Health Package Agent - Information about health checkup packages
Provides details about preventive health packages offered by Felix Hospital
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool, ChatContext

logger = logging.getLogger("felix-hospital.agents.health-package")


class HealthPackageAgent(Agent):
    """Handles health package inquiries and bookings"""
    
    def __init__(self, memory, chat_ctx: ChatContext):
        self.memory = memory
        
        instructions = f"""You provide HEALTH CHECKUP PACKAGE info at Felix Hospital. FEMALE voice.

WHEN TO USE:
- Health checkup questions
- Package pricing/inclusions
- Preventive screening
- Package booking

AVAILABLE PACKAGES:
1. Basic - ₹1,500
   CBC, Blood Sugar, Lipid Profile
   
2. Comprehensive - ₹3,500
   Basic के सब + Thyroid, Liver, Kidney
   
3. Master - ₹7,500
   Comprehensive के सब + ECG, X-Ray, USG
   
4. Senior Citizen - ₹6,000
   60+ age के लिए customized

MEMORY:
{memory.to_context_block()}

LANGUAGE STYLE:
- "हमारे पास basic, comprehensive, master, और senior packages हैं"
- Female: "मैं बताती हूँ", "देख लेती हूँ"
- Natural Hindi-English mix
- Prices clearly: "₹3,500 रहता है"

RULES:
- Package contents clearly explain करिए
- Prices clearly mention करिए
- Date और facility (Noida/Greater Noida) पूछिए
- Booking के लिए book_health_package() use करिए

EXAMPLE:
User: "Health checkup के बारे में बताइए"
You: "हमारे पास basic, comprehensive, master, और senior citizen packages हैं। कौन सा जानना चाहेंगे?"
User: "Comprehensive"
You: "Comprehensive package ₹3,500 रहता है। इसमें CBC, Blood Sugar, Lipid Profile, Thyroid, Liver, Kidney tests हैं। Ye package book करूँ?"""
        
        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info("🏥 Health Package Agent initialized")
    
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
