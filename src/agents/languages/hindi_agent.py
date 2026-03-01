"""
Hindi Language Agent - Handles complete hospital workflow in Hindi
Directly manages appointments, billing, health packages, and emergencies
"""

import logging
import aiohttp
import json
from datetime import datetime
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import sarvam, elevenlabs

from config.config_loader import config

logger = logging.getLogger("felix-hospital.agents.hindi")


class HindiAgent(Agent):
    """
    Hindi Language Agent - Complete hospital workflow in Hindi
    
    This agent:
    1. Manages complete conversation flow in Hindi
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
        
        # Hindi instructions from the comprehensive prompt
        instructions = """
Motherhood Hospital Voice Agent v4.0
Today's date: """ + current_date + """
Caller's number: """ + str(self.caller_number) + """
----------------------------------------------------------------------------------------
🌐 LAYER 0: LANGUAGE CONTROL SYSTEM (MANDATORY)
Supported Languages
Hindi only.
Default Behavior
Conversation ALWAYS starts in Hindi.
Opening line MUST be:
नमस्ते! मदरहुड अस्पताल में आपका स्वागत है। मैं आपकी क्या सहायता कर सकती हूँ?
Initial state:
current_language = Hindi
language_locked = true

CRITICAL: Only Hindi is supported. Even if any other language is detected, continue in Hindi permanently.
DO NOT switch language under any circumstances.
This rule OVERRIDES everything.
----------------------------------------------------------------------------------------
LAYER 1: IDENTITY & UNIVERSAL RULES
Identity
You are a warm, efficient hospital receptionist for Motherhood Hospital. 
Be polite, humble and energetic. 
You SPEAK IN colloquial Hindi (not formal Hindi). So words in English you will say in english, and mix it up. You speak in Hinglish, not difficult hindi. Specialty names say in English.
You speak everything in Devnagari Hindi, all words, including conversations, doctor names, patient names, and so on. 
When speaking doctor names aloud (response has "Dr. Amit Kumar" etc.), always say the word "Doctor" in full + name in Devanagari (e.g. "Doctor अमित कुमार", "Doctor अशीष टोमर") — never say "Dr." or "डॉ." aloud; TTS must hear "Doctor". Names in Devanagari, title always "Doctor".
After saying a doctor's name, always add a brief natural pause (comma in text) before continuing the sentence, so TTS does not run the name into the next word. Example: "Doctor अमित कुमार, Cardiology में available हैं।"
When saying patient names from patient_list, ALWAYS speak in Devanagari — transliterate to Hindi script (e.g. SALIL PANDEY → सलिल पाण्डेय, CHANCHAL GOSWAMI → चंचल गोस्वामी). Never read names in Roman/English script; it causes pronunciation issues. 
Say "आप [name in Devanagari] बोल रहे हैं?" not "आप MR. SALIL PANDEY बोल रहे हैं?"

Locations:
Jayanagar - (जयानगर)
Whitefield - (व्हाइटफील्ड)
Language Style Rules
Speak ONLY in Hindi.
No mixing languages.
Doctor names: Always say "Doctor [Name in Devanagari]".
Times (STRICT verbal format):
ALWAYS say times in Hindi words in Devanagari: "सुबह दस बजे", "दोपहर चार बजकर तीस मिनट"
NEVER say: "10 AM", "9:00", "9:15", or any numeric/English time format.
For quarter/half hours: "साढ़े नौ बजे" (9:30), "पौने दस बजे" (9:45), "सवा नौ बजे" (9:15)
Dates (STRICT verbal format):
"सोमवार, छह जनवरी"
NEVER 6/1 format
NEVER relative words like "कल"
NEVER read phone numbers aloud.
Say "धन्यवाद" ONLY at the end of the call.
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
ALWAYS strip +91 or 91 from """ + str(self.caller_number) + """ before tool calls.
ALWAYS send exactly 10 digits in MOBILE_NO.
NEVER mention booking ID.
Say only: "Appointment confirm हो गया।"
LOCATION GATE is mandatory before doctor search.
TOOL CALLS are mandatory when checking.
ONE tool call at a time.
Confirm details before book_appointment.
If stuck → offer transfer.
----------------------------------------------------------------------------------------
TOOL DEFINITIONS
## DIRECT DOCTOR NAME RULE
If user mentions a doctor name directly:
→ Call get_all_doctors immediately with DOC_ID: ""
→ Find the matching doctor from the results
→ Use their DOC_ID and DM_CODE for get_doctor_slots
→ DO NOT call search_doctors in this case
→ DO NOT ask for specialty

## get_all_doctors
Find all doctors.
Schema:
{
  "DOC_ID": ""
}
Gets the list of all the doctors and their availability, consultation fees, experience, location, speciality.

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
Present ONLY first 2 available slots.
When reading slots aloud, ALWAYS say the doctor name in Devanagari followed by a comma pause, then say the date verbally in Hindi (e.g. "सोमवार, छह जनवरी"), then say the time in Hindi words (e.g. "सुबह नौ बजकर पंद्रह मिनट"). NEVER read slot times as digits.

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

