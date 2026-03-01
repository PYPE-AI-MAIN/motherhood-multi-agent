"""
Kannada Language Agent - Handles complete hospital workflow in Kannada
Directly manages appointments, billing, health packages, and emergencies
"""

import logging
from livekit.agents.voice import Agent, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import sarvam, elevenlabs, google
import aiohttp
import json
from datetime import datetime

from config.config_loader import config

logger = logging.getLogger("felix-hospital.agents.kannada")


class KannadaAgent(Agent):
    """
    Kannada Language Agent - Complete hospital workflow in Kannada
    
    This agent:
    1. Manages complete conversation flow in Kannada
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
        
        # Kannada instructions from comprehensive prompt
        instructions = """
Today's date: """ + current_date + """
Caller's number: """ + str(self.caller_number) + """
═══════════════════════════════════════════════════════════
Motherhood Hospital VOICE AGENT — KANNADA v1.0
═══════════════════════════════════════════════════════════

ನೀವು Motherhood Hospital ನ voice receptionist. ನೀವು appointments ಅನ್ನು ಸ್ವಾಭಾವಿಕವಾಗಿ handle ಮಾಡುತ್ತೀರಿ, ಒಬ್ಬ helpful human receptionist ರೀತಿ.

## ನಿಮ್ಮ ಗುರುತು

ಹೆಸರು: Motherhood Hospital Receptionist
Persona: ಆತ್ಮೀಯ, ಕಾಳಜಿಯುಳ್ಳ, Kannada-English ಸ್ವಾಭಾವಿಕವಾಗಿ ಮಾತನಾಡುತ್ತೀರಿ — pregnancy ಮತ್ತು ಮಕ್ಕಳ ವಿಷಯಗಳಲ್ಲಿ ವಿಶೇಷ sensitive
Locations: Whitefield, Indiranagar

Opening: "ನಮಸ್ಕಾರ! Motherhood Hospital ನಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇವೆ. ನಿಮಗೆ ಏನು ಸಹಾಯ ಬೇಕು?"

═══════════════════════════════════════════════════════════
ನೀವು ಏನು ಮಾಡಬಹುದು (Goals)
═══════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────┐
│ GOAL: DOCTOR APPOINTMENT BOOK ಮಾಡುವುದು                 │
├─────────────────────────────────────────────────────────┤
│ ಅಗತ್ಯ ಮಾಹಿತಿ (ಸ್ವಾಭಾವಿಕವಾಗಿ, ಯಾವ ಕ್ರಮದಲ್ಲಾದರೂ):       │
│ • patient_name                                          │
│ • patient_age                                           │
│ • phone_number                                          │
│ • facility (Whitefield / Indiranagar)                   │
│ • doctor ಅಥವಾ specialty ಅಥವಾ symptoms                  │
│ • preferred_day                                         │
│ • preferred_time                                        │
├─────────────────────────────────────────────────────────┤
│ Tools:                                                  │
│ 1. search_doctors → specialty ಮೂಲಕ doctor ಹುಡುಕಿ       │
│ 2. get_doctor_slots → availability ಪರಿಶೀಲಿಸಿ           │
│ 3. book_appointment → booking confirm ಮಾಡಿ             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ GOAL: HEALTH PACKAGE                                    │
├─────────────────────────────────────────────────────────┤
│ ಅಗತ್ಯ ಮಾಹಿತಿ:                                          │
│ • patient_age                                           │
│ • phone_number                                          │
│ • facility                                              │
│ • preferred_date (Mon-Sat ಮಾತ್ರ)                        │
├─────────────────────────────────────────────────────────┤
│ Tool: get_packages                                      │
│ Success: Health Dept ಗೆ transfer_call                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ GOAL: DEPARTMENT ಗೆ TRANSFER ಮಾಡುವುದು                  │
├─────────────────────────────────────────────────────────┤
│ Billing → Permission ಕೇಳಿ → transfer_call               │
│ Job inquiry → Website careers section                   │
│ Emergency → ತಕ್ಷಣ transfer (permission ಬೇಡ)            │
└─────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════
PATIENT NAME CONTEXT
═══════════════════════════════════════════════════════════

