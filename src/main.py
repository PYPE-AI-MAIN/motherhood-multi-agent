"""
Felix Hospital Voice AI Agent - Multi-Agent Architecture
Uses Orchestrator that routes to specialized agents

Configuration is loaded from YAML files in config/
- settings.yaml: STT, TTS, LLM, hospital config
- agents.yaml: Agent prompts
- tasks.yaml: Task prompts
"""

import logging
import os
from dotenv import load_dotenv

from livekit.agents import (
    AgentServer, 
    JobContext, 
    cli, 
    WorkerOptions,
    AudioConfig,
    BackgroundAudioPlayer,
    BuiltinAudioClip
)
from livekit.agents.voice import AgentSession
from livekit.plugins import sarvam, elevenlabs, openai, silero
# from livekit.plugins.google import TTS as GoogleTTS  # Temporarily commented

# Whispey Integration (Temporarily disabled due to compatibility issues)
try:
    from whispey import LivekitObserve
    WHISPEY_AVAILABLE = False  # Temporarily disabled
    print("⚠️ Whispey temporarily disabled due to compatibility issues")
except ImportError:
    WHISPEY_AVAILABLE = False

from core.state import SessionState
from core.memory import LivingMemory
from config.config_loader import config

# Import all agents
from agents.orchestrator_agent import OrchestratorAgent
from agents.appointment_booking_agent import AppointmentBookingAgent
from agents.emergency_agent import EmergencyAgent
from agents.billing_agent import BillingAgent
from agents.health_package_agent import HealthPackageAgent

load_dotenv()

