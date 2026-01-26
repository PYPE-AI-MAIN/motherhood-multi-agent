"""
Mock Felix Hospital API
Provides sample doctors, slots, and booking functionality for testing
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json


# Mock Doctors Database
MOCK_DOCTORS = [
    {
        "doctor_id": "DOC001",
        "name": "Dr. Rajesh Sharma",
        "specialty": "Cardiology",
        "specialty_id": "14",
        "facility": "Noida",
        "experience_years": 15
    },
    {
        "doctor_id": "DOC002",
        "name": "Dr. Priya Verma",
        "specialty": "Orthopedics",
        "specialty_id": "14608",
        "facility": "Noida",
        "experience_years": 12
    },
    {
        "doctor_id": "DOC003",
        "name": "Dr. Amit Kumar",
        "specialty": "General Medicine",
        "specialty_id": "14555",
        "facility": "Noida",
        "experience_years": 10
    },
    {
        "doctor_id": "DOC004",
        "name": "Dr. Sunita Singh",
        "specialty": "Cardiology",
        "specialty_id": "14",
        "facility": "Greater Noida",
        "experience_years": 18
    },
    {
        "doctor_id": "DOC005",
        "name": "Dr. Vinay Gupta",
        "specialty": "Orthopedics",
        "specialty_id": "14608",
        "facility": "Greater Noida",
        "experience_years": 14
    }
]

# Store bookings in memory (in real app, this would be database)
MOCK_BOOKINGS = {}


class FelixHospitalMockAPI:
    """Mock implementation of Felix Hospital API"""
    
    def __init__(self):
        self.doctors = MOCK_DOCTORS
        self.bookings = MOCK_BOOKINGS
    
    async def search_doctors(
        self,
        location: Optional[str] = None,
        specialty_name: Optional[str] = None,
        speciality_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for doctors by specialty and optionally by facility

        Args:
            location: Optional facility filter ("Noida" or "Greater Noida")
            specialty_name: Specialty name (e.g., "Cardiology")
            speciality_id: Specialty ID (e.g., "14" for Cardiology)

        Returns:
            List of matching doctors
        """
        results = self.doctors.copy()

        # Filter by specialty_id if provided
        if speciality_id:
            results = [d for d in results if d["specialty_id"] == speciality_id]
        # Otherwise filter by specialty name
        elif specialty_name:
            results = [d for d in results if d["specialty"].lower() == specialty_name.lower()]

        # Filter by location/facility
        if location:
            results = [d for d in results if d["facility"].lower() == location.lower()]

        return results
    
    async def get_doctor_slots(
        self, 
        doctor_id: str, 
        from_date: str, 
        to_date: str
    ) -> List[Dict]:
        """
        Get available slots for a doctor between dates
        
        Args:
            doctor_id: Doctor ID
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
        
        Returns:
            List of available slots
        """
        # Parse dates
        start = datetime.strptime(from_date, "%Y-%m-%d")
        end = datetime.strptime(to_date, "%Y-%m-%d")
        
        # Generate slots
        slots = []
        current_date = start
        
        while current_date <= end:
            # Skip Sundays
            if current_date.weekday() != 6:
                # Morning slots: 9 AM - 12 PM
                for hour in [9, 10, 11, 12]:
                    for minute in [0, 30]:
                        slot_time = current_date.replace(hour=hour, minute=minute)
                        slot_id = f"SLOT_{doctor_id}_{slot_time.strftime('%Y%m%d_%H%M')}"
                        
                        # Check if slot is already booked
                        if slot_id not in self.bookings:
                            slots.append({
                                "slot_id": slot_id,
                                "doctor_id": doctor_id,
                                "date": current_date.strftime("%Y-%m-%d"),
                                "time": slot_time.strftime("%I:%M %p"),
                                "day_of_week": current_date.strftime("%A"),
                                "available": True
                            })
                
                # Afternoon slots: 2 PM - 5 PM
                for hour in [14, 15, 16, 17]:
                    for minute in [0, 30]:
                        slot_time = current_date.replace(hour=hour, minute=minute)
                        slot_id = f"SLOT_{doctor_id}_{slot_time.strftime('%Y%m%d_%H%M')}"
                        
                        if slot_id not in self.bookings:
                            slots.append({
                                "slot_id": slot_id,
                                "doctor_id": doctor_id,
                                "date": current_date.strftime("%Y-%m-%d"),
                                "time": slot_time.strftime("%I:%M %p"),
                                "day_of_week": current_date.strftime("%A"),
                                "available": True
                            })
            
            current_date += timedelta(days=1)
        
        return slots
    
    async def book_appointment(
        self,
        slot_id: str,
        patient_name: str,
        patient_age: int,
        gender: str,
        phone: str,
        doctor_id: str
    ) -> Dict:
        """
        Book an appointment
        
        Returns:
            Booking confirmation with booking_id
        """
        booking_id = f"BOOK_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        booking_data = {
            "booking_id": booking_id,
            "slot_id": slot_id,
            "patient_name": patient_name,
            "patient_age": patient_age,
            "gender": gender,
            "phone": phone,
            "doctor_id": doctor_id,
            "status": "confirmed",
            "created_at": datetime.now().isoformat()
        }
        
        # Store booking
        self.bookings[slot_id] = booking_data
        
        return booking_data
    
    async def get_all_doctors(self) -> List[Dict]:
        """Get all doctors"""
        return self.doctors


# Global instance
felix_api = FelixHospitalMockAPI()
