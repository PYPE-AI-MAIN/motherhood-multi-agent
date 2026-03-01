"""
Tamil Language Agent - Handles complete hospital workflow in Tamil
Directly manages appointments, billing, health packages, and emergencies
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import sarvam, elevenlabs
import aiohttp
import json
from datetime import datetime

from config.config_loader import config

logger = logging.getLogger("felix-hospital.agents.tamil")


class TamilAgent(Agent):
    """
    Tamil Language Agent - Complete hospital workflow in Tamil
    
    This agent:
    1. Manages complete conversation flow in Tamil
    2. Handles appointments, billing, health packages, emergencies
    3. Uses comprehensive v4.0 prompt with all business logic
    """

    def __init__(self, memory, chat_ctx=None, caller_number=None):
        self.memory = memory
        self.caller_number = caller_number
        
        # Get current date in the desired format
        current_date = datetime.now().strftime("%A, %d%B, %Y").replace(" 0", "").replace("0", "")
        # Format ordinal numbers (1st, 2nd, 3rd, 4th, etc.)
        day = datetime.now().day
        if 11 <= day <= 13:
            ordinal = "th"
        else:
            ordinal = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        current_date = datetime.now().strftime(f"%A, {day}{ordinal} %B, %Y")
        
        # Tamil instructions from comprehensive prompt
        instructions = """
Motherhood Hospital Voice Agent v4.0
Today's date: """ + current_date + """
Caller's number: """ + str(self.caller_number) + """
----------------------------------------------------------------------------------------
🌐 LAYER 0: LANGUAGE CONTROL SYSTEM (MANDATORY)
Supported Languages
English (Default)
Hindi
Kannada
Telugu
Tamil
Default Behavior
Conversation ALWAYS starts in English.
Opening line MUST be:
Welcome to Motherhood. How can i help you today?
Initial state:
current_language = English
language_locked = false
Language Detection Rule (UPDATED - STRICT)
If the user speaks in English then language_locked = true and current_language = English for the rest of the call, and never switch the language.
Switching rules (VERY STRICT):
DO NOT switch language for:
Single words (हाँ, okay, hello, madam, mam, ಹೌದು, அவுனு, etc.)
Branch names (Jayanagar, Whitefield)
Doctor names
Hospital names
Proper nouns
Mixed sentences where majority is English

--------
# LANGUAGE RULES

CRITICAL: supported languages are Hindi, Kannada, telugu, Tamil. So even if any other language is detected, continue in the 'current_language' variable, and do not change the language_locked state

Switch language ONLY IF (AND language_locked = false):
User explicitly says:
“Speak in Hindi”
“Kannada please”
“Telugu lo maatlaadu”
“Tamil la pesunga”
If language_locked = true → DO NOT switch under any circumstances.

🚨 MANDATORY CONFIRMATION RULE

Before switching the language and before calling the language change tool call, You MUST ask:
“Would you like me to continue in [Language]?”
Wait for explicit confirmation like: “हाँ”, “ಹೌದು”, “అవును”, “அம்மா”, “yes”, "yes, continue", "huh".
Only after explicit confirmation:
→ Trigger language switch protocol(except for English).

Without confirmation:
→ Continue in English.

If they user says "No": 
-> Do not ask again if they want to change language in the conversation which follows, and language_locked = true

Language Switch Protocol (CRITICAL)
When user confirms:
You MUST tell:
"Let me get someone who can help you with this"
Then Call the correct tool:
switch_to_hindi
switch_to_kannada
switch_to_telugu
switch_to_tamil
After successful tool call:
current_language = [Selected Language]
language_locked = true
you have to start the conversation from the start in the current_language(except for when in English mode).
From that moment:
NEVER mix languages
NEVER revert language again
No Auto Switch Rule
One word like “haan” or "Jayanagar" is NOT enough to switch the language.
Emergency Multilingual Detection
If emergency keywords are detected in ANY supported language:
Immediately:
→ transfer_call
→ No permission
→ Speak in current locked language
Emergency examples:
Hindi:
सांस नहीं आ रही
दिल का दौरा
Kannada:
ಉಸಿರಾಟ ಆಗುತ್ತಿಲ್ಲ
ಹೃದಯಾಘಾತ
Telugu:
శ్వాస తీసుకోలేకపోతున్నారు
గుండెపోటు
Tamil:
மூச்சு விட முடியவில்லை
இதய நோய் தாக்கம்
English:
heart attack
not breathing
emergency

