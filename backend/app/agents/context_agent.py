"""
Context Awareness Agent

Assesses real-time department state and computes a context_multiplier
that scales escalation urgency based on departmental saturation.

In production this pulls from the Digital Twin (Prompt 5).
Here it works from the department_context dict in state,
which the simulator or a real feed will populate.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.agents.state import AgentOutput, TriageState

logger = logging.getLogger(__name__)


def _compute_context_multiplier(metrics: Dict[str, Any]) -> float:
    """
    Returns a value between 0.8 and 2.0.
    Higher = department is saturated → lower escalation thresholds.
    """
    multiplier = 1.0

    nurse_ratio = metrics.get("nurse_patient_ratio", 5.0)
    if nurse_ratio > 8:
        multiplier += 0.3
    elif nurse_ratio > 6:
        multiplier += 0.15

    wait_time_min = metrics.get("predicted_wait_time_min", 30)
    if wait_time_min > 90:
        multiplier += 0.2
    elif wait_time_min > 60:
        multiplier += 0.1

    available_monitored = metrics.get("available_monitored_beds", 2)
    if available_monitored == 0:
        multiplier += 0.3
    elif available_monitored <= 1:
        multiplier += 0.15

    shift_change_minutes = metrics.get("shift_change_in_minutes", 120)
    if 0 < shift_change_minutes <= 30:
        multiplier += 0.2

    surge_active = metrics.get("surge_active", False)
    if surge_active:
        multiplier += 0.3

    return round(min(max(multiplier, 0.8), 2.0), 2)


def context_analysis_agent(state: TriageState) -> TriageState:
    """
    LangGraph node — evaluates department context and emits a
    context_multiplier that the debate node uses to scale risk thresholds.
    """
    patient_id = state.get("patient_id", "unknown")
    dept_ctx   = state.get("department_context") or {}

    logger.info(f"[ContextAgent] Evaluating department context for {patient_id}")

    # Use defaults when no real department data is available
    metrics = {
        "patients_waiting":          dept_ctx.get("patients_waiting", 8),
        "patients_in_treatment":     dept_ctx.get("patients_in_treatment", 6),
        "critical_patients":         dept_ctx.get("critical_patients", 1),
        "nurse_patient_ratio":       dept_ctx.get("nurse_patient_ratio", 5.0),
        "available_monitored_beds":  dept_ctx.get("available_monitored_beds", 3),
        "available_general_beds":    dept_ctx.get("available_general_beds", 4),
        "available_icu_beds":        dept_ctx.get("available_icu_beds", 1),
        "predicted_wait_time_min":   dept_ctx.get("predicted_wait_time_min", 45),
        "shift_change_in_minutes":   dept_ctx.get("shift_change_in_minutes", 120),
        "surge_active":              dept_ctx.get("surge_active", False),
        "attending_physicians":      dept_ctx.get("attending_physicians", 2),
        "nurses_on_duty":            dept_ctx.get("nurses_on_duty", 4),
    }

    context_multiplier = _compute_context_multiplier(metrics)

    # Risk contribution from context alone
    context_risk = min((context_multiplier - 1.0) / 2.0, 0.4)

    # Findings
    load_pct = min(
        (metrics["patients_waiting"] + metrics["patients_in_treatment"]) /
        max(metrics.get("available_general_beds", 1) + metrics["patients_in_treatment"], 1) * 100,
        100,
    )
    findings = [
        f"Department load: {load_pct:.0f}% capacity",
        f"Waiting: {metrics['patients_waiting']} patients | "
        f"In treatment: {metrics['patients_in_treatment']}",
        f"Nurse-to-patient ratio: 1:{metrics['nurse_patient_ratio']:.1f}",
        f"Monitored beds available: {metrics['available_monitored_beds']}",
        f"ICU beds available: {metrics['available_icu_beds']}",
        f"Predicted wait time: {metrics['predicted_wait_time_min']} minutes",
        f"Context multiplier: {context_multiplier}×"
        + ("  HIGH LOAD" if context_multiplier > 1.4 else ""),
    ]

    if metrics["shift_change_in_minutes"] <= 30:
        findings.append(
            f" SHIFT CHANGE IN {metrics['shift_change_in_minutes']} MINUTES — "
            "heightened handoff risk"
        )

    if metrics["surge_active"]:
        findings.append(" SURGE PROTOCOL ACTIVE")

    # Recommendation
    if context_multiplier >= 1.7:
        recommendation = (
            "CRITICAL LOAD: Department at capacity — escalate this patient earlier than "
            "standard thresholds; any deterioration in waiting room may go undetected"
        )
    elif context_multiplier >= 1.3:
        recommendation = (
            "ELEVATED LOAD: Consider moving high-risk patients to monitored areas "
            "proactively; tighten reassessment intervals"
        )
    else:
        recommendation = "Normal department load — standard escalation thresholds apply"

    output = AgentOutput(
        agent_name="context",
        risk_score=context_risk,
        confidence=0.85,
        findings=findings,
        recommendation=recommendation,
        data_quality=1.0 if dept_ctx else 0.5,
        supporting_evidence={
            "metrics": metrics,
            "context_multiplier": context_multiplier,
            "load_percentage": round(load_pct, 1),
        },
        raw={"context_multiplier": context_multiplier},
    )

    return _merge(state, "context", output)


def _merge(state: TriageState, agent_name: str, output: AgentOutput) -> TriageState:
    agent_outputs = dict(state.get("agent_outputs") or {})
    agent_outputs[agent_name] = output.model_dump()
    completed = list(state.get("agents_completed") or [])
    if agent_name not in completed:
        completed.append(agent_name)
    return {**state, "agent_outputs": agent_outputs, "agents_completed": completed}
