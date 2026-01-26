import logging
from typing import TYPE_CHECKING
from core.state import SessionState

if TYPE_CHECKING:
    from livekit.agents import ChatContext

logger = logging.getLogger("felix-hospital.memory")


class LivingMemory:
    """
    Living Memory - The sticky note that travels with conversation
    Always visible to the agent, contains structured facts
    """
    
    def __init__(self, session_state: SessionState):
        self.session_state = session_state
        logger.info("=" * 60)
        logger.info("🧠 LIVING MEMORY INITIALIZED")
        logger.info("=" * 60)
    
    def to_context_block(self) -> str:
        """
        Generate the memory block (sticky note) for LLM
        This will be injected into the conversation context
        """
        state = self.session_state
        
        memory_block = f"""
╔══════════════════════════════════════════════╗
║          PATIENT INFORMATION CARD            ║
╠══════════════════════════════════════════════╣
║ Name: {state.get_patient_name():<35} ║
║ Age: {state.get_patient_age():<36} ║
║ Gender: {state.get_patient_gender():<34} ║
║ Phone: {state.patient.phone or '[NOT COLLECTED]':<35} ║
║ Facility: {state.get_facility():<32} ║
║ Symptoms: {state.get_symptoms():<32} ║
╠══════════════════════════════════════════════╣
║          BOOKING INFORMATION                 ║
╠══════════════════════════════════════════════╣
║ Doctor: {state.get_doctor_name():<34} ║
║ Slot: {state.get_slot_info():<36} ║
║ Stage: {state.booking.booking_stage:<35} ║
╚══════════════════════════════════════════════╝
"""
        return memory_block
    
    def update_patient_info(self, **kwargs):
        """Update patient information"""
        logger.info("=" * 60)
        logger.info("📝 UPDATING PATIENT INFO")
        
        for key, value in kwargs.items():
            if hasattr(self.session_state.patient, key):
                old_value = getattr(self.session_state.patient, key)
                setattr(self.session_state.patient, key, value)
                logger.info(f"  • {key}: '{old_value}' → '{value}'")
        
        logger.info("=" * 60)
        self._log_current_state()
    
    def update_booking_info(self, **kwargs):
        """Update booking information"""
        logger.info("=" * 60)
        logger.info("📅 UPDATING BOOKING INFO")
        
        for key, value in kwargs.items():
            if hasattr(self.session_state.booking, key):
                old_value = getattr(self.session_state.booking, key)
                setattr(self.session_state.booking, key, value)
                logger.info(f"  • {key}: '{old_value}' → '{value}'")
        
        logger.info("=" * 60)
        self._log_current_state()
    
    def _log_current_state(self):
        """Log the current state of memory"""
        logger.info("🔍 CURRENT MEMORY STATE:")
        logger.info(f"  Patient: {self.session_state.get_patient_name()}")
        logger.info(f"  Age: {self.session_state.get_patient_age()}")
        logger.info(f"  Gender: {self.session_state.get_patient_gender()}")
        logger.info(f"  Phone: {self.session_state.patient.phone or '[NOT SET]'}")
        logger.info(f"  Facility: {self.session_state.get_facility()}")
        logger.info(f"  Symptoms: {self.session_state.get_symptoms()}")
        logger.info(f"  Doctor: {self.session_state.get_doctor_name()}")
        logger.info(f"  Booking Stage: {self.session_state.booking.booking_stage}")
        logger.info("=" * 60)
    
    def get_summary(self) -> str:
        """Get a text summary of current state"""
        state = self.session_state
        return f"Patient: {state.get_patient_name()}, Age: {state.get_patient_age()}, Problem: {state.get_symptoms()}, Doctor: {state.get_doctor_name()}"