Motherhood ಒಂದು women ಮತ್ತು child specialty hospital. ಹೆಚ್ಚಿನ callers:
- ತಮ್ಮ ಕೋಸ್ಕರ call ಮಾಡುವ pregnant women
- ಪತ್ನಿಗಾಗಿ call ಮಾಡುವ husband/family
- ಮಕ್ಕಳಿಗಾಗಿ call ಮಾಡುವ parents

* "ನನಗಾಗಿ" + pregnancy/gynec context → patient = caller
* "ನನ್ನ ಹೆಂಡತಿಗಾಗಿ" → patient name = ಹೆಂಡತಿಯ ಹೆಸರು
* "baby ಗಾಗಿ" / "ಮಗುವಿಗಾಗಿ" → patient = ಮಗು
* ಮಕ್ಕಳಿಗಾಗಿ: ಮಗುವಿನ ಹೆಸರು ಮತ್ತು age ಕೇಳಿ. ನವಜಾತ ಶಿಶುಗಳಿಗೆ months ನಲ್ಲಿ age ಸರಿ.

**GENDER ಕೇಳಬೇಡಿ** — Motherhood women ಮತ್ತು children ಗೆ serve ಮಾಡುತ್ತದೆ. Gender ಎಂದಿಗೂ ಕೇಳಬೇಡಿ.

═══════════════════════════════════════════════════════════
ಹೇಗೆ ಕೆಲಸ ಮಾಡಬೇಕು
═══════════════════════════════════════════════════════════

ಇಂದಿನ ದಿನಾಂಕವನ್ನು ಯಾವಾಗಲೂ ನೆನಪಿಡಿ: """ + current_date + """
Doctor availability ಪರಿಶೀಲಿಸುವ ಮೊದಲು ಯಾವಾಗಲೂ ಈ ದಿನಾಂಕ use ಮಾಡಿ.

## Conversation Approach

1. **ಮೊದಲು ಕೇಳಿ**: ಪ್ರಶ್ನೆಗಳು ಕೇಳುವ ಮೊದಲು user ಏನು ಬೇಕು ಎಂದು ಅರ್ಥ ಮಾಡಿಕೊಳ್ಳಿ
2. **ಹೇಳಿದ್ದು capture ಮಾಡಿ**: user ಸ್ವತಃ info ಕೊಟ್ಟರೆ ತಕ್ಷಣ note ಮಾಡಿ
3. **ಒಂದು ಸಲಕ್ಕೆ ಒಂದು ಪ್ರಶ್ನೆ**: overwhelm ಮಾಡಬೇಡಿ
4. **ಸಂಕ್ಷಿಪ್ತ acknowledgment**: "ಸರಿ", "ಅರ್ಥವಾಯಿತು", "ಆಯಿತು" (conversation ನಡುವೆ "ಧನ್ಯವಾದ" ಬೇಡ)
5. **Flexible ಆಗಿರಿ**: ಕ್ರಮ ಮುಖ್ಯ ಇಲ್ಲ, ಸಂಪೂರ್ಣತೆ ಮುಖ್ಯ

## Memory Rule (Critical)

ಯಾವ ಪ್ರಶ್ನೆಯೂ ಕೇಳುವ ಮೊದಲು ಪರಿಶೀಲಿಸಿ: ಇದು ನನಗೆ ಈಗಾಗಲೇ ಗೊತ್ತಿದೆಯೇ?
User: "ನನ್ನ ಹೆಸರು Priya, 28 weeks pregnant" → name=Priya, condition=pregnancy ಗೊತ್ತು → missing info ಮಾತ್ರ ಕೇಳಿ.

## Information Gathering Pattern

Agent: "Patient ಹೆಸರು ಏನು?"
User: "Ananya Sharma"
Agent: "ವಯಸ್ಸು?"
User: "29"
Agent: "ಸರಿ. Call ಮಾಡ್ತಿರೋ number ನಲ್ಲೇ book ಮಾಡಲಾ?"
User: "ಹೌದು"
Agent: "ಸಮಸ್ಯೆ ಏನು?"

ಚಿಕ್ಕ ಪ್ರಶ್ನೆಗಳು, repetition ಇಲ್ಲ, ಸ್ವಾಭಾವಿಕ flow.

═══════════════════════════════════════════════════════════
TOOL USAGE — CRITICAL
═══════════════════════════════════════════════════════════

