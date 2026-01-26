"""
Felix Hospital Appointment Booking Agent
Single agent with Living Memory for natural conversations
"""

from livekit.agents import Agent, llm, function_tool, RunContext
from livekit.agents.voice import Agent as VoiceAgent
from core.memory import LivingMemory
from core.state import SessionState
from tools.felix_api import felix_api
from utils.symptom_mapper import map_symptom_to_specialty
from utils.date_helpers import get_today, get_tomorrow, add_days, format_date_natural
import structlog

logger = structlog.get_logger()


class FelixHospitalAgent(VoiceAgent):
    """
    Main appointment booking agent for Felix Hospital
    Uses Living Memory to maintain context
    """
    
    def __init__(self, memory: LivingMemory):
        self.memory = memory
        self.session_state = memory.session_state
        
        # Agent instructions (based on your Felix Hospital prompt)
        instructions = f"""
You are a voice receptionist for Felix Hospital. You handle appointment bookings naturally, like a helpful human receptionist would.

## YOUR IDENTITY
Name: Felix Hospital Receptionist 
Persona: Warm, efficient, speaks Hindi-English mix naturally
Locations: Noida (Sector 137), Greater Noida (Gamma 1)

Opening: "नमस्ते! Felix Hospital से बात हो रही है। बताइए, क्या help चाहिए?"

## YOUR TASK
Help patients book doctor appointments by:
1. Collecting patient information (name, age, gender, phone, facility, symptoms)
2. Finding suitable doctors
3. Showing available slots
4. Confirming booking

## IMPORTANT RULES
- Speak Hindi-English mix naturally
- Ask ONE question at a time
- Never repeat questions if you already know the answer (check the PATIENT CARD)
- Times in English: "ten AM", "four thirty PM" (NOT "10:00", NOT "दस बजे")
- Never read phone numbers aloud - just confirm "same number"
- Acknowledge briefly: "ठीक है", "समझ गई" (NOT "धन्यवाद" mid-conversation)
- Always check PATIENT INFORMATION CARD before asking questions

## CONVERSATION FLOW
1. Greet warmly
2. Ask what help they need
3. If appointment: collect info one by one
4. Search for doctors
5. Present slots (first 2 options)
6. Confirm booking
7. Done!

## MEMORY SYSTEM
You have a PATIENT INFORMATION CARD that shows what you already know.
BEFORE asking ANY question, check the card!
If information is already there, DON'T ask again!

Today's date: {get_today()}

Remember: You're helping real patients. Be warm, efficient, and never forget what they tell you!
"""
        
        super().__init__(instructions=instructions)
    
    async def on_user_turn_completed(self, turn_ctx, new_message):
        """
        Called before LLM processes user message
        Inject Living Memory here
        """
        # Inject memory block at the end (high attention area)
        memory_block = self.memory.to_context_block()
        turn_ctx.add_message(
            role="system",
            content=memory_block
        )
        
        logger.info("memory_injected", memory=memory_block)
    
    # ============================================================================
    # TOOLS - Functions the agent can call
    # ============================================================================
    
    @function_tool()
    async def update_patient_info(
        self,
        ctx: RunContext,
        name: str = None,
        age: int = None,
        gender: str = None,
        phone: str = None,
        facility: str = None,
        symptoms: str = None
    ) -> str:
        """
        Update patient information in memory.
        Call this when you learn new information about the patient.
        
        Args:
            name: Patient's full name
            age: Patient's age
            gender: M or F
            phone: Phone number
            facility: Noida or Greater Noida
            symptoms: What problem patient has
        """
        updates = {}
        if name:
            updates['name'] = name
        if age:
            updates['age'] = age
        if gender:
            updates['gender'] = gender
        if phone:
            updates['phone'] = phone
        if facility:
            updates['facility'] = facility
        if symptoms:
            updates['symptoms'] = symptoms
        
        self.memory.update_patient_info(**updates)
        
        logger.info("patient_info_updated", updates=updates)
        
        return f"Patient info updated: {', '.join(f'{k}={v}' for k, v in updates.items())}"
    
    @function_tool()
    async def search_doctors_and_slots(
        self,
        ctx: RunContext,
        symptoms: str = None
    ) -> str:
        """
        Search for doctors based on patient symptoms and show available slots.
        This combines doctor search + slot availability.
        
        Args:
            symptoms: Patient symptoms (if not already in memory)
        """
        # Use symptoms from memory if not provided
        if not symptoms:
            symptoms = self.session_state.patient.symptoms
        
        if not symptoms:
            return "Please tell me the patient's symptoms first."
        
        # Map symptoms to specialty
        specialty_id, specialty_name = map_symptom_to_specialty(symptoms)
        
        logger.info("searching_doctors", symptoms=symptoms, specialty=specialty_name)
        
        # Search doctors
        facility = self.session_state.patient.facility
        doctors = await felix_api.search_doctors(specialty_id, facility)
        
        if not doctors:
            return f"No {specialty_name} doctors found. Please try different facility or symptoms."
        
        # Get first doctor
        doctor = doctors[0]
        
        # Update booking info
        self.memory.update_booking_info(
            doctor_id=doctor['doctor_id'],
            doctor_name=doctor['name'],
            doctor_specialty=specialty_name,
            booking_stage="searching"
        )
        
        # Search slots for next 2 days
        from_date = get_today()
        to_date = add_days(from_date, 2)
        
        slots = await felix_api.get_doctor_slots(
            doctor['doctor_id'],
            from_date,
            to_date
        )
        
        if not slots:
            # Try next 2 days
            from_date = add_days(from_date, 2)
            to_date = add_days(from_date, 2)
            slots = await felix_api.get_doctor_slots(
                doctor['doctor_id'],
                from_date,
                to_date
            )
        
        if not slots:
            return f"{doctor['name']} has no available slots in next few days."
        
        # Format first 2 slots for natural presentation
        first_slot = slots[0]
        second_slot = slots[1] if len(slots) > 1 else None
        
        result = f"Found {doctor['name']} ({specialty_name}).\n\n"
        result += f"Available: {first_slot['day_of_week']} {first_slot['time']}"
        if second_slot:
            result += f" or {second_slot['time']}"
        
        # Store slots in booking info for later
        self.memory.update_booking_info(booking_stage="slot_selection")
        ctx.userdata['available_slots'] = slots[:10]  # Store first 10 slots
        
        return result
    
    @function_tool()
    async def confirm_booking(
        self,
        ctx: RunContext,
        slot_time: str,
        slot_date: str = None
    ) -> str:
        """
        Confirm and book the appointment.
        
        Args:
            slot_time: Time like "10:00 AM", "eleven AM"
            slot_date: Date if specified, otherwise uses next available
        """
        patient = self.session_state.patient
        booking = self.session_state.booking
        
        # Validate we have all info
        if not patient.name:
            return "I need the patient's name first."
        if not patient.age:
            return "I need the patient's age first."
        if not patient.phone:
            return "I need the phone number first."
        if not booking.doctor_id:
            return "Please let me search for doctors first."
        
        # Get available slots
        available_slots = ctx.userdata.get('available_slots', [])
        if not available_slots:
            return "No slots available. Please search again."
        
        # Find matching slot
        selected_slot = None
        for slot in available_slots:
            if slot_time.lower() in slot['time'].lower():
                if not slot_date or slot_date in slot['date']:
                    selected_slot = slot
                    break
        
        if not selected_slot:
            return f"Could not find slot for {slot_time}. Please choose from available times."
        
        # Book appointment
        booking_result = await felix_api.book_appointment(
            slot_id=selected_slot['slot_id'],
            patient_name=patient.name,
            patient_age=patient.age,
            gender=patient.gender or "M",
            phone=patient.phone,
            doctor_id=booking.doctor_id
        )
        
        # Update memory
        self.memory.update_booking_info(
            booking_id=booking_result['booking_id'],
            selected_slot_id=selected_slot['slot_id'],
            selected_slot_time=selected_slot['time'],
            selected_slot_date=selected_slot['date'],
            booking_stage="completed"
        )
        
        logger.info("booking_confirmed", booking_id=booking_result['booking_id'])
        
        # Return confirmation (WITHOUT booking ID - as per requirements)
        day_name = selected_slot['day_of_week']
        date_formatted = format_date_natural(selected_slot['date'])
        
        return f"Appointment confirmed for {patient.name} with {booking.doctor_name} on {day_name}, {date_formatted} at {selected_slot['time']}. WhatsApp confirmation will be sent."
