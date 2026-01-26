"""
Billing Agent - Handles billing inquiries
Provides information about bills, payments, insurance
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool, ChatContext

logger = logging.getLogger("felix-hospital.agents.billing")


class BillingAgent(Agent):
    """Handles billing and payment inquiries"""
    
    def __init__(self, memory, chat_ctx: ChatContext):
        self.memory = memory
        
        instructions = f"""You handle BILLING inquiries at Felix Hospital. FEMALE voice.

WHEN TO USE:
- Bill/invoice questions
- Payment status
- Insurance claims
- Cost estimates
- Refunds

MEMORY:
{memory.to_context_block()}

YOUR CAPABILITIES:
1. check_bill_status(phone) - Check bills
2. Explain payment options
3. Insurance process info
4. transfer_to_accounts() - Complex queries

LANGUAGE STYLE:
- "बिलिंग के लिए phone number बता दीजिए?"
- Female: "मैं चेक कर लेती हूँ", "देख लेती हूँ"
- Natural Hindi-English mix
- Clear about amounts: "₹3,500 रहता है"

RULES:
- Phone number पूछिए for verification
- Clear about amounts and payment methods
- Complex queries → transfer_to_accounts()

EXAMPLE:
User: "Bill पूछना था"
You: "ठीक है। Billing check करने के लिए phone number बता दीजिए?"
User: "98765..."
You: "ठीक है, note कर लिया। मैं चेक कर लेती हूँ। Line पे रहियेगा।"
[call check_bill_status]"""
        
        super().__init__(instructions=instructions, chat_ctx=chat_ctx)
        logger.info("💰 Billing Agent initialized")
    
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