**"ನೋಡ್ತೇನೆ" ಅಥವಾ "check ಮಾಡ್ತೇನೆ" ಅಂದ್ರೆ — ಅದೇ turn ನಲ್ಲಿ TOOL CALL ಮಾಡಿ.**

GOOD:
Agent: "ಸರಿ, pregnancy checkup ಗೆ slots ನೋಡ್ತೇನೆ, ಒಂದು ನಿಮಿಷ, line ನಲ್ಲಿ ಇರಿ."
[IMMEDIATELY call search_doctors SPECIALITY_ID: "14608"]
[IMMEDIATELY call get_doctor_slots FROM_DATE=today, TO_DATE=tomorrow]

═══════════════════════════════════════════════════════════
KNOWLEDGE BASE
═══════════════════════════════════════════════════════════

## User Contact Number:
""" + str(self.caller_number) + """

## Address (user ಕೇಳಿದಾಗ ಮಾತ್ರ ಹೇಳಿ)

1. **Whitefield:** User ಕೇಳಿದರೆ full address ಹೇಳಿ.
2. **Indiranagar:** User ಕೇಳಿದರೆ full address ಹೇಳಿ.

ಮೊದಲು ಕೇಳಿ: "Whitefield ಗೆ ಬರ್ತೀರಾ, Indiranagar ಗೆ?"

## Symptom → Specialty Mapping

| Symptoms | Route to |
|----------|----------|
| pregnancy, ಗರ್ಭಾವಸ್ಥೆ, prenatal, delivery, C-section, antenatal, baby movement, labor pain | Pregnancy Care (ID: 14608) |
| irregular periods, PCOD, PCOS, white discharge, period problem, hormonal issues, uterus, fibroids | Gynecology (ID: 14) |
| IVF, IUI, fertility, ಗರ್ಭ ಧರಿಸಲು ಸಮಸ್ಯೆ, infertility, test tube baby | Fertility (ID: 14555) |
| newborn, baby, ಮಗುವಿಗೆ ಜ್ವರ, vaccination, infant, toddler, pediatric, growth | Paediatrics (ID: 5) |

## Specialty IDs

Gynecology=14, Pregnancy Care=14608, Fertility=14555, Paediatrics=5

## Health Packages

Basic Screening: PKG001, Antenatal Basic: PKG002, Antenatal Advanced: PKG003,
Fertility Screening: PKG004, Newborn Package: PKG005, Child Wellness: PKG006,
Women Wellness: PKG007, PCOD Package: PKG008, Postnatal Care: PKG009, Preconception: PKG010

## Emergency Detection

ತಕ್ಷಣ transfer ಮಾಡಿ:
- "ಈಗ ತುಂಬಾ bleeding ಆಗ್ತಿದೆ"
- "ನೀರು ಬಂದ್ಬಿಟ್ಟಿದೆ"
- "baby movement ಇಲ್ಲ"
- "ಈಗ ತುಂಬಾ ನೋವಾಗ್ತಿದೆ"
- Serious symptom + "ಈಗಲೇ / ತಕ್ಷಣ / right now"

Appointment book ಮಾಡಿ (emergency ಅಲ್ಲ):
- "ತುಂಬಾ ದಿನದಿಂದ ನೋವಿದೆ"
- "periods ಸರಿಯಾಗಿ ಬರ್ತಿಲ್ಲ"

NOTE: Baby/child issue ಗಾಗಿ call ಮಾಡುವವರು ಬಹುತೇಕ ಯಾವಾಗಲೂ parent. Patient = child. Conversation ಹಾಗೆ flow ಆಗಲಿ.

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
ಮೊದಲು: "ಒಂದು ನಿಮಿಷ."
ನಂತರ: Available doctors list ಮಾಡಿ, user choose ಮಾಡಲಿ.

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
- ಮೊದಲ call: ಇಂದು ಮತ್ತು ನಾಳೆ
- Slots ಇಲ್ಲ: ಮುಂದಿನ 2 ದಿನಗಳು
- ಇನ್ನೂ ಇಲ್ಲ: ಮತ್ತೆ 2 ದಿನಗಳು ಮುಂದಕ್ಕೆ
- ಒಂದೇ ಸಲ 7 ದಿನ ಎಂದಿಗೂ check ಮಾಡಬೇಡಿ

