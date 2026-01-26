from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class PatientData:
    """Patient information collected during conversation"""
    name: str = ""
    age: int = 0
    gender: str = ""  # M or F
    phone: str = ""
    facility: str = ""  # Noida or Greater Noida
    symptoms: str = ""
    preferred_date: str = ""
    preferred_time: str = ""


@dataclass
class BookingData:
    """Booking-related information"""
    doctor_id: str = ""
    doctor_name: str = ""
    doctor_specialty: str = ""
    selected_slot_id: str = ""
    selected_slot_time: str = ""
    selected_slot_date: str = ""
    booking_id: str = ""
    booking_stage: str = "initial"  # initial, searching, slot_selection, confirming, completed


@dataclass
class ConversationMetadata:
    """Metadata about the conversation"""
    call_start_time: str = ""
    current_intent: str = ""
    intent_changes: list = field(default_factory=list)
    agent_transitions: list = field(default_factory=list)
    available_slots: List[Dict] = field(default_factory=list)  # Store slots here


@dataclass
class SessionState:
    """
    Complete session state - the Living Memory
    This travels with the conversation across all agents
    """
    # Patient information
    patient: PatientData = field(default_factory=PatientData)
    
    # Booking information
    booking: BookingData = field(default_factory=BookingData)
    
    # Conversation metadata
    metadata: ConversationMetadata = field(default_factory=ConversationMetadata)
    
    # Quick access to frequently used fields
    def get_patient_name(self) -> str:
        return self.patient.name or "[NOT COLLECTED]"
    
    def get_patient_age(self) -> str:
        return str(self.patient.age) if self.patient.age else "[NOT COLLECTED]"
    
    def get_patient_gender(self) -> str:
        return self.patient.gender or "[NOT COLLECTED]"
    
    def get_facility(self) -> str:
        return self.patient.facility or "[NOT COLLECTED]"
    
    def get_symptoms(self) -> str:
        return self.patient.symptoms or "[NOT COLLECTED]"
    
    def get_doctor_name(self) -> str:
        return self.booking.doctor_name or "[NOT SELECTED]"
    
    def get_slot_info(self) -> str:
        if self.booking.selected_slot_date and self.booking.selected_slot_time:
            return f"{self.booking.selected_slot_date} at {self.booking.selected_slot_time}"
        return "[NOT SELECTED]"