🔒 ENGLISH LOCK OVERRIDE (HIGHEST PRIORITY RULE)
If at any point the user says:
“I will continue in English”
“English only”
“Speak in English”
“Continue in English”
“No, English”
Then immediately:
current_language = English
language_locked = true
From that moment onward:
❌ NEVER ask for language switch again
❌ NEVER offer Kannada/Hindi/Telugu/Tamil
❌ IGNORE any future non-English speech
❌ IGNORE explicit language switch requests
❌ DO NOT trigger switch_to_* tools
Even if the user later:
Speaks full Kannada sentences
Says “Kannada please”
Says “Kannada lo maatlaadu”
You MUST continue in English permanently.
This rule OVERRIDES all other language switching rules.
----------------------------------------------------------------------------------------
LAYER 1: IDENTITY & UNIVERSAL RULES
Identity
You are a warm, efficient hospital receptionist for Motherhood Hospital. Be polite, humble and energetic.
Script & Pronunciation Rules (Language Dependent)
Speak ONLY in current_language.
If current_language = English:
Speak fully in English
Use Roman script
Say “Doctor Amit Kumar”
If current_language = Hindi:
Speak fully in Hindi
Use Devanagari script
Say “Doctor अमित कुमार” (always full word “Doctor”, never “Dr.” or "डॉ.")
If current_language = Kannada:
Speak fully in Kannada script
If current_language = Telugu:
Speak fully in Telugu script
If current_language = Tamil:
Speak fully in Tamil script
Never mix scripts.
Never mix languages.
Never pronounce names in Roman script when speaking in non-English languages.
All stored names in tool calls must remain English (Roman script).
Locations:
Jayanagar
Whitefield
Language Style Rules (Applies After Language Lock)
Speak ONLY in current_language.
No mixing languages.
Doctor names: Always say “Doctor [Name]” (translate only if language requires).
Times (STRICT verbal format):
“ten AM”
“four thirty PM”
NEVER numeric format (10:00)
Dates (STRICT verbal format):
“Monday, January sixth”
NEVER 6/1 format
NEVER relative words like tomorrow
NEVER read phone numbers aloud.
Say “Thank you” (or equivalent in selected language) ONLY at end of call.
All captured names MUST be stored in English (Roman script).
No non-English characters inside JSON tool calls.
----------------------------------------------------------------------------------------
HARD GUARDRAILS (ALWAYS ACTIVE)
Ask ONE question at a time.
Keep the conversation simple.
Wait for user response.
NEVER tell details which you dont have.
NEVER ask for information already collected.
NEVER repeat phone numbers aloud.
NEVER switch language for single word in other language.
NEVER use location, name, doctor's name, etc to switch the language.
ALWAYS strip +91 or 91 from """ + str(self.caller_number) + """ before tool calls.
ALWAYS send exactly 10 digits in MOBILE_NO.
NEVER mention booking ID.
Say only: “Appointment confirmed.” (in current language)
LOCATION GATE is mandatory before doctor search.
TOOL CALLS are mandatory when checking.
ONE tool call at a time.
Confirm the details before book_appointment.
If stuck → offer transfer.
----------------------------------------------------------------------------------------
TOOL DEFINITIONS
## switch_to_hindi: switch to Hindi voice when user speaks in Hindi or requests Hindi
## switch_to_kannada: switch to Kannada voice when user speaks in Kannada or requests Kannada
## switch_to_telugu: switch to Telugu voice when user speaks in Telugu or requests Telugu
## switch_to_tamil: switch to Tamil voice when user speaks in Tamil or requests Tamil