# Configure logging from YAML config
log_config = config.settings.get("logging", {})
logging.basicConfig(
    level=getattr(logging, log_config.get("level", "INFO")),
    format=log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger = logging.getLogger("felix-hospital.main")

# Initialize Whispey if available (Temporarily disabled)
pype = None
if WHISPEY_AVAILABLE:
    try:
        pype = LivekitObserve(
            agent_id=os.getenv("WHISPEY_AGENT_ID", "motherhood-agent"),
            apikey=os.getenv("WHISPEY_API_KEY"),
            enable_otel=True
        )
        logger.info("✅ Whispey observation enabled")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize Whispey: {e}")
        pype = None

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


def create_stt():
    """Create STT instance from YAML config."""
    stt_config = config.stt_config
    provider = stt_config.get("provider", "sarvam")
    language = stt_config.get("language", "hi-IN")
    model = stt_config.get("model", "saaras:v3")
    mode = stt_config.get("mode", "codemix")

    if provider == "sarvam":
        return sarvam.STT(language=language, model=model, mode=mode)
    else:
        raise ValueError(f"Unknown STT provider: {provider}")

def create_stt_for_language(language_name: str):
    """Create STT instance for specific language."""
    stt_config = config.stt_config
    provider = stt_config.get("provider", "sarvam")
    
    # Get language code from config
    languages = stt_config.get("languages", {})
    language_code = languages.get(language_name, "hi-IN")  # fallback to Hindi
    
    if provider == "sarvam":
        return sarvam.STT(language=language_code)
    else:
        raise ValueError(f"Unknown STT provider: {provider}")


def create_tts():
    """Create TTS instance from YAML config."""
    tts_config = config.tts_config
    provider = tts_config.get("provider", "elevenlabs")
    voice_id = tts_config.get("voice_id", "h3vxoHEil3T93VGdTQQu")

    if provider == "elevenlabs":
        return elevenlabs.TTS(voice_id=voice_id)
    elif provider == "google":
        # return GoogleTTS(voice=voice_id)  # Temporarily commented
        return elevenlabs.TTS(voice_id=voice_id)  # Fallback to ElevenLabs
    elif provider == "sarvam":
        return sarvam.TTS(voice_id=voice_id)
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")


def create_tts_for_language(language_name: str):
    """Create TTS instance for specific language."""
    tts_config = config.tts_config
    languages = tts_config.get("languages", {})
    
    # Get language-specific config
    lang_config = languages.get(language_name, {
        "provider": "elevenlabs",
        "voice_id": "h3vxoHEil3T93VGdTQQu"
    })
    
    provider = lang_config.get("provider", "elevenlabs")
    voice_id = lang_config.get("voice_id", "h3vxoHEil3T93VGdTQQu")
    
    if provider == "elevenlabs":
        return elevenlabs.TTS(voice_id=voice_id)
    elif provider == "google":
        # return GoogleTTS(voice=voice_id)  # Temporarily commented
        return elevenlabs.TTS(voice_id=voice_id)  # Fallback to ElevenLabs
    elif provider == "sarvam":
        return sarvam.TTS(voice_id=voice_id)
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")


def create_llm():
    """Create LLM instance from YAML config."""
    llm_config = config.llm_config
    provider = llm_config.get("provider", "openai")
    model = llm_config.get("model", "gpt-4.1")

    if provider == "openai":
        return openai.LLM(model=model)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


@server.rtc_session(agent_name="motherhood-agent")
async def entrypoint(ctx: JobContext):
    """Main entrypoint - multi-agent orchestrator architecture"""

    logger.info("=" * 80)
    logger.info(f"🏥 {config.hospital_name.upper()} VOICE AI - MULTI-AGENT SESSION STARTING")
    logger.info("=" * 80)
    logger.info(f"   Room: {ctx.room.name}")
    logger.info(f"   Agent: {config.agent_name}")
    logger.info("=" * 80)

    # Initialize session state and living memory
    session_state = SessionState()
    memory = LivingMemory(session_state)

    # Extract caller number from room metadata
    caller_number = "Unknown"
    if hasattr(ctx.room, 'metadata') and ctx.room.metadata:
        caller_number = ctx.room.metadata.get('caller_number', 'Unknown')
    logger.info(f"📞 Caller Number: {caller_number}")
    
    # Create orchestrator (will create specialized agents on-demand during handoffs)
    logger.info("🔧 INITIALIZING ORCHESTRATOR...")
    orchestrator = OrchestratorAgent(memory=memory, caller_number=caller_number)
    logger.info("   ✅ Orchestrator Agent (will create specialized agents on-demand)")
    logger.info("")
    # Create AgentSession with plugins from YAML config
    stt_config = config.stt_config
    tts_config = config.tts_config
    llm_config = config.llm_config

    logger.info("=" * 80)
    logger.info("🔧 CREATING AGENT SESSION (from YAML config)...")
    logger.info(f"   • STT: {stt_config.get('provider')} ({stt_config.get('language')})")
    logger.info(f"   • LLM: {llm_config.get('provider')} ({llm_config.get('model')})")
    logger.info(f"   • TTS: {tts_config.get('provider')} (voice: {tts_config.get('voice_id')[:8]}...)")
    logger.info(f"   • VAD: {config.settings.get('vad', {}).get('provider', 'silero')}")
    logger.info(f"   • Background Audio: LiveKit BackgroundAudioPlayer")
    logger.info(f"   • Sounds: Office Ambience + Keyboard Typing")
    logger.info("=" * 80)

    # Create session with orchestrator (which has its own STT/TTS)
    session = AgentSession(
        stt=create_stt(),
        llm=create_llm(),
        tts=create_tts(),
        vad=ctx.proc.userdata["vad"],
    )

    # Start Whispey observation if available
    session_id = None
    if pype:
        try:
            # Extract caller number for Whispey tracking
            caller_number = "Unknown"
            if hasattr(ctx.room, 'metadata') and ctx.room.metadata:
                caller_number = ctx.room.metadata.get('caller_number', 'Unknown')
            
            session_id = pype.start_session(session, phone_number=caller_number)
            logger.info(f"📊 Whispey session started: {session_id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to start Whispey session: {e}")

    # Setup Whispey shutdown callback
    async def whispey_shutdown():
        if pype and session_id:
            try:
                await pype.export(session_id)
                logger.info("📊 Whispey session exported")
            except Exception as e:
                logger.warning(f"⚠️ Failed to export Whispey session: {e}")

    ctx.add_shutdown_callback(whispey_shutdown)

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
    
    # Setup LiveKit BackgroundAudioPlayer for ambient sounds
    background_audio = BackgroundAudioPlayer(
        # Play office ambience sound looping in the background
        ambient_sound=AudioConfig(
            source=BuiltinAudioClip.OFFICE_AMBIENCE, 
            volume=0.6  # Moderate volume for phone calls
        ),
        # Play keyboard typing sound when the agent is thinking
        thinking_sound=[
            AudioConfig(
                source=BuiltinAudioClip.KEYBOARD_TYPING, 
                volume=0.4,  # Lower volume for typing
                probability=0.8  # 80% chance to play
            ),
            AudioConfig(
                source=BuiltinAudioClip.KEYBOARD_TYPING2, 
                volume=0.3,  # Even lower for second typing sound
                probability=0.6  # 60% chance to play
            ),
        ],
    )
    
    # Start background audio
    await background_audio.start(room=ctx.room, agent_session=session)
    logger.info("🔊 LiveKit BackgroundAudioPlayer started")
    logger.info("   🏢 Office ambience: ON (volume: 0.6)")
    logger.info("   ⌨️ Keyboard typing: ON (volume: 0.4/0.3)")

    logger.info("=" * 80)
    logger.info("✅ SESSION COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info(f"🏥 {config.hospital_name.upper()} VOICE AI - MULTI-AGENT SYSTEM")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"Configuration loaded from: config/settings.yaml")
    logger.info(f"Hospital: {config.hospital_name}")
    logger.info(f"AI Agent: {config.agent_name}")
    logger.info(f"Facilities: {', '.join(config.facilities)}")
    logger.info("")
    logger.info("Architecture:")
    logger.info("  🎯 Orchestrator (Router)")
    logger.info("    ├─ 📅 Appointment Booking Agent (4-task workflow)")
    logger.info("    ├─ 🚨 Emergency Agent (Immediate transfer)")
    logger.info("    ├─ 💰 Billing Agent (Payment inquiries)")
    logger.info("    └─ 🏥 Health Package Agent (Checkup packages)")
    logger.info("")
    logger.info("AI Stack (from YAML config):")
    logger.info(f"  • STT: {config.stt_config.get('provider')} ({config.stt_config.get('language')})")
    logger.info(f"  • LLM: {config.llm_config.get('provider')} ({config.llm_config.get('model')})")
    logger.info(f"  • TTS: {config.tts_config.get('provider')}")
    logger.info("")
    logger.info("Features:")
    logger.info("  • Natural Hindi-English conversation")
    logger.info("  • Female receptionist voice")
    logger.info("  • Living Memory system")
    logger.info("  • Smart intent routing")
    logger.info("  • YAML-based configuration")
    logger.info("")
    logger.info("=" * 80)

    cli.run_app(server)
