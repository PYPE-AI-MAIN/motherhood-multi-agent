"""
Symptom to Specialty Mapping
Maps patient symptoms to medical specialties
"""

SYMPTOM_TO_SPECIALTY = {
    # Cardiology
    "chest pain": "14",
    "दिल": "14",
    "heart": "14",
    "सीने में दर्द": "14",
    "cardiac": "14",
    "cardiology": "14",
    "cardiologist": "14",
    
    # Orthopedics
    "joint pain": "14608",
    "घुटना": "14608",
    "back pain": "14608",
    "पीठ दर्द": "14608",
    "fracture": "14608",
    "bone": "14608",
    "knee": "14608",
    
    # General Medicine
    "fever": "14555",
    "बुखार": "14555",
    "cough": "14555",
    "खांसी": "14555",
    "cold": "14555",
    "vomiting": "14555",
    "उल्टी": "14555",
    "headache": "14555",
    "सिर दर्द": "14555",
    "weakness": "14555",
    "कमजोरी": "14555",
}

SPECIALTY_NAMES = {
    "14": "Cardiology",
    "14608": "Orthopedics",
    "14555": "General Medicine"
}


def map_symptom_to_specialty(symptom: str) -> tuple[str, str]:
    """
    Map patient symptom description to specialty ID

    Args:
        symptom: Patient's symptom description

    Returns:
        Tuple of (specialty_name, specialty_id)
    """
    symptom_lower = symptom.lower()

    for keyword, specialty_id in SYMPTOM_TO_SPECIALTY.items():
        if keyword in symptom_lower:
            specialty_name = SPECIALTY_NAMES.get(specialty_id, "General Medicine")
            return specialty_name, specialty_id

    # Default to General Medicine
    return "General Medicine", "14555"
