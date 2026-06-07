"""
Debate Synthesis Node

Implements the 3-round structured debate protocol:

  Round 1 — Individual agent presentations
  Round 2 — Cross-examination and conflict detection
  Round 3 — Weighted reconciliation → consensus risk score → ESI level

The debate node is where TriageNet's multi-agent architecture produces
its most visible output: a single, transparent, evidence-backed recommendation
that a nurse can confirm or override in under 30 seconds.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.agents.state import SynthesisOutput, TriageState

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ESI level mapping
# ─────────────────────────────────────────────────────────────────────────────

def _determine_esi(risk: float, has_critical_flags: bool) -> int:
    """
    Map consensus risk score to Emergency Severity Index level (1–5).
    ESI 1 = resuscitation; ESI 5 = non-urgent.
    """
    if has_critical_flags and risk >= 0.6:
        return 1
    if risk >= 0.75:
        return 1
    if risk >= 0.55:
        return 2
    if risk >= 0.35:
        return 3
    if risk >= 0.15:
        return 4
    return 5


def _esi_label(esi: int) -> str:
    return {
        1: "RESUSCITATION — Immediate life-saving intervention",
        2: "EMERGENT — High risk of deterioration",
        3: "URGENT — Stable but requires treatment",
        4: "LESS URGENT — Could wait 1–2 hours",
        5: "NON-URGENT — Routine care",
    }.get(esi, "UNKNOWN")


def _reassessment_seconds(esi: int, context_multiplier: float) -> int:
    """Compute reassessment interval, shortened if department is saturated."""
    base = {1: 0, 2: 300, 3: 900, 4: 1800, 5: 3600}[esi]
    # Multiplier above 1.3 tightens the interval
    if context_multiplier >= 1.3:
        base = int(base * 0.6)
    return max(base, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Debate rounds
# ─────────────────────────────────────────────────────────────────────────────

def _round1_presentations(agent_outputs: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """Collect each agent's position for the debate transcript."""
    positions = []
    for agent_name in ["vitals", "history", "context"]:
        out = agent_outputs.get(agent_name, {})
        positions.append({
            "agent": agent_name,
            "risk_score": out.get("risk_score", 0.0),
            "confidence": out.get("confidence", 0.5),
            "data_quality": out.get("data_quality", 1.0),
            "key_finding": out.get("findings", ["No finding"])[0],
            "recommendation": out.get("recommendation", ""),
            "flags": out.get("flags", []),
        })
    return positions


def _round2_conflicts(positions: List[Dict[str, Any]]) -> List[str]:
    """
    Detect conflicts between agents.
    A conflict is when risk scores differ by > 0.25, or when one agent
    flags a critical condition that another ignores.
    """
    conflicts = []
    scores = {p["agent"]: p["risk_score"] for p in positions}

    vitals_risk  = scores.get("vitals", 0)
    history_risk = scores.get("history", 0)
    context_risk = scores.get("context", 0)

    if abs(vitals_risk - history_risk) > 0.25:
        conflicts.append(
            f"Vitals risk ({vitals_risk:.2f}) diverges from history risk ({history_risk:.2f}) "
            f"by {abs(vitals_risk - history_risk):.2f} — possible baseline elevation"
        )

    # History flags critical condition but vitals appear stable
    history_flags = next((p["flags"] for p in positions if p["agent"] == "history"), [])
    critical_flags = {"ANTICOAGULATED", "IMMUNOCOMPROMISED", "CONGESTIVE_HEART_FAILURE"}
    has_critical_history = bool(critical_flags.intersection(set(history_flags)))

    if has_critical_history and vitals_risk < 0.3:
        conflicts.append(
            "History flags high-risk condition(s) but vitals appear stable — "
            "borderline vitals carry greater significance in this patient"
        )

    # Very high context multiplier with low patient risk
    context_mult = next(
        (p.get("raw", {}).get("context_multiplier", 1.0)
         for p in positions if p["agent"] == "context"), 1.0
    )
    if context_mult >= 1.5 and max(vitals_risk, history_risk) < 0.35:
        conflicts.append(
            f"Department load is critically high (multiplier {context_mult}×) — "
            "even moderate-risk patients should be escalated earlier"
        )

    return conflicts


def _round3_consensus(
    positions: List[Dict[str, Any]],
    conflicts: List[str],
) -> Tuple[float, float, float]:
    """
    Compute confidence-weighted consensus risk score.
    Returns (consensus_risk, effective_confidence, context_multiplier).
    """
    context_mult = 1.0
    for p in positions:
        if p["agent"] == "context":
            context_mult = p.get("raw", {}).get("context_multiplier",
                           p.get("risk_score", 0) * 2 + 1.0)

    # Adaptive weights: agent confidence × data quality
    weighted_sum = 0.0
    weight_total = 0.0
    for p in positions:
        if p["agent"] == "context":
            # Context contributes less to clinical risk score
            w = p["confidence"] * p["data_quality"] * 0.3
        else:
            w = p["confidence"] * p["data_quality"]
        weighted_sum += p["risk_score"] * w
        weight_total += w

    base_risk = weighted_sum / max(weight_total, 0.001)

    # Conflict resolution: conflicts boost the risk score conservatively
    conflict_boost = min(len(conflicts) * 0.05, 0.15)
    consensus_risk = min(base_risk + conflict_boost, 1.0)

    # Apply context multiplier (capped to avoid over-escalation)
    effective_risk = min(consensus_risk * min(context_mult, 1.5), 1.0)

    # Overall confidence = mean of agent confidences, penalised for conflicts
    mean_confidence = sum(p["confidence"] for p in positions) / len(positions)
    effective_confidence = max(mean_confidence - len(conflicts) * 0.05, 0.1)

    return round(effective_risk, 3), round(effective_confidence, 3), context_mult


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph node
# ─────────────────────────────────────────────────────────────────────────────

