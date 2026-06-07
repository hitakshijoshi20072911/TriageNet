"""
ED Simulation Utilities

Provides helpers for:
  - Generating synthetic FHIR bundles (for demo patients)
  - Generating synthetic department context (for demo)
  - Simple bed allocation scoring
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, date, timezone, timedelta
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# FHIR bundle generators
# ─────────────────────────────────────────────────────────────────────────────

def build_fhir_bundle(
    patient_mrn: str,
    name: str = "Jane Smith",
    age: int = 67,
    sex: str = "female",
    conditions: Optional[List[str]] = None,
    medications: Optional[List[str]] = None,
    allergies: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Build a minimal but valid FHIR R4 bundle for a demo patient.
    In production this would come from the Azure API for FHIR.
    """
    conditions  = conditions  or []
    medications = medications or []
    allergies   = allergies   or []

    birth_year = date.today().year - age
    birth_date = f"{birth_year}-06-15"

    entries = [
        # Patient resource
        {
            "resource": {
                "resourceType": "Patient",
                "id": patient_mrn,
                "name": [{"text": name}],
                "gender": sex,
                "birthDate": birth_date,
            }
        }
    ]

    # Conditions
    for condition in conditions:
        entries.append({
            "resource": {
                "resourceType": "Condition",
                "id": str(uuid.uuid4()),
                "code": {
                    "coding": [{"display": condition}],
                    "text": condition,
                },
                "clinicalStatus": {"coding": [{"code": "active"}]},
            }
        })

    # Medications
    for med in medications:
        entries.append({
            "resource": {
                "resourceType": "MedicationRequest",
                "id": str(uuid.uuid4()),
                "medicationCodeableConcept": {
                    "coding": [{"display": med}],
                    "text": med,
                },
                "status": "active",
            }
        })

    # Allergies
    for allergy in allergies:
        entries.append({
            "resource": {
                "resourceType": "AllergyIntolerance",
                "id": str(uuid.uuid4()),
                "code": {
                    "coding": [{"display": allergy}],
                    "text": allergy,
                },
                "reaction": [{"severity": "moderate"}],
            }
        })

    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


# ─────────────────────────────────────────────────────────────────────────────
# Pre-built demo patient bundles
# ─────────────────────────────────────────────────────────────────────────────

DEMO_PATIENTS = {
    # Hero scenario — deteriorating sepsis
    "P001": build_fhir_bundle(
        patient_mrn="MRN-P001",
        name="Jane Smith",
        age=67,
        sex="female",
        conditions=["Congestive heart failure", "Atrial fibrillation",
                    "Pneumonia (3 months ago)"],
        medications=["Warfarin 5mg daily", "Furosemide 40mg daily",
                     "Lisinopril 10mg daily", "Metoprolol 25mg daily"],
        allergies=["Penicillin"],
    ),
    # Medication risk scenario
    "P002": build_fhir_bundle(
        patient_mrn="MRN-P002",
        name="Robert Kumar",
        age=75,
        sex="male",
        conditions=["Chronic kidney disease stage 3", "Type 2 diabetes",
                    "Hypertension"],
        medications=["Warfarin 7.5mg daily", "Aspirin 81mg daily",
                     "Clopidogrel 75mg daily", "Metformin 500mg twice daily"],
        allergies=["Sulfa drugs", "NSAIDs"],
    ),
    # Anxiety / false alarm prevention
    "P003": build_fhir_bundle(
        patient_mrn="MRN-P003",
        name="Meera Lee",
        age=23,
        sex="female",
        conditions=["Generalised anxiety disorder", "Panic disorder"],
        medications=["Sertraline 50mg daily", "Lorazepam 0.5mg PRN"],
        allergies=[],
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Department context generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_department_context(
    department_id: str = "ED-01",
    surge: bool = False,
    shift_change_in_minutes: int = 120,
) -> Dict[str, Any]:
    """Generate a realistic department state dict for demo / testing."""
    base_patients_waiting  = random.randint(6, 15) if surge else random.randint(2, 8)
    nurses_on_duty         = random.randint(2, 4)
    patients_in_treatment  = random.randint(4, 10)

    return {
        "department_id":          department_id,
        "timestamp":              datetime.now(timezone.utc).isoformat(),
        "patients_waiting":       base_patients_waiting,
        "patients_in_treatment":  patients_in_treatment,
        "critical_patients":      random.randint(0, 2),
        "nurses_on_duty":         nurses_on_duty,
        "attending_physicians":   random.randint(1, 3),
        "nurse_patient_ratio":    round(
            patients_in_treatment / max(nurses_on_duty, 1), 1
        ),
        "available_monitored_beds": random.randint(0, 3),
        "available_general_beds":   random.randint(1, 6),
        "available_icu_beds":       random.randint(0, 1),
        "available_isolation_beds": random.randint(0, 2),
        "available_fast_track_beds": random.randint(0, 4),
        "predicted_wait_time_min":  random.randint(20, 90) if not surge else random.randint(60, 150),
        "shift_change_in_minutes":  shift_change_in_minutes,
        "surge_active":             surge,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Allocation scoring (simplified, no Monte Carlo)
# ─────────────────────────────────────────────────────────────────────────────

def simulate_allocation(
    patient_risk: float,
    bed_available: bool,
    bed_type: str = "monitored",
) -> Dict[str, Any]:
    """
    Simple (non-Monte Carlo) allocation decision.
    Returns a score and recommendation string.
    """
    base_score = patient_risk

    if not bed_available:
        # Deny bed → risk increases due to unmonitored waiting
        projected_risk = min(base_score * 1.4, 1.0)
        recommendation = "DEFER — no bed available; notify charge nurse for manual review"
    else:
        projected_risk = base_score * 0.75  # monitoring reduces effective risk
        recommendation = f"ALLOCATE — assign to {bed_type} bed"

    return {
        "input_risk":        round(patient_risk, 3),
        "projected_risk":    round(projected_risk, 3),
        "bed_type":          bed_type,
        "bed_available":     bed_available,
        "recommendation":    recommendation,
        "risk_delta":        round(projected_risk - patient_risk, 3),
    }