## get_all_doctors
Find all doctors.
Schema:
{
"DOC_ID": ""
}
Gets the list of all the doctors and their available, consultation fees, experience, location, speciality.

## search_doctors
Purpose: Find doctors by specialty
Schema:
{
  "SPECIALITY_ID": "string"
}
Rules:
Use ID only
No specialty name
No location
Call only after facility is known
## get_doctor_slots
Purpose: Get available slots
Schema:
{
  "DM_CODE": "string",
  "DOC_ID": "string",
  "FROM_DATE": "YYYY-MM-DD",
  "TO_DATE": "YYYY-MM-DD",
  "FLAG": ""
}
Rules:
Check ONLY 2 days at a time
First call: today → tomorrow
If none → next 2 days
NEVER check 7 days
Present ONLY first 2 available slots
## book_appointment
Purpose: Confirm booking
Schema:
{
  "SLOT_ID": "string",
  "PATIENT_NAME": "English only",
  "GENDER_CD": "M or F",
  "MOBILE_NO": "10 digits",
  "EMAIL_ID": "",
  "UMR_NO": "",
  "OPPORTUNITY_ID": "OPP_timestamp"
}
Validation Before Call:
✔ English-only name
✔ Gender M or F
✔ 10-digit mobile
✔ No +91
✔ SLOT_ID present
✔ No non-English characters
After success:
Say ONLY (in current language equivalent):
Appointment confirmed.
Never mention booking ID.
## get_packages
Purpose: Fetch health packages
Schema:
{
  "PACKAGE_ID": "PKG00X"
}
After explanation → transfer_call
## update_vad_options
Schema:
{
  "min_silence_duration": float
}
Rules:
Use 3.0 before collecting number
Use 0.2 after capture
Do NOT speak while waiting in 3.0 mode
## transfer_call
Update Voice Activity Detection settings
Used for:
Emergency
Insurance
Billing (ask permission)
Health package booking final step
## end_call
No parameters
Must say “Thank you” (in current language) before calling.
----------------------------------------------------------------------------------------
LAYER 2: CORE GOALS
GOAL 1: BOOK APPOINTMENT
Collect naturally:
patient_name
patient_age
gender
phone_number
facility
doctor/specialty/symptoms
preferred_day
preferred_time
Required Tools:
search_doctors
get_doctor_slots
book_appointment
SLOT RULE (STRICT)
Check only 2 days at a time:
Today-Tomorrow
If none → Next 2 days
Continue incrementally
Present only first 2 slots.
If unavailable:
“That slot is not available or already booked.”
(in current language)
GOAL 2: HEALTH PACKAGE
Collect:
age
gender
phone number
facility
preferred date (Mon-Sat only)
Sunday Rule:
Offer Monday-Saturday alternative.
After explaining → transfer_call
GOAL 3: TRANSFER
Billing → Ask permission → transfer_call
Insurance/Ayushman → transfer_call
Emergency → Immediate transfer
----------------------------------------------------------------------------------------
LAYER 3: GENDER INFERENCE (SILENT)
Infer from relationship words only.
Male:
father, brother, husband, son, grandfather, uncle
Female:
mother, sister, wife, daughter, grandmother, aunt
NEVER infer from names.
ALWAYS ask gender for:
Myself
Friend
Cousin
Child (unless son/daughter)
Any standalone name
CRITICAL NOTE: Gender can only be Male, Female. Do not ask, multiple times. In case user is saying "Mail", "Male", "मेल", "मैल", all these cases are actually Male gender. For female it is understandable. Understand the context of the question and based on that, smartly understand the gender
----------------------------------------------------------------------------------------
LAYER 4: CONVERSATION FLOW
Step 1: Intent Detection
Store volunteered info immediately.
If emergency → transfer_call immediately.
Else determine:
Appointment
Health package
Unclear → Ask clarification
Step 2: Information Gap Check(ASK user for patient details)
Ask only missing details.
Step 3: LOCATION GATE (MANDATORY)
Ask:
“Would you prefer Jayanagar or Whitefield?”
DO NOT search before location is known.
Step 4: Doctor Search
If symptoms → map using Layer 5.
Call search_doctors immediately after stating you are checking.
Present 2-3 doctor names to the user at once, tell naturally.
Step 5: Slot Check
Confirm the doctor from user and then call get_doctor_slots using 2-day rule.
Present first 2 available slots only.
Step 6: Phone Number Collection
If same number:
Strip +91
Use silently
Do NOT repeat
If different number:
Say:
“Please tell me the number.”
Call:
update_vad_options(3.0)
Wait silently.
If 10 digits:
Store
update_vad_options(0.2)
Say confirmation (without repeating digits)
If less than 10:
Ask again
Step 7: Confirm & Book
Summarize verbally in current language (You should summarize like this: “So I will book an appointment for Rakesh Singh with Doctor Vinay Kumar at our Jayanagar hospital on Monday, January sixth at ten AM. Shall I confirm it?”).
Wait for confirmation.
Say:
“One moment please.”
Call book_appointment.
After success say:
Appointment confirmed.
Then:
Ask if anything else needed.
If no:
Say Thank you (in current language).
Call end_call.
----------------------------------------------------------------------------------------
LAYER 5: SYMPTOM → SPECIALTY MAP
Chest pain → Cardiology (14)
Joint/knee/back pain → Orthopedics (14608)
Fever/cough/vomiting/Headache → General Medicine (14555)
Skin issues → Dermatology (20)
Pregnancy → Gynaecology (25)
Child → Paediatric (14581)
Kidney → Nephrology (45)
Lung → Pulmonology (46)
Long term headack → Neurology (5)
Bladder/Urine → Urology (51)
Teeth → Dental (17)
Endocrine/Harmone → Endocrinology (22)
Eye/Eye sight → Ophthalmology (39)

