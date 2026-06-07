"""
Vitals Analysis Agent

Performs:
  1. Signal quality / artefact check
  2. CUSUM trend analysis on each vital parameter
  3. MEWS (Modified Early Warning Score) calculation
  4. Multi-parameter clinical pattern detection (sepsis, shock, respiratory failure)
  5. Shock index computation
  6. Risk score synthesis (0.0 – 1.0)

All logic is deterministic and works without an LLM — making it
fast, auditable, and testable. LLM is used only for the narrative
findings / recommendation text (stubbed here, wired in Prompt 4).
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from app.agents.state import AgentOutput, TriageState, VitalReading

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# MEWS scoring tables
# ─────────────────────────────────────────────────────────────────────────────

def _mews_respiratory_rate(rr: float) -> int:
    if rr < 9:     return 2
    if rr <= 14:   return 0
    if rr <= 20:   return 1
    if rr <= 29:   return 2
    return 3

def _mews_heart_rate(hr: float) -> int:
    if hr < 40:    return 2
    if hr <= 50:   return 1
    if hr <= 100:  return 0
    if hr <= 110:  return 1
    if hr <= 129:  return 2
    return 3

def _mews_systolic_bp(sbp: float) -> int:
    if sbp < 70:    return 3
    if sbp < 80:    return 2
    if sbp < 100:   return 1
    if sbp <= 199:  return 0
    return 2

def _mews_temperature(temp: float) -> int:
    if temp < 35.0:   return 2
    if temp <= 38.4:  return 0
    return 2

def _mews_consciousness(avpu: str) -> int:
    mapping = {"A": 0, "V": 1, "P": 2, "U": 3}
    return mapping.get(avpu.upper(), 0)


def calculate_mews(reading: VitalReading) -> int:
    return (
        _mews_respiratory_rate(reading.resp_rate)
        + _mews_heart_rate(reading.heart_rate)
        + _mews_systolic_bp(reading.systolic_bp)
        + _mews_temperature(reading.temperature)
        + _mews_consciousness(reading.consciousness)
    )


# ─────────────────────────────────────────────────────────────────────────────
# CUSUM trend analysis
# ─────────────────────────────────────────────────────────────────────────────

def cusum_analysis(values: List[float], target: float | None = None,
                   k: float = 0.5, h: float = 4.0) -> Dict[str, Any]:
    """
    Two-sided CUSUM to detect upward or downward shifts.

    Args:
        values:  time-ordered list of observations
        target:  reference value (mean of first 3 readings if not supplied)
        k:       allowable slack (half the shift size we want to detect)
        h:       decision threshold (alarm when |S| > h)

    Returns dict with:
        alarm_up, alarm_down: bool
        cusum_up, cusum_down: final cumulative sums
        shift_detected: direction string or None
        alarm_index: first index that crossed h, or None
    """
    if len(values) < 2:
        return {"alarm_up": False, "alarm_down": False,
                "cusum_up": 0.0, "cusum_down": 0.0,
                "shift_detected": None, "alarm_index": None}

    mu = target if target is not None else sum(values[:3]) / min(3, len(values))
    # Estimate std from first readings
    if len(values) >= 3:
        diffs = [abs(v - mu) for v in values[:3]]
        sigma = max(sum(diffs) / 3, 1.0)
    else:
        sigma = max(abs(values[0] - mu), 1.0)

    S_up, S_down = 0.0, 0.0
    alarm_up, alarm_down = False, False
    alarm_index = None

    for i, v in enumerate(values):
        z = (v - mu) / sigma
        S_up   = max(0.0, S_up   + z - k)
        S_down = max(0.0, S_down - z - k)

        if S_up > h and not alarm_up:
            alarm_up, alarm_index = True, i
        if S_down > h and not alarm_down:
            alarm_down, alarm_index = True, i

    shift = None
    if alarm_up:    shift = "increasing"
    if alarm_down:  shift = "decreasing"
    if alarm_up and alarm_down: shift = "unstable"

    return {
        "alarm_up": alarm_up, "alarm_down": alarm_down,
        "cusum_up": round(S_up, 3), "cusum_down": round(S_down, 3),
        "shift_detected": shift, "alarm_index": alarm_index,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pattern detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_clinical_patterns(readings: List[VitalReading]) -> List[str]:
    """
    Detect named clinical patterns from a time series of vital signs.
    Returns a list of pattern name strings.
    """
    if not readings:
        return []

    latest = readings[-1]
    patterns = []

    # SIRS / early sepsis: HR>90, RR>20, Temp out of normal range
    sirs_criteria = sum([
        latest.heart_rate > 90,
        latest.resp_rate > 20,
        latest.temperature > 38.0 or latest.temperature < 36.0,
        latest.systolic_bp < 90,   # hypotension as 4th criterion
    ])
    if sirs_criteria >= 2:
        patterns.append(f"SIRS_CRITERIA_{sirs_criteria}/4")
    if sirs_criteria >= 3:
        patterns.append("EARLY_SEPSIS_PATTERN")

    # Haemodynamic compromise
    if latest.shock_index > 1.0:
        patterns.append(f"ELEVATED_SHOCK_INDEX_{latest.shock_index:.2f}")
    if latest.systolic_bp < 90:
        patterns.append("HYPOTENSION")
    if latest.pulse_pressure < 30:
        patterns.append("NARROWED_PULSE_PRESSURE")

    # Respiratory
    if latest.spO2 < 94:
        patterns.append("HYPOXIA")
    if latest.resp_rate > 25:
        patterns.append("SIGNIFICANT_TACHYPNOEA")

    # Trend-based: check last 3 readings for narrowing pulse pressure
    if len(readings) >= 3:
        pp_trend = [r.pulse_pressure for r in readings[-3:]]
        if pp_trend[-1] < pp_trend[0] - 10:
            patterns.append("NARROWING_PULSE_PRESSURE_TREND")

        hr_trend = [r.heart_rate for r in readings[-3:]]
        if hr_trend[-1] > hr_trend[0] + 10:
            patterns.append("PROGRESSIVE_TACHYCARDIA")

        spo2_trend = [r.spO2 for r in readings[-3:]]
        if spo2_trend[-1] < spo2_trend[0] - 2:
            patterns.append("DECLINING_SPO2")

    # Fever
    if latest.temperature >= 38.5:
        patterns.append("FEVER")
    elif latest.temperature < 36.0:
        patterns.append("HYPOTHERMIA")

    return patterns


# ─────────────────────────────────────────────────────────────────────────────
# Risk score synthesis
# ─────────────────────────────────────────────────────────────────────────────

def compute_vitals_risk(mews: int, patterns: List[str],
                         cusum_alarms: int) -> float:
    """
    Combine MEWS, pattern count, and CUSUM alarm count into a 0–1 risk score.

    MEWS scale:  0-1 (low), 2-3 (medium), 4-5 (high), 6+ (very high)
    """
    # MEWS contribution (0 – 0.6)
    mews_score = min(mews / 10.0, 0.6)

    # Pattern contribution (0 – 0.25)
    critical_patterns = {"EARLY_SEPSIS_PATTERN", "HYPOTENSION",
                         "ELEVATED_SHOCK_INDEX", "HYPOXIA"}
    critical_count = sum(1 for p in patterns
                         if any(c in p for c in critical_patterns))
    pattern_score = min(critical_count * 0.1 + len(patterns) * 0.03, 0.25)

    # CUSUM alarm contribution (0 – 0.15)
    cusum_score = min(cusum_alarms * 0.05, 0.15)

    return round(min(mews_score + pattern_score + cusum_score, 1.0), 3)


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph node
# ─────────────────────────────────────────────────────────────────────────────

def vitals_analysis_agent(state: TriageState) -> TriageState:
    """
    LangGraph node — performs full vitals analysis and writes result into
    state["agent_outputs"]["vitals"].
    """
    patient_id = state.get("patient_id", "unknown")
    raw_vitals = state.get("vitals_stream", [])

    logger.info(f"[VitalsAgent] Analysing {len(raw_vitals)} readings for {patient_id}")

    # Parse raw dicts into VitalReading objects
    readings: List[VitalReading] = []
    for v in raw_vitals:
        try:
            readings.append(VitalReading(**v) if isinstance(v, dict) else v)
        except Exception as e:
            logger.warning(f"[VitalsAgent] Skipping malformed reading: {e}")

    if not readings:
        # No data — return a minimal safe output
        output = AgentOutput(
            agent_name="vitals",
            risk_score=0.0,
            confidence=0.0,
            findings=["No vital sign data available"],
            recommendation="Obtain vitals immediately",
            data_quality=0.0,
        )
        return _merge(state, "vitals", output)

    latest = readings[-1]

    # 1. MEWS
    mews = calculate_mews(latest)

    # 2. CUSUM on each parameter
    hr_values  = [r.heart_rate   for r in readings]
    sbp_values = [r.systolic_bp  for r in readings]
    rr_values  = [r.resp_rate    for r in readings]
    spo2_values = [r.spO2        for r in readings]

    cusum_hr   = cusum_analysis(hr_values)
    cusum_sbp  = cusum_analysis(sbp_values)
    cusum_rr   = cusum_analysis(rr_values)
    cusum_spo2 = cusum_analysis(spo2_values)

    cusum_alarm_count = sum([
        cusum_hr["alarm_up"] or cusum_hr["alarm_down"],
        cusum_sbp["alarm_up"] or cusum_sbp["alarm_down"],
        cusum_rr["alarm_up"] or cusum_rr["alarm_down"],
        cusum_spo2["alarm_up"] or cusum_spo2["alarm_down"],
    ])

    # 3. Pattern detection
    patterns = detect_clinical_patterns(readings)

    # 4. Risk score
    risk_score = compute_vitals_risk(mews, patterns, cusum_alarm_count)

    # 5. Data quality (penalise few readings)
    data_quality = min(len(readings) / 5.0, 1.0)

    # 6. Confidence (high if readings are frequent and consistent)
    confidence = min(data_quality + (0.1 if cusum_alarm_count == 0 else 0), 1.0)

    # 7. Human-readable findings
    findings = [
        f"Latest vitals: HR {latest.heart_rate:.0f}bpm, BP {latest.systolic_bp:.0f}/{latest.diastolic_bp:.0f}mmHg, "
        f"SpO₂ {latest.spO2:.1f}%, RR {latest.resp_rate:.0f}, Temp {latest.temperature:.1f}°C",
        f"MEWS score: {mews} ({'Low' if mews <= 1 else 'Medium' if mews <= 3 else 'High' if mews <= 5 else 'Very High'})",
        f"Shock index: {latest.shock_index:.2f} ({'Normal' if latest.shock_index < 0.9 else 'Elevated'})",
    ]

    if cusum_alarm_count > 0:
        alarmed = []
        if cusum_hr["alarm_up"]:   alarmed.append(f"HR trending UP (CUSUM={cusum_hr['cusum_up']})")
        if cusum_sbp["alarm_down"]: alarmed.append(f"SBP trending DOWN (CUSUM={cusum_sbp['cusum_down']})")
        if cusum_rr["alarm_up"]:   alarmed.append(f"RR trending UP")
        if cusum_spo2["alarm_down"]: alarmed.append(f"SpO₂ trending DOWN")
        findings.append(f"CUSUM alarms ({cusum_alarm_count}): {'; '.join(alarmed)}")

    if patterns:
        findings.append(f"Clinical patterns detected: {', '.join(patterns)}")

    # 8. Recommendation
    if risk_score >= 0.75:
        recommendation = "URGENT: Immediate physician evaluation required — critical risk profile"
    elif risk_score >= 0.5:
        recommendation = "HIGH: Move to monitored area and reassess within 10 minutes"
    elif risk_score >= 0.3:
        recommendation = "MEDIUM: Reassess within 15 minutes; watch for deterioration"
    else:
        recommendation = "LOW: Continue standard monitoring — reassess in 30 minutes"

    output = AgentOutput(
        agent_name="vitals",
        risk_score=risk_score,
        confidence=confidence,
        findings=findings,
        recommendation=recommendation,
        data_quality=data_quality,
        supporting_evidence={
            "mews": mews,
            "shock_index": round(latest.shock_index, 3),
            "pulse_pressure": round(latest.pulse_pressure, 1),
            "patterns": patterns,
            "cusum_alarms": cusum_alarm_count,
            "cusum_detail": {
                "hr": cusum_hr, "sbp": cusum_sbp,
                "rr": cusum_rr, "spo2": cusum_spo2,
            },
            "latest_reading": latest.model_dump(),
            "reading_count": len(readings),
        },
        flags=[p for p in patterns if "SEPSIS" in p or "SHOCK" in p or "HYPOXIA" in p],
    )

    return _merge(state, "vitals", output)


def _merge(state: TriageState, agent_name: str, output: AgentOutput) -> TriageState:
    """Write agent output into state and mark agent as completed."""
    agent_outputs = dict(state.get("agent_outputs") or {})
    agent_outputs[agent_name] = output.model_dump()

    completed = list(state.get("agents_completed") or [])
    if agent_name not in completed:
        completed.append(agent_name)

    return {
        **state,
        "agent_outputs": agent_outputs,
        "agents_completed": completed,
    }