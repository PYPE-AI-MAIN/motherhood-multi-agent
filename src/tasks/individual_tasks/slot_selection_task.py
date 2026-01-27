"""
Slot Selection Task - Patient selects appointment slot using AgentTask pattern
Uses task.complete() to return structured result
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from livekit.agents.voice import AgentTask
from livekit.agents.llm import function_tool, ChatContext

from core.memory import LivingMemory

logger = logging.getLogger("felix-hospital.tasks.slot_selection")


class SlotSelectionResult(BaseModel):
    """Structured output from slot selection task"""
    selected_slot_id: str = Field(default="", description="Selected slot ID")
    selected_time: str = Field(default="", description="Selected time")
    selected_date: str = Field(default="", description="Selected date")
    day_of_week: str = Field(default="", description="Day of week")
    completed: bool = Field(default=False, description="Whether selection is complete")


class SlotSelectionTask(AgentTask[SlotSelectionResult]):
    """
    AgentTask for slot selection.

    This task:
    1. Presents available slots to patient
    2. Gets patient's preferred slot
    3. Confirms selection
    """

    def __init__(self, memory: LivingMemory, chat_ctx: ChatContext):
        self.memory = memory

        # Get available slots
        slots = self.memory.session_state.metadata.available_slots
        slots_text = ""
        if slots:
            for i, slot in enumerate(slots[:5], 1):
                slots_text += f"{i}. {slot['day_of_week']} {slot['time']}\n"

        instructions = f"""You help patients select appointment slots at Felix Hospital. FEMALE voice.

MEMORY:
{self.memory.to_context_block()}

AVAILABLE SLOTS:
{slots_text if slots_text else "No slots loaded yet"}

YOUR TASK:
1. Ask patient: "कौन सा time सही रहेगा आपके लिए?"
2. Listen to their preference
3. Call select_slot() with their chosen time
4. Confirm the selection naturally (NO robotic announcements)

LANGUAGE:
- Say times in ENGLISH: "ten AM", "two thirty PM" (NOT "10:00")
- Female voice: "समझ गई", "ठीक है", "Perfect"
- Natural Hindi-English mix

IMPORTANT:
- Present only 2-3 slots at a time
- Be clear about day AND time
- Call select_slot() once patient chooses
- NO announcements like "slot selection complete"

REAL CONVERSATION EXAMPLES:

Example 1 (Patient chooses from options):
You: "Monday ten AM, eleven AM या Tuesday two PM - कौन सा time सही रहेगा?"
User: "Monday eleven AM"
You: "Perfect। Confirm कर दूँ Monday eleven AM के लिए?"
User: "हाँ जी"
[call select_slot("11:00 AM")]

Example 2 (Patient asks about specific day):
User: "Sunday ko koi slot hai?"
You: "Sunday के लिए देख lेती हूँ।"
[Check slots...]
You: "Sunday ke liye slots available नहीं हैं। Monday या Tuesday prefer कर सकते हैं। Monday ten AM available है, book कर दूँ?"
User: "हाँ Monday ठीक है"
[call select_slot("10:00 AM")]

Example 3 (Tomorrow's slot):
You: "Kal के लिए ten AM, eleven AM या one PM available है। कौन सा prefer करेंगे?"
User: "Ten AM"
[call select_slot("10:00 AM")]

Example 4 (Quick confirmation):
You: "Dr. Ankur Singh के साथ Monday eleven AM, twelve PM available है। कौन सा time?"
User: "eleven AM चल जाएगा"
You: "Bilkul। Confirm कर दूँ?"
User: "हाँ"
[call select_slot("11:00 AM")]"""

        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info("📅 Slot Selection Task initialized")

    async def on_enter(self) -> None:
        """Called when task starts"""
        slots = self.memory.session_state.metadata.available_slots

        logger.info("=" * 60)
        logger.info("📅 SLOT SELECTION TASK - STARTED")
        logger.info("   Goal: Patient selects preferred appointment time")
        logger.info(f"   Available slots: {len(slots) if slots else 0}")
        logger.info("=" * 60)

    @function_tool
    async def select_slot(self, slot_time: str) -> str:
        """Select an appointment slot.

        Args:
            slot_time: The time patient wants (e.g., "10:00 AM", "ten AM", "2 PM")
        """
        logger.info(f"🎯 Selecting slot: {slot_time}")

        slots = self.memory.session_state.metadata.available_slots
        if not slots:
            logger.error("   No slots available!")
            return "No slots available. Please search for doctor again."

        # Find matching slot (flexible matching)
        selected = None
        slot_time_lower = slot_time.lower().replace(":", "").replace(" ", "")

        for slot in slots:
            slot_time_normalized = slot['time'].lower().replace(":", "").replace(" ", "")
            if slot_time_lower in slot_time_normalized or slot_time_normalized in slot_time_lower:
                selected = slot
                break

        # Also try partial match on hour
        if not selected:
            for slot in slots:
                # Extract hour from slot time
                if any(h in slot_time_lower for h in slot['time'].lower().split(":")[0]):
                    selected = slot
                    break

        if not selected:
            logger.warning(f"   Slot not found for: {slot_time}")
            available = ", ".join([s['time'] for s in slots[:3]])
            return f"That time isn't available. Available: {available}"

        logger.info(f"   Selected: {selected['day_of_week']} {selected['date']} at {selected['time']}")

        # Save to memory
        self.memory.update_booking_info(
            selected_slot_id=selected['slot_id'],
            selected_slot_time=selected['time'],
            selected_slot_date=selected['date'],
            booking_stage="slot_selected"
        )

        # Create result and complete
        result = SlotSelectionResult(
            selected_slot_id=selected['slot_id'],
            selected_time=selected['time'],
            selected_date=selected['date'],
            day_of_week=selected['day_of_week'],
            completed=True
        )

        logger.info("=" * 60)
        logger.info("✅ SLOT SELECTION TASK COMPLETE!")
        logger.info(f"   Slot: {result.day_of_week} {result.selected_date} at {result.selected_time}")
        logger.info("=" * 60)

        # Return control to parent
        self.complete(result)
        return f"Selected: {selected['day_of_week']} {selected['time']}"