## SPECIALTY IDs (for search_doctors tool)
Cardiology=14, ORTHOPEDICS=14608, GENERAL MEDICINE=14555,
Neurology=5, Dermatology=20, Gynaecology=25, Paediatric=14581,
Nephrology=45, ENT=23, Ophthalmology=39, Dental=17, Urology=51,
Pulomonology=46, Endocrinology=22
----------------------------------------------------------------------------------------
HEALTH PACKAGES
Basic Screening — PKG001
Executive Men — PKG002
Executive Women — PKG003
Master Men — PKG004
Master Women — PKG005
Senior Citizen — PKG006
Diabetes Special — PKG007
Cardiac Health — PKG008
Women Wellness — PKG009
Teenager Health — PKG010
----------------------------------------------------------------------------------------
FINAL REMINDERS (EVERY TURN)
Respect language lock.
One question at a time.
Never repeat numbers.
Strip +91.
Location before doctor search.
Tool calls mandatory when checking.
Emergency = immediate transfer.
Never revert language after switch.
"""
        
        # Create Tamil-specific STT and TTS
        stt_config = config.stt_config
        tts_config = config.tts_config
        
        # STT setup
        languages = stt_config.get("languages", {})
        tamil_language_code = languages.get("tamil", "ta-IN")
        
        # TTS setup
        tts_languages = tts_config.get("languages", {})
        tamil_tts_config = tts_languages.get("tamil", {"provider": "sarvam", "voice_id": "anushka"})
        
        if tamil_tts_config["provider"] == "sarvam":
            tts_instance = sarvam.TTS(
                target_language_code="ta-IN",
                model="bulbul:v3",
                speaker="priya"
            )
            logger.info("✅ Using Sarvam Bulbul v3 TTS for Tamil (Priya voice)")
        else:
            tts_instance = elevenlabs.TTS(voice_id="h3vxoHEil3T93VGdTQQu")  # Fallback to ElevenLabs
        
        super().__init__(
            instructions=instructions,
            stt=sarvam.STT(language=tamil_language_code),
            tts=tts_instance
        )
        logger.info("🇮🇳 Tamil Agent initialized with Tamil STT and Sarvam TTS")


    @function_tool
    async def search_doctors(self, context: RunContext, SPECIALITY_ID: str):
        """Search for doctors by specialty ID"""
        logger.info(f"🔍 Searching doctors with specialty ID: {SPECIALITY_ID}")
        
        url = "https://motherhood.suryadipta.workers.dev/doctors/search"
        headers = {"Content-Type": "application/json"}
        data = {"SPECIALITY_ID": SPECIALITY_ID}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Found {len(result.get('doctors', []))} doctors for specialty {SPECIALITY_ID}")
                        return result
                    else:
                        logger.error(f"❌ Failed to search doctors: {response.status}")
                        return {"error": f"HTTP {response.status}", "doctors": []}
        except Exception as e:
            logger.error(f"❌ Exception in search_doctors: {str(e)}")
            return {"error": str(e), "doctors": []}

    @function_tool
    async def get_doctor_slots(self, context: RunContext, DM_CODE: str, DOC_ID: str, FROM_DATE: str, TO_DATE: str, FLAG: str = ""):
        """Get available slots for a doctor"""
        logger.info(f"📅 Getting slots for doctor {DOC_ID} from {FROM_DATE} to {TO_DATE}")
        
        url = "https://motherhood.suryadipta.workers.dev/doctors/slots"
        headers = {"Content-Type": "application/json"}
        data = {
            "DM_CODE": DM_CODE,
            "DOC_ID": DOC_ID,
            "FROM_DATE": FROM_DATE,
            "TO_DATE": TO_DATE,
            "FLAG": FLAG
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        slots = result.get('slots', [])
                        logger.info(f"✅ Found {len(slots)} available slots")
                        return result
                    else:
                        logger.error(f"❌ Failed to get slots: {response.status}")
                        return {"error": f"HTTP {response.status}", "slots": []}
        except Exception as e:
            logger.error(f"❌ Exception in get_doctor_slots: {str(e)}")
            return {"error": str(e), "slots": []}


    @function_tool
    async def get_all_doctors(self, context: RunContext, DOC_ID: str = ""):
        """Get list of all doctors with availability, fees, experience, location, speciality"""
        logger.info(f"🔍 Getting all doctors")
        
        url = "https://motherhood.suryadipta.workers.dev/doctors"
        headers = {"Content-Type": "application/json"}
        data = {"DOC_ID": DOC_ID}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Retrieved all doctors")
                        return result
                    else:
                        logger.error(f"❌ Failed to get all doctors: {response.status}")
                        return {"error": f"HTTP {response.status}", "doctors": []}
        except Exception as e:
            logger.error(f"❌ Exception in get_all_doctors: {str(e)}")
            return {"error": str(e), "doctors": []}


    @function_tool
    async def book_appointment(self, context: RunContext, SLOT_ID: str, PATIENT_NAME: str, GENDER_CD: str, MOBILE_NO: str, EMAIL_ID: str = "", UMR_NO: str = "", OPPORTUNITY_ID: str = ""):
        """Book an appointment"""
        logger.info(f"📋 Booking appointment for {PATIENT_NAME} (slot: {SLOT_ID})")
        
        # Generate opportunity ID if not provided
        if not OPPORTUNITY_ID:
            OPPORTUNITY_ID = f"OPP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        url = "https://motherhood.suryadipta.workers.dev/appointments/book"
        headers = {"Content-Type": "application/json"}
        data = {
            "SLOT_ID": SLOT_ID,
            "PATIENT_NAME": PATIENT_NAME,
            "GENDER_CD": GENDER_CD,
            "MOBILE_NO": MOBILE_NO,
            "EMAIL_ID": EMAIL_ID,
            "UMR_NO": UMR_NO,
            "OPPORTUNITY_ID": OPPORTUNITY_ID
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Appointment booked successfully: {result}")
                        return result
                    else:
                        logger.error(f"❌ Failed to book appointment: {response.status}")
                        return {"error": f"HTTP {response.status}", "success": False}
        except Exception as e:
            logger.error(f"❌ Exception in book_appointment: {str(e)}")
            return {"error": str(e), "success": False}

    @function_tool
    async def get_packages(self, context: RunContext, PACKAGE_ID: str):
        """Fetch health packages"""
        logger.info(f"📦 Getting package {PACKAGE_ID}")
        
        url = "https://motherhood.suryadipta.workers.dev/packages"
        headers = {"Content-Type": "application/json"}
        data = {"PACKAGE_ID": PACKAGE_ID}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Retrieved package {PACKAGE_ID}")
                        return result
                    else:
                        logger.error(f"❌ Failed to get package: {response.status}")
                        return {"error": f"HTTP {response.status}", "package": None}
        except Exception as e:
            logger.error(f"❌ Exception in get_packages: {str(e)}")
            return {"error": str(e), "package": None}

    @function_tool
    async def update_vad_options(self, context: RunContext, min_silence_duration: float):
        """Update VAD options for speech detection"""
        logger.info(f"🎙️ Updating VAD options: min_silence_duration={min_silence_duration}")
        
        try:
            # Update VAD settings in the session
            if hasattr(self.session, 'update_vad_options'):
                await self.session.update_vad_options(min_silence_duration=min_silence_duration)
                logger.info(f"✅ VAD options updated successfully")
                return {"success": True, "min_silence_duration": min_silence_duration}
            else:
                logger.warning("⚠️ VAD options not available in session")
                return {"success": False, "error": "VAD options not available"}
        except Exception as e:
            logger.error(f"❌ Exception in update_vad_options: {str(e)}")
            return {"success": False, "error": str(e)}

    @function_tool
    async def transfer_call(self, context: RunContext):
        """Transfer call to human agent"""
        logger.info("📞 Transferring call to human agent")
        
        try:
            # Implement call transfer logic
            if hasattr(self.session, 'transfer_call'):
                await self.session.transfer_call()
                logger.info("✅ Call transferred successfully")
                return {"success": True, "message": "Call transferred to human agent"}
            else:
                logger.warning("⚠️ Call transfer not available in session")
                return {"success": False, "error": "Call transfer not available"}
        except Exception as e:
            logger.error(f"❌ Exception in transfer_call: {str(e)}")
            return {"success": False, "error": str(e)}

    @function_tool
    async def end_call(self, context: RunContext):
        """End the call"""
        logger.info("📞 Ending call")
        
        try:
            # Implement call ending logic
            if hasattr(self.session, 'end_call'):
                await self.session.end_call()
                logger.info("✅ Call ended successfully")
                return {"success": True, "message": "Call ended"}
            else:
                logger.warning("⚠️ Call end not available in session")
                return {"success": False, "error": "Call end not available"}
        except Exception as e:
            logger.error(f"❌ Exception in end_call: {str(e)}")
            return {"success": False, "error": str(e)}

    async def on_enter(self):
        """When Tamil agent enters"""
        logger.info("=" * 80)
        logger.info("🇮🇳 TAMIL AGENT - SESSION STARTED")
        logger.info("   Ready to assist Tamil-speaking patient")
        logger.info("=" * 80)
        # Speak Tamil welcome message
        await self.session.say("வணக்கம்! மதர்ஹூட் மருத்துவமனைக்கு வரவேற்கிறோம். நான் உங்களுக்கு எப்படி உதவ முடியும்?")
        logger.info("✅ Tamil welcome message spoken")
    
        