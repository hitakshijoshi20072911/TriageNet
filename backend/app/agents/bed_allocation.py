"""
Bed Allocation Agent

When the debate synthesis recommends a specific resource (monitored bed,
ICU slot, isolation room), this agent:
  1. Checks real-time availability from the digital twin / department context
  2. If a conflict exists (two patients need the same resource), runs a
     simplified Monte Carlo risk comparison to recommend the optimal allocation
  3. Returns a structured allocation decision with reasoning

This is the "resource negotiation" feature that elevates TriageNet from
a triage tool to a department orchestrator.
"""
from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Literal, Optional

from app.agents.state import TriageState

logger = logging.getLogger(__name__)

BedType = Literal["icu", "monitored", "general", "isolation", "fast_track"]


def _available_beds(dept_ctx: Dict[str, Any]) -> Dict[str, int]:
    return {
        "icu":        dept_ctx.get("available_icu_beds", 1),
        "monitored":  dept_ctx.get("available_monitored_beds", 3),
        "general":    dept_ctx.get("available_general_beds", 4),
        "isolation":  dept_ctx.get("available_isolation_beds", 1),
        "fast_track": dept_ctx.get("available_fast_track_beds", 2),
    }


def _recommend_bed_type(risk_score: float, flags: List[str]) -> BedType:
    """Recommend bed type based on risk score and clinical flags."""
    if risk_score >= 0.75:
        return "icu"
    if risk_score >= 0.55 or "EARLY_SEPSIS_PATTERN" in flags or "HYPOTENSION" in flags:
        return "monitored"
    if "ANTICOAGULATED" in flags or "IMMUNOCOMPROMISED" in flags:
        return "monitored"
    if risk_score >= 0.3:
        return "general"
    return "fast_track"


def run_allocation_monte_carlo(
    patient_risk: float,
    competing_patient_risk: Optional[float],
    bed_type: BedType,
    n: int = 50,
) -> Dict[str, Any]:
    """
    Lightweight Monte Carlo simulation — estimate the probability of adverse
    outcome if this patient is allocated vs. denied the requested bed.

    Each scenario draws a random deterioration rate and computes the
    probability of crossing a crisis threshold within 30 minutes.
    """
    random.seed(42)
    adverse_if_allocated   = 0
    adverse_if_not_allocated = 0

    for _ in range(n):
        # Deterioration rate sampled from a distribution around current risk
        detn_rate = patient_risk + random.gauss(0, 0.1)
        detn_rate = max(0.0, min(1.0, detn_rate))

        # In target bed: slower deterioration (better monitoring, faster response)
        risk_in_bed = detn_rate * random.uniform(0.5, 0.8)
        if risk_in_bed >= 0.85:
            adverse_if_allocated += 1

        # In waiting room / lower-acuity area: faster deterioration
        risk_not_in_bed = detn_rate * random.uniform(1.1, 1.6)
        if risk_not_in_bed >= 0.85:
            adverse_if_not_allocated += 1

    p_adverse_allocated     = round(adverse_if_allocated / n, 3)
    p_adverse_not_allocated = round(adverse_if_not_allocated / n, 3)

    competing_adverse = None
    if competing_patient_risk is not None:
        comp_scores = []
        for _ in range(n):
            r = competing_patient_risk + random.gauss(0, 0.08)
            r = max(0.0, min(1.0, r))
            comp_scores.append(r * random.uniform(0.9, 1.2) >= 0.85)
        competing_adverse = round(sum(comp_scores) / n, 3)

    return {
        "p_adverse_if_allocated":     p_adverse_allocated,
        "p_adverse_if_not_allocated": p_adverse_not_allocated,
        "competing_patient_adverse":  competing_adverse,
        "recommendation": "ALLOCATE" if p_adverse_not_allocated > p_adverse_allocated else "DEFER",
        "risk_delta": round(p_adverse_not_allocated - p_adverse_allocated, 3),
        "simulations": n,
    }


def bed_allocation_agent(state: TriageState) -> TriageState:
    """
    LangGraph node — determines optimal bed allocation for the patient.
    Runs Monte Carlo conflict resolution if the required bed type is scarce.
    """
    patient_id = state.get("patient_id", "unknown")
    synthesis  = state.get("synthesis_result") or {}
    dept_ctx   = state.get("department_context") or {}

    logger.info(f"[BedAllocationAgent] Processing allocation for {patient_id}")

    # Pull risk data from synthesis if available, else from vitals agent
    agent_outputs = state.get("agent_outputs") or {}
    vitals_out  = agent_outputs.get("vitals", {})
    history_out = agent_outputs.get("history", {})

    risk_score = synthesis.get("consensus_risk_score",
                 vitals_out.get("risk_score", 0.3))
    all_flags  = (vitals_out.get("flags", []) + history_out.get("flags", []))

    # Determine what this patient needs
    required_bed = _recommend_bed_type(risk_score, all_flags)
    available    = _available_beds(dept_ctx)
    beds_of_type = available.get(required_bed, 0)

    # Check for conflict (scarcity)
    conflict = beds_of_type == 0
    simulation_result = None
    allocation_decision = "ALLOCATE"
    conflict_detail = None

    if conflict:
        # Run simulation: what's the cost of NOT allocating?
        simulation_result = run_allocation_monte_carlo(
            patient_risk=risk_score,
            competing_patient_risk=None,  # would be populated from digital twin
            bed_type=required_bed,
        )
        allocation_decision = simulation_result["recommendation"]
        conflict_detail = (
            f"No {required_bed} beds available. "
            f"P(adverse if denied) = {simulation_result['p_adverse_if_not_allocated']:.1%}. "
            f"Monte Carlo recommendation: {allocation_decision}."
        )
        logger.warning(f"[BedAllocationAgent] CONFLICT: {conflict_detail}")

    findings = [
        f"Required bed type: {required_bed.upper()} (based on risk score {risk_score:.2f})",
        f"Available {required_bed} beds: {beds_of_type}",
        f"Allocation decision: {allocation_decision}",
    ]
    if conflict_detail:
        findings.append(f"⚠️ Conflict: {conflict_detail}")
    if all_flags:
        findings.append(f"Clinical flags driving allocation: {', '.join(set(all_flags))}")

    result = {
        "required_bed_type": required_bed,
        "allocation_decision": allocation_decision,
        "conflict": conflict,
        "beds_available": beds_of_type,
        "simulation": simulation_result,
        "findings": findings,
        "flags_considered": list(set(all_flags)),
    }

    agent_outputs = dict(state.get("agent_outputs") or {})
    agent_outputs["bed_allocation"] = result

    completed = list(state.get("agents_completed") or [])
    if "bed_allocation" not in completed:
        completed.append("bed_allocation")

    return {**state, "agent_outputs": agent_outputs, "agents_completed": completed}