#!/usr/bin/env python3
"""
Test all imports in Felix Hospital project
"""

import sys
import os

# Add src to path
sys.path.insert(0, '/Users/ashishtripathy/Desktop/Proj/livekit_workflows/src')

print("=" * 80)
print("TESTING ALL IMPORTS")
print("=" * 80)

errors = []

# Test 1: Individual Tasks
print("\n📋 Testing Individual Tasks...")
try:
    from tasks.individual_tasks.data_collection_task import DataCollectionTaskAgent, PatientData
    print("  ✅ data_collection_task: DataCollectionTaskAgent, PatientData")
except Exception as e:
    print(f"  ❌ data_collection_task ERROR: {e}")
    errors.append(("data_collection_task", str(e)))

try:
    from tasks.individual_tasks.doctor_search_task import DoctorSearchTaskAgent, DoctorSearchResult
    print("  ✅ doctor_search_task: DoctorSearchTaskAgent, DoctorSearchResult")
except Exception as e:
    print(f"  ❌ doctor_search_task ERROR: {e}")
    errors.append(("doctor_search_task", str(e)))

try:
    from tasks.individual_tasks.slot_selection_task import SlotSelectionTaskAgent, SlotSelectionResult
    print("  ✅ slot_selection_task: SlotSelectionTaskAgent, SlotSelectionResult")
except Exception as e:
    print(f"  ❌ slot_selection_task ERROR: {e}")
    errors.append(("slot_selection_task", str(e)))

try:
    from tasks.individual_tasks.booking_confirmation_task import BookingConfirmationTaskAgent, BookingConfirmationResult
    print("  ✅ booking_confirmation_task: BookingConfirmationTaskAgent, BookingConfirmationResult")
except Exception as e:
    print(f"  ❌ booking_confirmation_task ERROR: {e}")
    errors.append(("booking_confirmation_task", str(e)))

# Test 2: Task Groups
print("\n📦 Testing Task Groups...")
try:
    from tasks.task_groups.appointment_booking_task_group import AppointmentBookingTaskGroup
    print("  ✅ appointment_booking_task_group: AppointmentBookingTaskGroup")
except Exception as e:
    print(f"  ❌ appointment_booking_task_group ERROR: {e}")
    errors.append(("appointment_booking_task_group", str(e)))

# Test 3: Agents
print("\n🤖 Testing Agents...")
try:
    from agents.orchestrator_agent import OrchestratorAgent
    print("  ✅ orchestrator_agent: OrchestratorAgent")
except Exception as e:
    print(f"  ❌ orchestrator_agent ERROR: {e}")
    errors.append(("orchestrator_agent", str(e)))

try:
    from agents.appointment_booking_agent import AppointmentBookingAgent
    print("  ✅ appointment_booking_agent: AppointmentBookingAgent")
except Exception as e:
    print(f"  ❌ appointment_booking_agent ERROR: {e}")
    errors.append(("appointment_booking_agent", str(e)))

try:
    from agents.emergency_agent import EmergencyAgent
    print("  ✅ emergency_agent: EmergencyAgent")
except Exception as e:
    print(f"  ❌ emergency_agent ERROR: {e}")
    errors.append(("emergency_agent", str(e)))

try:
    from agents.billing_agent import BillingAgent
    print("  ✅ billing_agent: BillingAgent")
except Exception as e:
    print(f"  ❌ billing_agent ERROR: {e}")
    errors.append(("billing_agent", str(e)))

try:
    from agents.health_package_agent import HealthPackageAgent
    print("  ✅ health_package_agent: HealthPackageAgent")
except Exception as e:
    print(f"  ❌ health_package_agent ERROR: {e}")
    errors.append(("health_package_agent", str(e)))

# Test 4: Core
print("\n🧠 Testing Core...")
try:
    from core.state import SessionState
    print("  ✅ core.state: SessionState")
except Exception as e:
    print(f"  ❌ core.state ERROR: {e}")
    errors.append(("core.state", str(e)))

try:
    from core.memory import LivingMemory
    print("  ✅ core.memory: LivingMemory")
except Exception as e:
    print(f"  ❌ core.memory ERROR: {e}")
    errors.append(("core.memory", str(e)))

# Summary
print("\n" + "=" * 80)
if errors:
    print(f"❌ FAILED: {len(errors)} import errors found")
    print("=" * 80)
    for module, error in errors:
        print(f"\n❌ {module}:")
        print(f"   {error}")
else:
    print("✅ SUCCESS: All imports working correctly!")
print("=" * 80)

sys.exit(len(errors))