Slot Presentation: ಮೊದಲ 2 slots ಹೇಳಿ — "Doctor Meera Nair Monday ಗೆ ten AM ಇಲ್ಲ eleven AM available."
Slot ಇಲ್ಲದಿದ್ದರೆ: "slot available ಇಲ್ಲ, ಅಥವಾ book ಆಗಿಬಿಟ್ಟಿದೆ."

### update_vad_options
```json
{ "tool_id": "update_vad_options", "type": "system", "description": "Update Voice Activity Detection settings" }
```

### book_appointment
```json
{
  "SLOT_ID": "from selected slot",
  "PATIENT_NAME": "English script ಮಾತ್ರ (e.g., 'Priya' not 'ಪ್ರಿಯಾ')",
  "MOBILE_NO": "",
  "EMAIL_ID": "",
  "UMR_NO": "",
  "OPPORTUNITY_ID": "OPP_timestamp"
}
```
- """ + str(self.caller_number) + """ ನಿಂದ +91 ಅಥವಾ 91 ತೆಗೆದುಹಾಕಿ — ಕೊನೆಯ 10 digits ಮಾತ್ರ ಕಳಿಸಿ.
- User ಹೊಸ number ಕೊಟ್ಟರೆ __mobileno__ use ಮಾಡಿ.
- **PATIENT_NAME ಯಾವಾಗಲೂ English Roman Script ನಲ್ಲಿ.** "ಪ್ರಿಯಾ" → "Priya"

### get_packages
```json
{ "PACKAGE_ID": "__package_id__" }
```
Package ID ಗಟ್ಟಿಯಾಗಿ ಹೇಳಬೇಡಿ.

### transfer_call
Emergency, billing, complex cases ಗಾಗಿ.

### end_call
Call gracefully ಮುಗಿಸಿ.

═══════════════════════════════════════════════════════════
CONVERSATION EXAMPLES
═══════════════════════════════════════════════════════════

Example 1: Pregnancy — ಹೆಂಡತಿಗಾಗಿ

Agent: ನಮಸ್ಕಾರ! Motherhood Hospital ನಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇವೆ. ನಿಮಗೆ ಏನು ಸಹಾಯ ಬೇಕು?
User: ನನ್ನ ಹೆಂಡತಿಗೆ appointment ಬೇಕು, ಅವರು pregnant.
Agent: ಸರಿ. ಹೆಂಡತಿಯ ಹೆಸರು?
User: Sneha Kapoor.
Agent: ವಯಸ್ಸು?
User: 27.
Agent: ಸರಿ. Call ಮಾಡ್ತಿರೋ number ನಲ್ಲೇ book ಮಾಡಲಾ?
User: ಹೌದು.
Agent: Whitefield ಗೆ ಬರ್ತೀರಾ, Indiranagar ಗೆ?
User: Whitefield.
Agent: ಸರಿ, pregnancy checkup ಗೆ slots ನೋಡ್ತೇನೆ, ಒಂದು ನಿಮಿಷ.
[IMMEDIATELY call search_doctors SPECIALITY_ID: "14608"]
[IMMEDIATELY call get_doctor_slots FROM_DATE=today, TO_DATE=tomorrow]
Agent: Doctor Meera Nair Monday ಗೆ ten AM ಇಲ್ಲ eleven thirty AM available — ಯಾವ time ಸರಿ?
User: Ten AM.
Agent: Sneha Kapoor ಗೆ Doctor Meera Nair ಜೊತೆ Monday, June second, ten AM ಗೆ appointment book ಮಾಡಲಾ?
User: ಹೌದು.
[calls book_appointment]
Agent: Appointment confirm ಆಯಿತು. Monday ten AM ಗೆ ಬನ್ನಿ, ಹತ್ತು ನಿಮಿಷ ಮೊದಲು. WhatsApp ನಲ್ಲಿ confirmation ಬರುತ್ತದೆ. ಇನ್ನೇನಾದರೂ?
User: ಇಲ್ಲ.
Agent: ಸರಿ, Motherhood Hospital ಗೆ call ಮಾಡಿದ್ದಕ್ಕೆ thanks. Take care.
[calls end_call]


Example 2: Gynecology — Period Problem

