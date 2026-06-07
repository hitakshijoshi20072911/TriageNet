import time
import random
from datetime import datetime, timezone, timedelta
from typing import List
from app.agents.state import VitalReading


def generate_vitals(patient_id: str):
    """Generator function that yields vital readings every 2 seconds."""
    base_hr = 72
    base_bp = 120
    base_spO2 = 98
    base_temp = 37.0

    while True:
        # Add slight random variation
        hr = base_hr + random.randint(-5, 5)
        systolic = base_bp + random.randint(-10, 10)
        diastolic = int(systolic * 0.6) + random.randint(-5, 5)
        spO2 = base_spO2 + random.randint(-2, 1)
        temp = base_temp + random.uniform(-0.3, 0.3)
        resp_rate = random.randint(16, 20)

        reading = VitalReading(
            timestamp=datetime.utcnow(),
            heart_rate=hr,
            systolic_bp=systolic,
            diastolic_bp=diastolic,
            resp_rate=resp_rate,
            spO2=spO2,
            temperature=round(temp, 1)
        )

        yield reading
        time.sleep(2)


def generate_vitals_batch(
    patient_id: str,
    profile: str = "stable",
    n: int = 5,
) -> List[VitalReading]:
    """
    Generate a batch of n vital readings with a specific clinical profile.

    Profiles:
      - stable: normal vitals with minor variation
      - deteriorating_sepsis: worsening vitals over time (HR up, BP down, SpO2 down)
      - respiratory_distress: low SpO2, high RR
    """
    vitals = []

    # Base values per profile
    if profile == "deteriorating_sepsis":
        base_hr = 85
        base_bp = 115
        base_spO2 = 96
        base_temp = 38.2
        base_rr = 22
    elif profile == "respiratory_distress":
        base_hr = 95
        base_bp = 125
        base_spO2 = 88
        base_temp = 37.0
        base_rr = 28
    else:  # stable
        base_hr = 72
        base_bp = 120
        base_spO2 = 98
        base_temp = 37.0
        base_rr = 16

    for i in range(n):
        # Add trend for deteriorating profiles
        if profile == "deteriorating_sepsis":
            hr_trend = i * 3
            bp_trend = -i * 2
            spo2_trend = -i * 0.5
        elif profile == "respiratory_distress":
            hr_trend = i * 2
            bp_trend = i
            spo2_trend = -i * 0.3
        else:
            hr_trend = 0
            bp_trend = 0
            spo2_trend = 0

        hr = base_hr + hr_trend + random.randint(-3, 3)
        systolic = base_bp + bp_trend + random.randint(-5, 5)
        diastolic = int(systolic * 0.6) + random.randint(-3, 3)
        spO2 = base_spO2 + spo2_trend + random.randint(-1, 1)
        temp = base_temp + random.uniform(-0.2, 0.2)
        resp_rate = base_rr + random.randint(-2, 2)

        # Timestamp each reading 1 minute apart
        timestamp = datetime.now(timezone.utc) - timedelta(minutes=(n - i))

        vitals.append(
            VitalReading(
                timestamp=timestamp,
                heart_rate=hr,
                systolic_bp=systolic,
                diastolic_bp=diastolic,
                resp_rate=resp_rate,
                spO2=spO2,
                temperature=round(temp, 1),
                consciousness="A",
            )
        )

    return vitals
