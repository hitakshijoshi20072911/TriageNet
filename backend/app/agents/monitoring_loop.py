"""
Monitoring Loop Node

Controls the re-evaluation cadence. After the initial triage recommendation
is given (and either escalated or not), this node checks whether a fresh
full-agent re-evaluation is needed.

Adaptive intervals:
  ESI 1–2 / risk ≥ 0.65  → re-evaluate every  5 minutes
  ESI 3   / risk 0.35–0.65 → re-evaluate every 15 minutes
  ESI 4–5 / risk < 0.35   → re-evaluate every 30 minutes
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Literal

from app.agents.state import TriageState

logger = logging.getLogger(__name__)


def _seconds_since_last(state: TriageState) -> float:
    last_str = state.get("last_evaluation_time")
    if not last_str:
        return 99999.0
    try:
        last = datetime.fromisoformat(last_str)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last).total_seconds()
    except Exception:
        return 99999.0


def _reassessment_interval(state: TriageState) -> int:
    synthesis = state.get("synthesis_result") or {}
    base = synthesis.get("reassessment_interval_seconds", 900)  # default 15 min
    return max(base, 60)


def monitoring_loop_node(state: TriageState) -> TriageState:
    """
    LangGraph node — decides whether to loop back to supervisor_router
    (triggering a new full agent sweep) or simply wait.

    The conditional edge after this node routes to:
      "reevaluate"  → supervisor_router (clears agents_completed, starts fresh)
      "continue"    → loops back here after a delay (in async context)
      "discharge"   → END (patient left ED)
    """
    patient_id = state.get("patient_id", "unknown")
    monitoring_active = state.get("monitoring_active", True)

    if not monitoring_active:
        logger.info(f"[MonitoringLoop] Patient {patient_id} discharged from monitoring")
        return {**state, "monitoring_active": False}

    elapsed     = _seconds_since_last(state)
    interval    = _reassessment_interval(state)
    synthesis   = state.get("synthesis_result") or {}
    risk_score  = synthesis.get("consensus_risk_score", 0.3)

    logger.info(
        f"[MonitoringLoop] Patient {patient_id} | "
        f"risk={risk_score:.2f} | elapsed={elapsed:.0f}s | "
        f"interval={interval}s"
    )

    # Mark next evaluation time
    next_eval = (
        datetime.now(timezone.utc) + timedelta(seconds=interval)
    ).isoformat()

    if elapsed >= interval:
        logger.info(f"[MonitoringLoop] Triggering re-evaluation for {patient_id}")
        # Reset agents_completed so all agents re-run
        return {
            **state,
            "agents_completed": [],
            "agent_outputs": {},
            "next_evaluation_time": next_eval,
            "awaiting_human": False,
        }

    # Not yet time — return state unchanged, loop will re-check
    logger.info(f"[MonitoringLoop] {interval - elapsed:.0f}s until next eval")
    return {
        **state,
        "next_evaluation_time": next_eval,
    }


def should_reevaluate(state: TriageState) -> Literal["reevaluate", "continue", "discharge"]:
    """
    Conditional edge function used after monitoring_loop_node.
    """
    if not state.get("monitoring_active", True):
        return "discharge"

    agents_completed = state.get("agents_completed", [])
    # If agents_completed was cleared by monitoring_loop_node, trigger re-evaluation
    if len(agents_completed) == 0:
        return "reevaluate"

    return "continue"