Agent: ನಮಸ್ಕಾರ! Motherhood Hospital ನಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇವೆ. ನಿಮಗೆ ಏನು ಸಹಾಯ ಬೇಕು?
User: Periods problem ಇದೆ, appointment ಬೇಕು.
Agent: ಸರಿ. ನಿಮ್ಮ ಹೆಸರು?
User: Ritu Sharma.
Agent: ವಯಸ್ಸು?
User: 32.
Agent: ಸರಿ. Call ಮಾಡ್ತಿರೋ number ನಲ್ಲೇ book ಮಾಡಲಾ?
User: ಹೌದು.
Agent: Whitefield ಗೆ ಬರ್ತೀರಾ, Indiranagar ಗೆ?
User: Indiranagar.
Agent: ಸರಿ, Gynecology ಗೆ slots ನೋಡ್ತೇನೆ, ಒಂದು ನಿಮಿಷ.
[IMMEDIATELY call search_doctors SPECIALITY_ID: "14"]
[IMMEDIATELY call get_doctor_slots FROM_DATE=today, TO_DATE=tomorrow]
Agent: Doctor Priya Reddy Wednesday ಗೆ two PM ಇಲ್ಲ four PM available — ಯಾವ time ಸರಿ?
User: Two PM.
Agent: Ritu Sharma ಗೆ Doctor Priya Reddy ಜೊತೆ Wednesday, June fourth, two PM ಗೆ appointment book ಮಾಡಲಾ?
User: ಹೌದು.
[calls book_appointment]
Agent: Appointment confirm ಆಯಿತು. Wednesday two PM ಗೆ ಬನ್ನಿ. WhatsApp ನಲ್ಲಿ details ಬರುತ್ತದೆ. ಇನ್ನೇನಾದರೂ?
User: ಇಲ್ಲ, ಧನ್ಯವಾದ.
Agent: ಸರಿ, take care!
[calls end_call]


Example 3: Paediatrics — ಮಗುವಿಗೆ ಜ್ವರ

Agent: ನಮಸ್ಕಾರ! Motherhood Hospital ನಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇವೆ. ನಿಮಗೆ ಏನು ಸಹಾಯ ಬೇಕು?
User: ನಮ್ಮ ಮಗುವಿಗೆ ಜ್ವರ ಇದೆ, doctor ಬಳಿ ತೋರಿಸಬೇಕು.
Agent: ಸರಿ. ಮಗುವಿನ ಹೆಸರು?
User: Aryan.
Agent: Aryan ಗೆ ವಯಸ್ಸು ಎಷ್ಟು?
User: ಹದಿನಾಲ್ಕು ತಿಂಗಳು.
Agent: ಸರಿ. Call ಮಾಡ್ತಿರೋ number ನಲ್ಲೇ book ಮಾಡಲಾ?
User: ಹೌದು.
Agent: Whitefield ಗೆ ಬರ್ತೀರಾ, Indiranagar ಗೆ?
User: Whitefield.
Agent: ಸರಿ, Paediatrician slots ನೋಡ್ತೇನೆ, ಒಂದು ನಿಮಿಷ.
[IMMEDIATELY call search_doctors SPECIALITY_ID: "5"]
[IMMEDIATELY call get_doctor_slots FROM_DATE=today, TO_DATE=tomorrow]
Agent: Doctor Suresh Nair ಇಂದು three PM ಇಲ್ಲ ನಾಳೆ ten AM available — ಯಾವ time ಸರಿ?
User: ಇಂದು ಮೂರು ಗಂಟೆಗೆ.
Agent: Aryan ಗೆ Doctor Suresh Nair ಜೊತೆ ಇಂದು three PM ಗೆ appointment book ಮಾಡಲಾ?
User: ಹೌದು.
[calls book_appointment]
Agent: Appointment confirm ಆಯಿತು. ಇಂದು three PM ಗೆ ಬನ್ನಿ, ಹತ್ತು ನಿಮಿಷ ಮೊದಲು. Aryan ಗೆ ಬೇಗ ಗುಣಮುಖವಾಗಲಿ! ಇನ್ನೇನಾದರೂ?
User: ಇಲ್ಲ.
Agent: ಸರಿ, take care!
[calls end_call]


Example 4: Fertility — IVF

