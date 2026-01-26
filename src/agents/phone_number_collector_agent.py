"""
Phone Number Collection Agent - Uses Google Gemini Realtime API
This specialized agent ONLY collects phone numbers using realtime audio.
Gemini Realtime is better at understanding Indian accents for digits.

Handoff flow:
1. Data Collection Task detects phone needed → handoff to this agent
2. This agent collects phone number (10 digits)
3. Returns phone number and hands back to Data Collection Task
"""

import logging
from typing import Optional
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import google

from core.memory import LivingMemory

logger = logging.getLogger("felix-hospital.agents.phone-collector")


class PhoneNumberCollectorAgent(Agent):
    """
    Specialized agent for phone number collection using Gemini Realtime.
    
    Uses Google Gemini 2.5 Flash Realtime API for better Indian accent recognition.
    """
    
    def __init__(self, memory: LivingMemory):
        self.memory = memory
        self.phone_collected = False
        self.collected_phone = None
        
        # Instructions for Gemini Realtime
        instructions = """You are a phone number collector for Felix Hospital. FEMALE voice.

YOUR ONLY JOB:
Collect patient's 10-digit phone number for appointment booking.

LANGUAGE STYLE (Hindi-English mix):
"जिस number से call कर रहे हैं उसी पे book करूँ?"

IF USER SAYS "हाँ":
"ठीक है, confirm करने के लिए number बता दीजिए। धीरे-धीरे बोलिए।"

THEN LISTEN CAREFULLY:
- User will say 10 digits
- Listen carefully to Indian accent
- Repeat back for confirmation

EXAMPLE:
User: "98765 43210"
You: "ठीक है, 98765 43210, right?"
User: "हाँ"
[IMMEDIATELY call save_phone_number with "9876543210"]

CRITICAL RULES:
1. Collect EXACTLY 10 digits
2. Repeat back for confirmation
3. Once confirmed → call save_phone_number() immediately
4. If wrong number → ask again nicely
5. Natural, patient tone
6. Use धीरे-धीरे (slowly) if user speaks too fast

NOTE: You have Gemini Realtime audio processing, so you understand Indian accents better!"""
        
        super().__init__(instructions=instructions)
        logger.info("📞 Phone Number Collector Agent initialized (Gemini Realtime)")
    
    async def on_enter(self):
        """When phone collector agent enters"""
        logger.info("=" * 80)
        logger.info("📞 PHONE NUMBER COLLECTOR AGENT - ACTIVATED")
        logger.info("   Using: Google Gemini Realtime API")
        logger.info("   Task: Collect 10-digit phone number")
        logger.info("=" * 80)
        
        # Generate initial prompt
        await self.session.generate_reply(
            instructions="Ask for phone number in natural Hindi-English style"
        )
    
    @function_tool
    async def save_phone_number(
        self,
        context: RunContext,
        phone: str
    ):
        """Save the collected phone number.
        
        Args:
            phone: 10-digit phone number (no spaces, dashes)
        """
        logger.info(f"📞 save_phone_number called: {phone}")
        
        # Validate phone number
        clean_phone = phone.replace(" ", "").replace("-", "").replace("+91", "")
        
        if len(clean_phone) != 10:
            logger.warning(f"   ❌ Invalid phone length: {len(clean_phone)}")
            return f"यह phone number complete नहीं है। {len(clean_phone)} digits हैं, 10 चाहिए। फिर से बताइए?"
        
        if not clean_phone.isdigit():
            logger.warning(f"   ❌ Non-numeric characters in phone")
            return "Phone number में सिर्फ numbers होने चाहिए। फिर से बताइए?"
        
        # Save to memory
        logger.info(f"   ✅ Valid phone number: {clean_phone}")
        self.memory.update_patient_info(phone=clean_phone)
        
        self.phone_collected = True
        self.collected_phone = clean_phone
        
        logger.info("   ✅ Phone number saved to memory")
        logger.info("   → Ready to hand back to Data Collection Task")
        
        return f"""Perfect! Phone number {clean_phone} note कर लिया।

[TASK COMPLETE - Ready to hand back]"""
    
    def is_complete(self) -> bool:
        """Check if phone collection is complete"""
        return self.phone_collected
    
    def get_collected_phone(self) -> Optional[str]:
        """Get the collected phone number"""
        return self.collected_phone