def debate_synthesis_node(state: TriageState) -> TriageState:
    """
    LangGraph node — runs the 3-round structured debate and produces
    a SynthesisOutput stored in state["synthesis_result"].
    """
    patient_id    = state.get("patient_id", "unknown")
    agent_outputs = state.get("agent_outputs") or {}

    logger.info(f"[DebateNode] Starting synthesis for {patient_id}")

    # ── Round 1: Presentations ─────────────────────────────────────────────
    positions = _round1_presentations(agent_outputs)
    logger.info(f"[DebateNode] R1 scores: "
                + " | ".join(f"{p['agent']}={p['risk_score']:.2f}" for p in positions))

    # ── Round 2: Conflict detection ────────────────────────────────────────
    conflicts = _round2_conflicts(positions)
    if conflicts:
        logger.warning(f"[DebateNode] R2 conflicts: {conflicts}")

    # ── Round 3: Consensus ─────────────────────────────────────────────────
    consensus_risk, confidence, context_mult = _round3_consensus(positions, conflicts)
    logger.info(f"[DebateNode] R3 consensus risk={consensus_risk} conf={confidence}")

    # Collect all critical flags across agents
    all_flags: List[str] = []
    for p in positions:
        all_flags.extend(p.get("flags", []))

    critical_flags = {"EARLY_SEPSIS_PATTERN", "HYPOTENSION", "ANTICOAGULATED",
                      "IMMUNOCOMPROMISED", "CONGESTIVE_HEART_FAILURE", "HYPOXIA"}
    has_critical = bool(critical_flags.intersection(set(all_flags)))

    # ESI determination
    esi_level = _determine_esi(consensus_risk, has_critical)
    reassessment = _reassessment_seconds(esi_level, context_mult)

    # Should we escalate?
    should_escalate = esi_level <= 2 or consensus_risk >= 0.65
    if esi_level == 1 or consensus_risk >= 0.85:
        escalation_urgency = "IMMEDIATE"
    elif should_escalate:
        escalation_urgency = "URGENT"
    else:
        escalation_urgency = "ROUTINE"

    # Evidence per agent
    evidence: Dict[str, List[str]] = {}
    for agent_name in ["vitals", "history", "context"]:
        out = agent_outputs.get(agent_name, {})
        evidence[agent_name] = out.get("findings", [])

    # Monitoring focus
    monitoring_focus: List[str] = []
    vitals_flags = agent_outputs.get("vitals", {}).get("flags", [])
    if any("SEPSIS" in f for f in vitals_flags):
        monitoring_focus.append("Sepsis markers: lactate, blood cultures, urine output")
    if "ANTICOAGULATED" in all_flags:
        monitoring_focus.append("Bleeding risk: skin colour, neurological status, urine colour")
    if "HYPOXIA" in vitals_flags:
        monitoring_focus.append("Respiratory: SpO₂ trend, respiratory effort, accessory muscle use")
    if "PROGRESSIVE_TACHYCARDIA" in vitals_flags:
        monitoring_focus.append("Haemodynamics: HR and BP trend every 5 minutes")
    if not monitoring_focus:
        monitoring_focus.append("Routine vital sign monitoring per reassessment interval")

    synthesis = SynthesisOutput(
        esi_level=esi_level,
        confidence=confidence,
        consensus_risk_score=consensus_risk,
        evidence=evidence,
        dissenting_opinions=conflicts,
        reassessment_interval_seconds=reassessment,
        monitoring_focus=monitoring_focus,
        should_escalate=should_escalate,
        escalation_urgency=escalation_urgency,
        debate_rounds=[
            {"round": 1, "positions": positions},
            {"round": 2, "conflicts": conflicts},
            {"round": 3, "consensus_risk": consensus_risk,
             "context_multiplier": context_mult, "esi_level": esi_level},
        ],
    )

    logger.info(
        f"[DebateNode] ESI={esi_level} ({_esi_label(esi_level)}) | "
        f"Risk={consensus_risk} | Escalate={should_escalate} ({escalation_urgency})"
    )

    return {
        **state,
        "synthesis_result": synthesis.model_dump(),
        "awaiting_human": True,
        "last_evaluation_time": datetime.now(timezone.utc).isoformat(),
    }