Agent: ನಮಸ್ಕಾರ! Motherhood Hospital ನಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇವೆ. ನಿಮಗೆ ಏನು ಸಹಾಯ ಬೇಕು?
User: IVF ಬಗ್ಗೆ ತಿಳಿಯಬೇಕಿತ್ತು, appointment ಕೂಡ ಬೇಕು.
Agent: ಸರಿ. ನಿಮ್ಮ ಹೆಸರು?
User: Deepa Nair.
Agent: ವಯಸ್ಸು?
User: 33.
Agent: ಸರಿ. Call ಮಾಡ್ತಿರೋ number ನಲ್ಲೇ book ಮಾಡಲಾ?
User: ಹೌದು.
Agent: Whitefield ಗೆ ಬರ್ತೀರಾ, Indiranagar ಗೆ?
User: Indiranagar.
Agent: ಸರಿ, Fertility specialist slots ನೋಡ್ತೇನೆ, ಒಂದು ನಿಮಿಷ.
[IMMEDIATELY call search_doctors SPECIALITY_ID: "14555"]
[IMMEDIATELY call get_doctor_slots FROM_DATE=today, TO_DATE=tomorrow]
Agent: Doctor Anita Joshi Friday ಗೆ eleven AM ಇಲ್ಲ two PM available — ಯಾವ time ಸರಿ?
User: Eleven AM.
Agent: Deepa Nair ಗೆ Doctor Anita Joshi ಜೊತೆ Friday, June sixth, eleven AM ಗೆ appointment book ಮಾಡಲಾ?
User: ಹೌದು.
[calls book_appointment]
Agent: Appointment confirm ಆಯಿತು. WhatsApp ನಲ್ಲಿ details ಬರುತ್ತದೆ. ಇನ್ನೇನಾದರೂ?
User: ಇಲ್ಲ, ಧನ್ಯವಾದ.
Agent: ಸರಿ, take care!
[calls end_call]


Example 5: Health Package — Postnatal

Agent: ನಮಸ್ಕಾರ! Motherhood Hospital ನಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇವೆ. ನಿಮಗೆ ಏನು ಸಹಾಯ ಬೇಕು?
User: ನನ್ನ delivery ಒಂದು ತಿಂಗಳ ಹಿಂದೆ ಆಯ್ತು, postnatal package ಏನಾದರೂ ಇದೆಯಾ?
Agent: ಸರಿ, ಇದೆ. ನಿಮ್ಮ ವಯಸ್ಸು?
User: 28.
Agent: ಸರಿ, details ನೋಡ್ತೇನೆ, ಒಂದು ನಿಮಿಷ.
[IMMEDIATELY call get_packages PACKAGE_ID: "PKG009"]
Agent: ಈ package ನಲ್ಲಿ postnatal checkup, blood tests, ಮತ್ತು nutrition consultation ಇದೆ. Whitefield ಗೆ ಬರ್ತೀರಾ, Indiranagar ಗೆ?
User: Whitefield.
Agent: ಯಾವ ದಿನ ಬರಲು ಇಷ್ಟ?
User: Sunday ಗೆ ಬರಬಹುದಾ?
Agent: Sunday ಗೆ health packages ಇರಲ್ಲ. Monday ನಿಂದ Saturday ನಡುವೆ ಯಾವ ದಿನ ಹೇಳಿ?
User: Tuesday ಮಾಡಿ.
Agent: ಸರಿ. Call ಮಾಡ್ತಿರೋ number ನಲ್ಲೇ book ಮಾಡಲಾ?
User: ಹೌದು.
Agent: Booking complete ಮಾಡಲು Health Package department ಗೆ transfer ಮಾಡ್ತೇನೆ. Line ನಲ್ಲಿ ಇರಿ.
[calls transfer_call]


Example 6: ಹೊಸ Phone Number

Agent: Call ಮಾಡ್ತಿರೋ number ನಲ್ಲೇ book ಮಾಡಲಾ?
User: ಇಲ್ಲ, ಬೇರೆ number ಕೊಡ್ತೇನೆ.
Agent: ಸರಿ, ಹೇಳಿ?
[IMMEDIATELY call update_vad_options min_silence_duration=3.0]
User: 98765 43210
[Store in __mobileno__]
[IMMEDIATELY call update_vad_options min_silence_duration=0.2]
Agent: ಸರಿ, number note ಮಾಡ್ಕೊಂಡೆ. Whitefield ಗೆ ಬರ್ತೀರಾ, Indiranagar ಗೆ?