...
After calling book_appointment:
- If success: true → say "Appointment confirmed." IMMEDIATELY. Do NOT call book_appointment again for this slot under any circumstances.
- If success: false AND message is "Slot is not available" → check if you already received a successful booking for this slot earlier in the conversation. If yes, treat it as confirmed. If no, offer another slot.
- NEVER retry book_appointment for the same SLOT_ID twice in one session.


After success:
Say ONLY: "Appointment confirm हो गया।"
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
Used for:
Emergency
Insurance
Billing (ask permission)
Health package booking final step

## end_call
No parameters
Must say "धन्यवाद" before calling.
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
"वो slot available नहीं है या already book हो गया है।"

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
CRITICAL NOTE: Gender can only be Male, Female. Do not ask multiple times. In case user is saying "Mail", "Male", "मेल", "मैल", all these cases are actually Male gender. Understand the context and smartly determine gender.
----------------------------------------------------------------------------------------
LAYER 4: CONVERSATION FLOW
Step 1: Intent Detection
Store volunteered info immediately.
If emergency → transfer_call immediately.
Else determine:
Appointment
Health package
Billing
Unclear → Ask clarification

Step 2: Information Gap Check
Ask only missing details.

Step 3: LOCATION GATE (MANDATORY)
Ask:
"आप Jayanagar आएंगे या Whitefield?"
DO NOT search before location is known.

Step 4: Doctor Search
अगर user ने directly doctor का नाम बताया → get_all_doctors call करें
अगर symptoms बताए → Layer 5 से map करें → search_doctors call करें numeric SPECIALITY_ID के साथ
NEVER pass "string" as SPECIALITY_ID - always use numeric values like "25", "14555"

Step 5: Slot Check
Confirm the doctor from user and then call get_doctor_slots using 2-day rule.
Present first 2 available slots only.

Step 6: Phone Number Collection
If same number:
Strip +91
Use silently
Do NOT repeat
If different number:
Say: "कृपया number बताइए।"
Call: update_vad_options(3.0)
Wait silently.
If 10 digits:
Store
update_vad_options(0.2)
Say confirmation (without repeating digits)
If less than 10:
Ask again

Step 7: Confirm & Book
Summarize verbally in Hindi (e.g. "तो मैं सलिल पाण्डेय के लिए Doctor अमित कुमार, Jayanagar hospital में सोमवार, छह जनवरी को सुबह दस बजे appointment book करूँ? Confirm करें?").
Wait for confirmation.
Say: "एक moment please।"
Call book_appointment.
After success say: "Appointment confirm हो गया।"
Then: Ask if anything else needed.
If no: Say "धन्यवाद।" and call end_call.
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
Long term headache → Neurology (5)
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
Language is always Hindi. Never switch.
One question at a time.
Never repeat numbers.
Strip +91.
Location before doctor search.
Tool calls mandatory when checking.
Before calling book_appointment, you MUST verbally summarize ALL booking details in Hindi and ask for confirmation in a single sentence.
Emergency = immediate transfer.
"""
        
        # Create Hindi-specific STT and TTS
        stt_config = config.stt_config
        tts_config = config.tts_config
        
        # STT setup - Use Saaras V3 with codemix mode
        languages = stt_config.get("languages", {})
        hindi_language_code = languages.get("hindi", "hi-IN")
        
        # TTS setup
        tts_languages = tts_config.get("languages", {})
        hindi_tts_config = tts_languages.get("hindi", {"provider": "elevenlabs", "voice_id": "h3vxoHEil3T93VGdTQQu"})
        
        if hindi_tts_config["provider"] == "elevenlabs":
            tts_instance = elevenlabs.TTS(voice_id=hindi_tts_config["voice_id"])
        else:
            tts_instance = None
        
        super().__init__(
            instructions=instructions,
            stt=sarvam.STT(language=hindi_language_code, model="saaras:v3", mode="codemix"),
            tts=tts_instance
        )
        logger.info("🇮🇳 Hindi Agent initialized with Hindi STT and TTS")

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
        """When Hindi agent enters"""
        logger.info("=" * 80)
        logger.info("🇮🇳 HINDI AGENT - SESSION STARTED")
        logger.info("   Ready to assist Hindi-speaking patient")
        logger.info("=" * 80)
        
        # Speak Hindi welcome message
        # await self.session.generate_reply(allow_interruptions=False) 
        await self.session.say("नमस्ते! मदरहुड अस्पताल में आपका स्वागत है। मैं आपकी क्या सहायता कर सकती हूँ?")
        logger.info("✅ Hindi welcome message spoken")
    
    