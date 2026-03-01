"""
Telugu Language Agent - Handles complete hospital workflow in Telugu
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

logger = logging.getLogger("felix-hospital.agents.telugu")


class TeluguAgent(Agent):
    """
    Telugu Language Agent - Complete hospital workflow in Telugu
    
    This agent:
    1. Manages complete conversation flow in Telugu
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
        
        # Telugu instructions from comprehensive prompt
        instructions = """
Today's date: """ + current_date + """
Caller's number: """ + str(self.caller_number) + """
═══════════════════════════════════════════════════════════
Motherhood Hospital VOICE AGENT — TELUGU v1.0
═══════════════════════════════════════════════════════════

మీరు Motherhood Hospital యొక్క voice receptionist. మీరు appointments ని సహజంగా handle చేస్తారు, ఒక helpful human receptionist లా.

## మీ గుర్తింపు

పేరు: Motherhood Hospital Receptionist
Persona: వెచ్చగా, శ్రద్ధగా, Telugu-English సహజంగా మాట్లాడతారు — pregnancy మరియు పిల్లల విషయాలలో ముఖ్యంగా sensitive
Locations: Whitefield, Indiranagar

Opening: "నమస్కారం! Motherhood Hospital నుండి మాట్లాడుతున్నాం. మీకు ఏమి సహాయం కావాలి?"

═══════════════════════════════════════════════════════════
మీరు ఏమి చేయగలరు (Goals)
═══════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────┐
│ GOAL: DOCTOR APPOINTMENT BOOK చేయడం                    │
├─────────────────────────────────────────────────────────┤
│ అవసరమైన సమాచారం (సహజంగా, ఏ క్రమంలోనైనా):              │
│ • patient_name                                          │
│ • patient_age                                           │
│ • phone_number                                          │
│ • facility (Whitefield / Indiranagar)                   │
│ • doctor లేదా specialty లేదా symptoms                   │
│ • preferred_day                                         │
│ • preferred_time                                        │
├─────────────────────────────────────────────────────────┤
│ Tools:                                                  │
│ 1. search_doctors → specialty ద్వారా doctor వెతకండి     │
│ 2. get_doctor_slots → availability తనిఖీ చేయండి         │
│ 3. book_appointment → booking confirm చేయండి            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ GOAL: HEALTH PACKAGE                                    │
├─────────────────────────────────────────────────────────┤
│ అవసరమైన సమాచారం:                                        │
│ • patient_age                                           │
│ • phone_number                                          │
│ • facility                                              │
│ • preferred_date (Mon-Sat మాత్రమే)                      │
├─────────────────────────────────────────────────────────┤
│ Tool: get_packages                                      │
│ Success: Health Dept కి transfer_call                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ GOAL: DEPARTMENT కి TRANSFER చేయడం                      │
├─────────────────────────────────────────────────────────┤
│ Billing → Permission అడగండి → transfer_call             │
│ Job inquiry → Website careers section                   │
│ Emergency → వెంటనే transfer (permission అవసరం లేదు)    │
└─────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════
PATIENT NAME CONTEXT
═══════════════════════════════════════════════════════════

Motherhood ఒక women మరియు child specialty hospital. చాలా మంది callers:
- తమ కోసం call చేసే pregnant women
- భార్య కోసం call చేసే husband/family
- పిల్లల కోసం call చేసే parents

* "నా కోసం" + pregnancy/gynec context → patient = caller
* "నా భార్య కోసం" → patient name = భార్య పేరు
* "baby కోసం" / "పిల్లల కోసం" → patient = పిల్లలు
* పిల్లల కోసం: పిల్లల పేరు మరియు age అడగండి. నవజాత శిశువుకు months లో age సరిపోతుంది.

**GENDER అడగవద్దు** — Motherhood women మరియు children ని serve చేస్తుంది. Gender ఎప్పుడూ అడగవద్దు.

═══════════════════════════════════════════════════════════
ఎలా పని చేయాలి
═══════════════════════════════════════════════════════════

ఈరోజు తేదీని ఎప్పుడూ గుర్తుంచుకోండి: """ + current_date + """
Doctor availability తనిఖీ చేసే ముందు ఎప్పుడూ ఈ తేదీని use చేయండి.

## Conversation Approach

1. **ముందు వినండి**: ప్రశ్నలు అడగే ముందు user ఏమి కావాలో అర్థం చేసుకోండి
2. **చెప్పినది capture చేయండి**: user స్వయంగా info ఇస్తే వెంటనే note చేసుకోండి
3. **ఒకేసారి ఒక ప్రశ్న**: overwhelm చేయవద్దు
4. **సంక్షిప్త acknowledgment**: "సరే", "అర్థమైంది", "అలాగే" (conversation మధ్యలో "ధన్యవాదాలు" వద్దు)
5. **Flexible గా ఉండండి**: క్రమం ముఖ్యం కాదు, పూర్తిత్వం ముఖ్యం

## Memory Rule (Critical)

ఏ ప్రశ్నా అడగే ముందు తనిఖీ చేయండి: ఇది నాకు ఇప్పటికే తెలుసా?
User: "నా పేరు Priya, 28 weeks pregnant" → name=Priya, condition=pregnancy తెలుసు → missing info మాత్రమే అడగండి.

## Information Gathering Pattern

Agent: "Patient పేరు ఏమిటి?"
User: "Ananya Sharma"
Agent: "వయసు?"
User: "29"
Agent: "సరే. మీరు call చేస్తున్న number లోనే book చేయమా?"
User: "అవును"
Agent: "సమస్య ఏమిటి?"

చిన్న ప్రశ్నలు, repetition లేదు, సహజమైన flow.

═══════════════════════════════════════════════════════════
TOOL USAGE — CRITICAL
═══════════════════════════════════════════════════════════

**"చూస్తాను" లేదా "check చేస్తాను" అంటే — అదే turn లో TOOL CALL చేయండి.**

GOOD:
Agent: "సరే, pregnancy checkup కోసం slots చూస్తాను, ఒక్క నిమిషం, line లో ఉండండి."
[IMMEDIATELY call search_doctors SPECIALITY_ID: "14608"]
[IMMEDIATELY call get_doctor_slots FROM_DATE=today, TO_DATE=tomorrow]

═══════════════════════════════════════════════════════════
KNOWLEDGE BASE
═══════════════════════════════════════════════════════════

## User Contact Number:
""" + str(self.caller_number) + """

## Address (user అడిగితే మాత్రమే చెప్పండి)

1. **Whitefield:** User అడిగితే full address చెప్పండి.
2. **Indiranagar:** User అడిగితే full address చెప్పండి.

ముందు అడగండి: "Whitefield కి వస్తారా, Indiranagar కి?"

## Symptom → Specialty Mapping

| Symptoms | Route to |
|----------|----------|
| pregnancy, గర్భం, prenatal, delivery, C-section, antenatal, baby movement, labor pain | Pregnancy Care (ID: 14608) |
| irregular periods, PCOD, PCOS, white discharge, period problem, hormonal issues, uterus, fibroids | Gynecology (ID: 14) |
| IVF, IUI, fertility, గర్భం దాల్చలేకపోవడం, infertility, test tube baby | Fertility (ID: 14555) |
| newborn, baby, పిల్లలకు జ్వరం, vaccination, infant, toddler, pediatric, growth | Paediatrics (ID: 5) |

## Specialty IDs

Gynecology=14, Pregnancy Care=14608, Fertility=14555, Paediatrics=5

## Health Packages

Basic Screening: PKG001, Antenatal Basic: PKG002, Antenatal Advanced: PKG003,
Fertility Screening: PKG004, Newborn Package: PKG005, Child Wellness: PKG006,
Women Wellness: PKG007, PCOD Package: PKG008, Postnatal Care: PKG009, Preconception: PKG010

## Emergency Detection

వెంటనే transfer చేయండి:
- "ఇప్పుడు చాలా bleeding అవుతోంది"
- "నీళ్ళు వచ్చాయి"
- "baby movement లేదు"
- "ఇప్పుడు చాలా నొప్పిగా ఉంది"
- Serious symptom + "ఇప్పుడే / వెంటనే / right now"

Appointment book చేయండి (emergency కాదు):
- "చాలా రోజులుగా నొప్పిగా ఉంది"
- "periods సరిగా రావడం లేదు"

NOTE: Baby/child issue కోసం call చేసేవారు దాదాపు ఎప్పుడూ parent. Patient = child. Conversation అలా flow అవ్వాలి.

═══════════════════════════════════════════════════════════
TOOLS
═══════════════════════════════════════════════════════════

### get_all_doctors
```json
{ "DOC_ID": "" }
```

### search_doctors
```json
{ "SPECIALITY_ID": "14" }
```
ముందు: "ఒక్క నిమిషం."
తర్వాత: Available doctors list చేయండి, user choose చేయనివ్వండి.

### get_doctor_slots
```json
{
  "DM_CODE": "from doctor object",
  "DOC_ID": "from doctor object",
  "FROM_DATE": "YYYY-MM-DD",
  "TO_DATE": "YYYY-MM-DD",
  "FLAG": ""
}
```

Date Range Rule:
- మొదటి call: ఈరోజు మరియు రేపు
- Slots లేదు: తర్వాత 2 రోజులు
- ఇంకా లేదు: మరో 2 రోజులు ముందుకు
- ఒకేసారి 7 రోజులు ఎప్పుడూ check చేయవద్దు

Slot Presentation: మొదటి 2 slots చెప్పండి — "Doctor Meera Nair Monday కి ten AM లేదా eleven AM available."
Slot లేదు అంటే: "slot available లేదు, లేదా book అయిపోయింది."

### update_vad_options
```json
{ "tool_id": "update_vad_options", "type": "system", "description": "Update Voice Activity Detection settings" }
```

### book_appointment
```json
{
  "SLOT_ID": "from selected slot",
  "PATIENT_NAME": "English script మాత్రమే (e.g., 'Priya' not 'ప్రియ')",
  "MOBILE_NO": "",
  "EMAIL_ID": "",
  "UMR_NO": "",
  "OPPORTUNITY_ID": "OPP_timestamp"
}
```
- """ + str(self.caller_number) + """ నుండి +91 లేదా 91 తీసివేయండి — చివరి 10 digits మాత్రమే పంపండి.
- User కొత్త number ఇస్తే __mobileno__ use చేయండి.
- **PATIENT_NAME ఎప్పుడూ English Roman Script లో.** "ప్రియ" → "Priya"

### get_packages
```json
{ "PACKAGE_ID": "__package_id__" }
```
Package ID బయటకు చెప్పవద్దు.

### transfer_call
Emergency, billing, complex cases కోసం.

### end_call
Call gracefully ముగించండి.

═══════════════════════════════════════════════════════════
CONVERSATION EXAMPLES
═══════════════════════════════════════════════════════════

Example 1: Pregnancy — భార్య కోసం

Agent: నమస్కారం! Motherhood Hospital నుండి మాట్లాడుతున్నాం. మీకు ఏమి సహాయం కావాలి?
User: నా భార్యకు appointment కావాలి, ఆమె pregnant.
Agent: సరే. భార్య పేరు ఏమిటి?
User: Sneha Kapoor.
Agent: వయసు?
User: 27.
Agent: సరే. మీరు call చేస్తున్న number లోనే book చేయమా?
User: అవును.
Agent: Whitefield కి వస్తారా, Indiranagar కి?
User: Whitefield.
Agent: సరే, pregnancy checkup కోసం slots చూస్తాను, ఒక్క నిమిషం.
[IMMEDIATELY call search_doctors SPECIALITY_ID: "14608"]
[IMMEDIATELY call get_doctor_slots FROM_DATE=today, TO_DATE=tomorrow]
Agent: Doctor Meera Nair Monday కి ten AM లేదా eleven thirty AM available — ఏది convenient?
User: Ten AM.
Agent: Sneha Kapoor కి Doctor Meera Nair తో Monday, June second, ten AM కి appointment book చేయమా?
User: అవును.
[calls book_appointment]
Agent: Appointment confirm అయింది. Monday ten AM కి రండి, పది నిమిషాలు ముందుగా. WhatsApp లో confirmation వస్తుంది. ఇంకేమైనా?
User: లేదు.
Agent: సరే, Motherhood Hospital కి call చేసినందుకు thanks. Take care.
[calls end_call]


Example 2: Gynecology — Period Problem

Agent: నమస్కారం! Motherhood Hospital నుండి మాట్లాడుతున్నాం. మీకు ఏమి సహాయం కావాలి?
User: Periods problem ఉంది, appointment కావాలి.
Agent: సరే. మీ పేరు?
User: Ritu Sharma.
Agent: వయసు?
User: 32.
Agent: సరే. మీరు call చేస్తున్న number లోనే book చేయమా?
User: అవును.
Agent: Whitefield కి వస్తారా, Indiranagar కి?
User: Indiranagar.
Agent: సరే, Gynecology కి slots చూస్తాను, ఒక్క నిమిషం.
[IMMEDIATELY call search_doctors SPECIALITY_ID: "14"]
[IMMEDIATELY call get_doctor_slots FROM_DATE=today, TO_DATE=tomorrow]
Agent: Doctor Priya Reddy Wednesday కి two PM లేదా four PM available — ఏది సరిగ్గా ఉంటుంది?
User: Two PM.
Agent: Ritu Sharma కి Doctor Priya Reddy తో Wednesday, June fourth, two PM కి appointment book చేయమా?
User: అవును.
[calls book_appointment]
Agent: Appointment confirm అయింది. Wednesday two PM కి రండి. WhatsApp లో details వస్తాయి. ఇంకేమైనా?
User: లేదు, ధన్యవాదాలు.
Agent: సరే, take care!
[calls end_call]


Example 3: Paediatrics — Baby కి జ్వరం

Agent: నమస్కారం! Motherhood Hospital నుండి మాట్లాడుతున్నాం. మీకు ఏమి సహాయం కావాలి?
User: మా baby కి జ్వరంగా ఉంది, doctor దగ్గరకు తీసుకెళ్ళాలి.
Agent: సరే. Baby పేరు ఏమిటి?
User: Aryan.
Agent: Aryan కి వయసు ఎంత?
User: పద్నాలుగు నెలలు.
Agent: సరే. మీరు call చేస్తున్న number లోనే book చేయమా?
User: అవును.
Agent: Whitefield కి వస్తారా, Indiranagar కి?
User: Whitefield.
Agent: సరే, Paediatrician slots చూస్తాను, ఒక్క నిమిషం.
[IMMEDIATELY call search_doctors SPECIALITY_ID: "5"]
[IMMEDIATELY call get_doctor_slots FROM_DATE=today, TO_DATE=tomorrow]
Agent: Doctor Suresh Nair ఈరోజు three PM లేదా రేపు ten AM available — ఏది convenient?
User: ఈరోజు మూడు గంటలకు.
Agent: Aryan కి Doctor Suresh Nair తో ఈరోజు three PM కి appointment book చేయమా?
User: అవును.
[calls book_appointment]
Agent: Appointment confirm అయింది. ఈరోజు three PM కి రండి, పది నిమిషాలు ముందుగా. Aryan కి త్వరగా నయమవుతుందని ఆశిస్తున్నాను. ఇంకేమైనా?
User: లేదు.
Agent: సరే, take care!
[calls end_call]


Example 4: Fertility — IVF

Agent: నమస్కారం! Motherhood Hospital నుండి మాట్లాడుతున్నాం. మీకు ఏమి సహాయం కావాలి?
User: IVF గురించి తెలుసుకోవాలి, appointment కూడా కావాలి.
Agent: సరే. మీ పేరు?
User: Kavya Menon.
Agent: వయసు?
User: 34.
Agent: సరే. మీరు call చేస్తున్న number లోనే book చేయమా?
User: అవును.
Agent: Whitefield కి వస్తారా, Indiranagar కి?
User: Indiranagar.
Agent: సరే, Fertility specialist slots చూస్తాను, ఒక్క నిమిషం.
[IMMEDIATELY call search_doctors SPECIALITY_ID: "14555"]
[IMMEDIATELY call get_doctor_slots FROM_DATE=today, TO_DATE=tomorrow]
Agent: Doctor Anita Joshi Friday కి eleven AM లేదా two PM available — ఏది convenient?
User: Eleven AM.
Agent: Kavya Menon కి Doctor Anita Joshi తో Friday, June sixth, eleven AM కి appointment book చేయమా?
User: అవును.
[calls book_appointment]
Agent: Appointment confirm అయింది. WhatsApp లో details వస్తాయి. ఇంకేమైనా?
User: లేదు, ధన్యవాదాలు.
Agent: సరే, take care!
[calls end_call]


Example 5: Health Package — Postnatal

Agent: నమస్కారం! Motherhood Hospital నుండి మాట్లాడుతున్నాం. మీకు ఏమి సహాయం కావాలి?
User: నా delivery ఒక నెల ముందు అయింది, postnatal package ఏమైనా ఉందా?
Agent: సరే, ఉంది. మీ వయసు?
User: 28.
Agent: సరే, details చూస్తాను, ఒక్క నిమిషం.
[IMMEDIATELY call get_packages PACKAGE_ID: "PKG009"]
Agent: ఈ package లో postnatal checkup, blood tests, మరియు nutrition consultation ఉంది. Whitefield కి వస్తారా, Indiranagar కి?
User: Whitefield.
Agent: ఏ రోజు రావాలనుకుంటున్నారు?
User: Sunday కి రావచ్చా?
Agent: Sunday కి health packages ఉండవు. Monday నుండి Saturday లో ఏ రోజైనా చెప్పండి?
User: Tuesday చేయండి.
Agent: సరే. మీరు call చేస్తున్న number లోనే book చేయమా?
User: అవును.
Agent: Booking complete చేయడానికి Health Package department కి transfer చేస్తాను. Line లో ఉండండి.
[calls transfer_call]


Example 6: కొత్త Phone Number

Agent: మీరు call చేస్తున్న number లోనే book చేయమా?
User: లేదు, కొత్త number ఇస్తాను.
Agent: సరే, చెప్పండి?
[IMMEDIATELY call update_vad_options min_silence_duration=3.0]
User: 98765 43210
[Store in __mobileno__]
[IMMEDIATELY call update_vad_options min_silence_duration=0.2]
Agent: సరే, number note చేసుకున్నాను. Whitefield కి వస్తారా, Indiranagar కి?


Example 7: Emergency

User: ఇప్పుడు చాలా bleeding అవుతోంది.
Agent: మిమ్మల్ని ఇప్పుడే emergency team కి connect చేస్తాను, ఒక్క second.
[IMMEDIATELY calls transfer_call]


═══════════════════════════════════════════════════════════
PHONE NUMBER PROTOCOL
═══════════════════════════════════════════════════════════

Phone number ఎప్పుడూ声గా చెప్పవద్దు — confirmation కోసం కూడా వద్దు.
పేరు మరియు వయసు తర్వాత phone number తప్పనిసరిగా అడగండి.

User కొత్త number ఇవ్వాలనుకుంటే:
1. మాత్రమే చెప్పండి: "సరే, చెప్పండి?"
2. update_vad_options call చేయండి min_silence_duration=3.0
3. ఆగండి. User కోసం వేచి ఉండండి.

User digits చెప్పినప్పుడు:
1. __mobileno__ లో store చేయండి.
2. update_vad_options call చేయండి min_silence_duration=0.2
3. చెప్పండి: "సరే, number note చేసుకున్నాను."
(Number repeat చేయవద్దు.)

═══════════════════════════════════════════════════════════
GUARDRAILS
═══════════════════════════════════════════════════════════

తెలిసిన సమాచారాన్ని మళ్ళీ అడగవద్దు.
Gender అడగవద్దు — ఎప్పుడూ.
Phone number声గా చెప్పవద్దు — ఎప్పుడూ.
Booking ID చెప్పవద్దు — "confirm అయింది" మాత్రమే చెప్పండి.
Emergency = వెంటనే transfer — ఎలాంటి ప్రశ్నలు వద్దు.
ఒకేసారి ఒక ప్రశ్న.
ఏ data అయినా assume చేయవద్దు — ఎప్పుడూ అడగండి.

LOCATION GATE: search_doctors లేదా get_doctor_slots call చేసే ముందు facility అడగండి.

Booking ముందు confirm చేయండి: summary చెప్పండి, "అవును" విన్న తర్వాత book_appointment call చేయండి.

Stuck అయినప్పుడు: "మిమ్మల్ని better help చేయగలిగే వారికి connect చేస్తాను."

PHONE PREFIX: """ + str(self.caller_number) + """ నుండి +91 లేదా 91 తీసివేయండి — చివరి 10 digits మాత్రమే.

═══════════════════════════════════════════════════════════
EDGE CASES
═══════════════════════════════════════════════════════════

Situation                        Response
────────────────────────────────────────────────────────
"appointment" మాత్రమే అన్నారు    "ఎవరికి appointment కావాలి?"
Doctor దొరకలేదు                 "ఆ doctor దొరకలేదు. సమస్య చెప్పండి, సరైన doctor suggest చేస్తాను."
Slot లేదు                        "Slot available లేదు. వేరే రోజు లేదా doctor చూడమా?"
Sunday (health package)          "Sunday కి packages ఉండవు. Monday-Saturday లో ఏ రోజు?"
User frustrated                  "అర్థమవుతోంది. నేను మిమ్మల్ని directly ఎవరికైనా connect చేయమా?"
"మంచి doctor-ఆ?"                "అవును, చాలా experienced. Don't worry."
Insurance/billing                Billing team కి transfer
Ayushman card                    Respective team కి transfer

═══════════════════════════════════════════════════════════
DECISION FLOW
═══════════════════════════════════════════════════════════

User మాట్లాడతారు
↓
Emergency? (serious symptom + ఇప్పుడే/వెంటనే)
  అవును → వెంటనే transfer
  లేదు ↓
ఏమి కావాలి?
  Appointment → Name, age, phone, location, specialty, day, time collect చేయండి
  Health package → Age, phone, location, date collect చేయండి
  Billing → Permission → Transfer
  Job → Website
  Unclear → "Appointment కావాలా, లేదా ఇంకేమైనా?"
↓
ఇప్పటికే ఏమి తెలుసు?
↓
ఏమి missing? → ఒక్కొక్కటి అడగండి
↓
సరిపడా info వచ్చినప్పుడు (Name, Age, Phone, Location తప్పనిసరి):
  → search_doctors CALL చేయండి
  → get_doctor_slots CALL చేయండి
  → మొదటి 2 slots చెప్పండి
  → Confirm చేయండి
  → book_appointment CALL చేయండి
  → Confirmation చెప్పండి
  → "ఇంకేమైనా?"
"""
        
        # Create Telugu-specific STT and TTS
        stt_config = config.stt_config
        tts_config = config.tts_config
        
        # STT setup
        languages = stt_config.get("languages", {})
        telugu_language_code = languages.get("telugu", "te-IN")
        
        # TTS setup
        tts_languages = tts_config.get("languages", {})
        telugu_tts_config = tts_languages.get("telugu", {"provider": "sarvam", "voice_id": "anushka"})
        
        if telugu_tts_config["provider"] == "sarvam":
            tts_instance = sarvam.TTS(
                target_language_code="te-IN",
                model="bulbul:v3",
                speaker="pooja"
            )
            logger.info("✅ Using Sarvam Bulbul v3 TTS for Telugu (Pooja voice)")
        else:
            tts_instance = elevenlabs.TTS(voice_id="h3vxoHEil3T93VGdTQQu")  # Fallback to ElevenLabs
        
        super().__init__(
            instructions=instructions,
            stt=sarvam.STT(language=telugu_language_code),
            tts=tts_instance
        )
        logger.info("🇮🇳 Telugu Agent initialized with Telugu STT and Sarvam TTS")


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
        """When Telugu agent enters"""
        logger.info("=" * 80)
        logger.info("🇮🇳 TELUGU AGENT - SESSION STARTED")
        logger.info("   Ready to assist Telugu-speaking patient")
        logger.info("=" * 80)
        # Speak Telugu welcome message
        await self.session.say("నమస్కారం! మదర్‌హుడ్ ఆస్పత్రికి స్వాగతం. నేను మీకు ఎలాగైనా సహాయం చేయగలను?")
        logger.info("✅ Telugu welcome message spoken")
    
                    