"""
Felix Hospital Voice AI Agent - Multi-Agent Architecture
Uses Orchestrator that routes to specialized agents
"""

import logging
from dotenv import load_dotenv

from livekit.agents import AgentServer, JobContext, cli
from livekit.agents.voice import AgentSession
from livekit.plugins import sarvam, elevenlabs, openai, silero

from core.state import SessionState
from core.memory import LivingMemory

# Import all agents
from agents.orchestrator_agent import OrchestratorAgent
from agents.appointment_booking_agent import AppointmentBookingAgent
from agents.emergency_agent import EmergencyAgent
from agents.billing_agent import BillingAgent
from agents.health_package_agent import HealthPackageAgent

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("felix-hospital.main")

# Initialize server
server = AgentServer()


def prewarm(proc):
    """Prewarm VAD model"""
    logger.info("=" * 80)
    logger.info("🔄 PREWARMING MODELS...")
    logger.info("=" * 80)
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("✅ Silero VAD model loaded")


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entrypoint - multi-agent orchestrator architecture"""
    
    logger.info("=" * 80)
    logger.info("🏥 FELIX HOSPITAL VOICE AI - MULTI-AGENT SESSION STARTING")
    logger.info("=" * 80)
    logger.info(f"   Room: {ctx.room.name}")
    logger.info("=" * 80)
    
    # Initialize session state and living memory
    session_state = SessionState()
    memory = LivingMemory(session_state)
    
    # Create orchestrator (will create specialized agents on-demand during handoffs)
    logger.info("🔧 INITIALIZING ORCHESTRATOR...")
    logger.info("")
    
    orchestrator = OrchestratorAgent(memory=memory)
    logger.info("   ✅ Orchestrator Agent (will create specialized agents on-demand)")
    logger.info("")
    logger.info("✅ System Ready!")
    
    # Create AgentSession with plugins
    logger.info("=" * 80)
    logger.info("🔧 CREATING AGENT SESSION...")
    logger.info("   • STT: Sarvam (Hindi)")
    logger.info("   • LLM: OpenAI GPT-4o-mini")
    logger.info("   • TTS: ElevenLabs (Female voice)")
    logger.info("   • VAD: Silero")
    logger.info("=" * 80)
    
    session = AgentSession(
        stt=sarvam.STT(language="hi-IN"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(voice_id="h3vxoHEil3T93VGdTQQu"),
        vad=ctx.proc.userdata["vad"],
    )
    
    logger.info("=" * 80)
    logger.info("🚀 STARTING SESSION WITH ORCHESTRATOR")
    logger.info("   First contact: Orchestrator Agent")
    logger.info("   Will route to appropriate specialized agent")
    logger.info("=" * 80)
    
    # Start session with orchestrator (entry point)
    await session.start(
        agent=orchestrator,  # Start with orchestrator!
        room=ctx.room,
    )
    
    logger.info("=" * 80)
    logger.info("✅ SESSION COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("🏥 FELIX HOSPITAL VOICE AI - MULTI-AGENT SYSTEM")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Architecture:")
    logger.info("  🎯 Orchestrator (Router)")
    logger.info("    ├─ 📅 Appointment Booking Agent (4-task workflow)")
    logger.info("    ├─ 🚨 Emergency Agent (Immediate transfer)")
    logger.info("    ├─ 💰 Billing Agent (Payment inquiries)")
    logger.info("    └─ 🏥 Health Package Agent (Checkup packages)")
    logger.info("")
    logger.info("Features:")
    logger.info("  • Natural Hindi-English conversation")
    logger.info("  • Female receptionist voice")
    logger.info("  • Living Memory system")
    logger.info("  • Smart intent routing")
    logger.info("")
    logger.info("=" * 80)
    
    cli.run_app(server)