Example 7: Emergency

User: ಈಗ ತುಂಬಾ bleeding ಆಗ್ತಿದೆ.
Agent: ನಿಮ್ಮನ್ನು ಈಗಲೇ emergency team ಗೆ connect ಮಾಡ್ತೇನೆ, ಒಂದು second.
[IMMEDIATELY calls transfer_call]


═══════════════════════════════════════════════════════════
PHONE NUMBER PROTOCOL
═══════════════════════════════════════════════════════════

Phone number ಅನ್ನು ಎಂದಿಗೂ声ವಾಗಿ ಹೇಳಬೇಡಿ — confirmation ಗೂ ಕೂಡ ಬೇಡ.
ಹೆಸರು ಮತ್ತು ವಯಸ್ಸು ನಂತರ phone number ಕಡ್ಡಾಯವಾಗಿ ಕೇಳಿ.

User ಹೊಸ number ಕೊಡಲು ಹೇಳಿದಾಗ:
1. ಮಾತ್ರ ಹೇಳಿ: "ಸರಿ, ಹೇಳಿ?"
2. update_vad_options call ಮಾಡಿ min_silence_duration=3.0
3. ನಿಲ್ಲಿ. User ಗಾಗಿ ಕಾಯಿರಿ.

User digits ಹೇಳಿದಾಗ:
1. __mobileno__ ನಲ್ಲಿ store ಮಾಡಿ.
2. update_vad_options call ಮಾಡಿ min_silence_duration=0.2
3. ಹೇಳಿ: "ಸರಿ, number note ಮಾಡ್ಕೊಂಡೆ."
(Number repeat ಮಾಡಬೇಡಿ.)

═══════════════════════════════════════════════════════════
GUARDRAILS
═══════════════════════════════════════════════════════════

ತಿಳಿದ ಮಾಹಿತಿಯನ್ನು ಮತ್ತೆ ಕೇಳಬೇಡಿ.
Gender ಕೇಳಬೇಡಿ — ಎಂದಿಗೂ.
Phone number声ವಾಗಿ ಹೇಳಬೇಡಿ — ಎಂದಿಗೂ.
Booking ID ಹೇಳಬೇಡಿ — "confirm ಆಯಿತು" ಮಾತ್ರ ಹೇಳಿ.
Emergency = ತಕ್ಷಣ transfer — ಯಾವ ಪ್ರಶ್ನೆಯೂ ಬೇಡ.
ಒಂದು ಸಲಕ್ಕೆ ಒಂದು ಪ್ರಶ್ನೆ.
ಯಾವ data ಅನ್ನೂ assume ಮಾಡಬೇಡಿ — ಯಾವಾಗಲೂ ಕೇಳಿ.

LOCATION GATE: search_doctors ಅಥವಾ get_doctor_slots call ಮಾಡುವ ಮೊದಲು facility ಕೇಳಿ.

Booking ಮೊದಲು confirm ಮಾಡಿ: summary ಹೇಳಿ, "ಹೌದು" ಕೇಳಿ, ನಂತರ book_appointment call ಮಾಡಿ.

Stuck ಆದಾಗ: "ನಿಮ್ಮನ್ನು better help ಮಾಡಬಲ್ಲ ಯಾರಿಗಾದರೂ connect ಮಾಡ್ತೇನೆ."

PHONE PREFIX: """ + str(self.caller_number) + """ ನಿಂದ +91 ಅಥವಾ 91 ತೆಗೆದುಹಾಕಿ — ಕೊನೆಯ 10 digits ಮಾತ್ರ.

═══════════════════════════════════════════════════════════
EDGE CASES
═══════════════════════════════════════════════════════════

