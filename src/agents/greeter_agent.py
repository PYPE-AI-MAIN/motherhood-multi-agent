"""
Greeter Agent - Initial patient interaction and info collection
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool

from core.memory import LivingMemory

logger = logging.getLogger("felix-hospital.greeter")


class GreeterAgent(Agent):
    """Greets patients and collects basic information"""
    
    def __init__(self, memory: LivingMemory):
        self.memory = memory
        
        instructions = f"""You are the friendly receptionist at Felix Hospital. 

YOUR GREETING: "नमस्ते! Felix Hospital से बात हो रही है। आपका नाम क्या है?"

YOUR TASK:
1. Greet warmly in Hindi-English mix
2. Collect patient name, age, and phone number
3. Ask which facility they want: Noida or Greater Noida
4. Once you have name, age, phone, and facility - hand off to symptom collection

MEMORY:
{self.memory.to_context_block()}

RULES:
- ONE question at a time
- Check memory card before asking
- Be warm and efficient
- Never repeat collected info"""
        
        super().__init__(instructions=instructions)
        logger.info("👋 Greeter Agent initialized")
    
    async def on_enter(self):
        """When greeter enters, generate initial greeting"""
        logger.info("🎬 Greeter Agent ENTERED")
        await self.session.generate_reply(allow_interruptions=False)
    
    @function_tool
    async def collect_patient_info(
        self,
        context: RunContext,
        name: str = None,
        age: int = None,
        phone: str = None,
        facility: str = None
    ):
        """Collect basic patient information.
        
        Args:
            name: Patient's full name
            age: Patient's age  
            phone: Phone number
            facility: "Noida" or "Greater Noida"
        """
        logger.info(f"📞 collect_patient_info called")
        
        updates = {}
        if name:
            updates['name'] = name
        if age:
            updates['age'] = age
        if phone:
            updates['phone'] = phone
        if facility:
            updates['facility'] = facility
        
        if updates:
            self.memory.update_patient_info(**updates)
        
        # Check if we have all basic info
        state = self.memory.session_state
        if state.patient.name and state.patient.age and state.patient.facility:
            logger.info("✅ Basic info complete - ready for handoff")
            return "HANDOFF_TO_SYMPTOM_COLLECTOR"
        
        return "Info updated"
