"""
Emergency Agent - Handles emergency cases
Immediately transfers to hospital emergency line
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool, ChatContext

logger = logging.getLogger("felix-hospital.agents.emergency")


class EmergencyAgent(Agent):
    """Handles emergency situations"""
    
    def __init__(self, memory, chat_ctx: ChatContext):
        self.memory = memory
        
        instructions = """You handle EMERGENCY situations at Felix Hospital. FEMALE voice.

WHEN TO USE:
- "अभी chest pain हो रहा है"
- "साँस नहीं आ रही"
- Severe accident/injury
- Unconscious patient
- Any life-threatening + "अभी" (right now)

YOUR IMMEDIATE RESPONSE:
"यह emergency है। मैं आपको तुरंत emergency team से connect कर रही हूँ। Line पे रहियेगा।"

Then IMMEDIATELY call transfer_to_emergency()

CRITICAL RULES:
- Act INSTANTLY - no delays
- NO information collection
- NO questions
- Just transfer immediately

LANGUAGE:
- Female: "कर रही हूँ" (NOT "कर रहा हूँ")
- Calm but urgent tone
- "रहियेगा" (stay on line)"""
        
        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info("🚨 Emergency Agent initialized")
    
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