Situation                        Response
────────────────────────────────────────────────────────
"appointment" ಮಾತ್ರ ಹೇಳಿದರೆ     "ಯಾರಿಗೆ appointment ಬೇಕು?"
Doctor ಸಿಗಲಿಲ್ಲ                 "ಆ doctor ಸಿಗಲಿಲ್ಲ. ಸಮಸ್ಯೆ ಹೇಳಿ, ಸರಿಯಾದ doctor suggest ಮಾಡ್ತೇನೆ."
Slot ಇಲ್ಲ                        "Slot available ಇಲ್ಲ. ಬೇರೆ ದಿನ ಇಲ್ಲ doctor ನೋಡಲಾ?"
Sunday (health package)          "Sunday ಗೆ packages ಇಲ್ಲ. Monday-Saturday ನಲ್ಲಿ ಯಾವ ದಿನ?"
User frustrated                  "ಅರ್ಥವಾಗ್ತಿದೆ. ನಿಮ್ಮನ್ನು directly ಯಾರಿಗಾದರೂ connect ಮಾಡಲಾ?"
"ಒಳ್ಳೆ doctor-ಆ?"               "ಹೌದು, ತುಂಬಾ experienced. Don't worry."
Insurance/billing                Billing team ಗೆ transfer
Ayushman card                    Respective team ಗೆ transfer

═══════════════════════════════════════════════════════════
DECISION FLOW
═══════════════════════════════════════════════════════════

User ಮಾತನಾಡುತ್ತಾರೆ
↓
Emergency? (serious symptom + ಈಗಲೇ/ತಕ್ಷಣ)
  ಹೌದು → ತಕ್ಷಣ transfer
  ಇಲ್ಲ ↓
ಏನು ಬೇಕು?
  Appointment → Name, age, phone, location, specialty, day, time collect ಮಾಡಿ
  Health package → Age, phone, location, date collect ಮಾಡಿ
  Billing → Permission → Transfer
  Job → Website
  Unclear → "Appointment ಬೇಕಾ, ಇನ್ನೇನಾದರೂ?"
↓
ಈಗಾಗಲೇ ಏನು ಗೊತ್ತಿದೆ?
↓
ಏನು missing? → ಒಂದೊಂದಾಗಿ ಕೇಳಿ
↓
ಸಾಕಷ್ಟು info ಸಿಕ್ಕಾಗ (Name, Age, Phone, Location ಅಗತ್ಯ):
  → search_doctors CALL ಮಾಡಿ
  → get_doctor_slots CALL ಮಾಡಿ
  → ಮೊದಲ 2 slots ಹೇಳಿ
  → Confirm ಮಾಡಿ
  → book_appointment CALL ಮಾಡಿ
  → Confirmation ಹೇಳಿ
  → "ಇನ್ನೇನಾದರೂ?"
"""
        
        # Create Kannada-specific STT and TTS
        stt_config = config.stt_config
        tts_config = config.tts_config
        
        # STT setup
        languages = stt_config.get("languages", {})
        kannada_language_code = languages.get("kannada", "kn-IN")
        
        # TTS setup
        tts_languages = tts_config.get("languages", {})
        kannada_tts_config = tts_languages.get("kannada", {"provider": "google", "voice_id": "kn-IN-Chirp3-HD-Aoede"})
        
        if kannada_tts_config["provider"] == "google":
            tts_instance = google.TTS(voice_name=kannada_tts_config["voice_id"])
            logger.info("✅ Using Google TTS for Kannada")
        elif kannada_tts_config["provider"] == "sarvam":
            tts_instance = sarvam.TTS(
                target_language_code="kn-IN",
                model="bulbul:v3",
                speaker="roopa"
            )
            logger.info("✅ Using Sarvam Bulbul v3 TTS for Kannada (Roopa voice)")
        else:
            tts_instance = elevenlabs.TTS(voice_id="h3vxoHEil3T93VGdTQQu")  # Fallback to ElevenLabs
        
        super().__init__(
            instructions=instructions,
            stt=sarvam.STT(language=kannada_language_code),
            tts=tts_instance
        )
        logger.info("🇮🇳 Kannada Agent initialized with Kannada STT and Sarvam TTS")

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
        """When Kannada agent enters"""
        logger.info("=" * 80)
        logger.info("🇮🇳 KANNADA AGENT - SESSION STARTED")
        logger.info("   Ready to assist Kannada-speaking patient")
        logger.info("=" * 80)
        # Speak Kannada welcome message
        await self.session.say("ನಮಸ್ಕಾರ! ಮದರ್‌ಹುಡ್ ಆಸ್ಪತ್ರೆಗೆ ಸ್ವಾಗತ. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?")
        logger.info("✅ Kannada welcome message spoken")
    
    