"""
Vitals Stream Simulator

Generates realistic, time-varying vital sign readings for demo patients.
Each patient has a "profile" that controls their physiological trajectory —
stable, gradual deterioration, sepsis pattern, etc.

Used by:
  - The WebSocket endpoint (Prompt 4) to stream live vitals to the dashboard
  - The monitoring loop to simulate real sensor data
"""
from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict

from app.agents.state import VitalReading


# ─────────────────────────────────────────────────────────────────────────────
# Patient profiles
# ─────────────────────────────────────────────────────────────────────────────

PATIENT_PROFILES: Dict[str, Dict] = {
    # Hero scenario: subtle sepsis developing over 45 minutes
    "deteriorating_sepsis": {
        "base_hr": 82, "hr_drift": +0.4,           # HR climbs
        "base_sbp": 132, "sbp_drift": -0.35,       # BP falls
        "base_dbp": 84,  "dbp_drift": -0.2,
        "base_rr": 16,   "rr_drift": +0.15,        # RR rises
        "base_spo2": 98, "spo2_drift": -0.08,      # SpO2 falls
        "base_temp": 37.1, "temp_drift": +0.04,
        "noise": 0.8,
    },
    # Stable patient — reassuring monitor readings
    "stable": {
        "base_hr": 74, "hr_drift": 0,
        "base_sbp": 118, "sbp_drift": 0,
        "base_dbp": 76,  "dbp_drift": 0,
        "base_rr": 14,   "rr_drift": 0,
        "base_spo2": 99, "spo2_drift": 0,
        "base_temp": 36.7, "temp_drift": 0,
        "noise": 1.2,
    },
    # Hypertensive patient, otherwise stable
    "hypertensive": {
        "base_hr": 80, "hr_drift": 0,
        "base_sbp": 158, "sbp_drift": +0.05,
        "base_dbp": 96,  "dbp_drift": +0.03,
        "base_rr": 15,   "rr_drift": 0,
        "base_spo2": 97, "spo2_drift": 0,
        "base_temp": 36.5, "temp_drift": 0,
        "noise": 1.5,
    },
    # Anxiety / tachycardia — should resolve after rest
    "anxiety": {
        "base_hr": 108, "hr_drift": -0.2,          # HR will settle
        "base_sbp": 128, "sbp_drift": +0.05,
        "base_dbp": 82,  "dbp_drift": +0.02,
        "base_rr": 22,   "rr_drift": -0.1,
        "base_spo2": 98, "spo2_drift": 0,
        "base_temp": 36.9, "temp_drift": 0,
        "noise": 2.0,
    },
}


def _generate_reading(profile_name: str, step: int) -> VitalReading:
    """Generate one VitalReading at time step `step` for the given profile."""
    p = PATIENT_PROFILES.get(profile_name, PATIENT_PROFILES["stable"])
    noise = p["noise"]
    rng = random.gauss

    hr   = p["base_hr"]   + p["hr_drift"]   * step + rng(0, noise * 0.5)
    sbp  = p["base_sbp"]  + p["sbp_drift"]  * step + rng(0, noise)
    dbp  = p["base_dbp"]  + p["dbp_drift"]  * step + rng(0, noise * 0.5)
    rr   = p["base_rr"]   + p["rr_drift"]   * step + rng(0, noise * 0.3)
    spo2 = p["base_spo2"] + p["spo2_drift"] * step + rng(0, noise * 0.2)
    temp = p["base_temp"]  + p["temp_drift"]  * step + rng(0, 0.05)

    # Physiological clamping
    hr   = max(30, min(hr, 200))
    sbp  = max(60, min(sbp, 240))
    dbp  = max(30, min(dbp, min(sbp - 5, 140)))
    rr   = max(4, min(rr, 45))
    spo2 = max(70, min(spo2, 100))
    temp = max(34.0, min(temp, 42.0))

    return VitalReading(
        timestamp=datetime.now(timezone.utc),
        heart_rate=round(hr, 1),
        systolic_bp=round(sbp, 1),
        diastolic_bp=round(dbp, 1),
        resp_rate=round(rr, 1),
        spO2=round(spo2, 1),
        temperature=round(temp, 2),
        consciousness="A",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Async generator — used by WebSocket endpoint
# ─────────────────────────────────────────────────────────────────────────────

async def generate_vitals(
    patient_id: str,
    profile: str = "deteriorating_sepsis",
    interval_seconds: float = 2.0,
) -> AsyncGenerator[VitalReading, None]:
    """
    Async generator that yields a new VitalReading every `interval_seconds`.

    Usage:
        async for reading in generate_vitals(patient_id):
            await ws.send_json(reading.model_dump())
    """
    step = 0
    while True:
        reading = _generate_reading(profile, step)
        yield reading
        step += 1
        await asyncio.sleep(interval_seconds)


def generate_vitals_batch(
    patient_id: str,
    profile: str = "stable",
    n: int = 10,
) -> list[VitalReading]:
    """
    Synchronous: return `n` readings in one call.
    Used when bootstrapping initial state for a newly arrived patient.
    """
    return [_generate_reading(profile, i) for i in range(n)]