"""
Human-in-the-Loop Checkpoint Node

In production this node uses LangGraph's interrupt() to pause graph execution
and wait for a nurse's decision via the REST API (POST /api/v1/hitl/decision).

For this skeleton iteration we implement a non-blocking version that:
  1. Logs the recommendation clearly for the nurse
  2. Sets awaiting_human = True in state
  3. Returns state immediately — the graph will be resumed by the HITL API endpoint

The actual LangGraph interrupt() wiring happens when we connect the API in Prompt 4.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agents.state import TriageState

logger = logging.getLogger(__name__)


def human_in_the_loop_node(state: TriageState) -> TriageState:
    """
    LangGraph node — presents the synthesis result for nurse review.

    On interrupt: execution halts here. The API endpoint will call
    graph.update_state() with the nurse's decision and resume.
    """
    synthesis = state.get("synthesis_result") or {}
    patient_id = state.get("patient_id", "unknown")

    esi_level    = synthesis.get("esi_level", "?")
    risk_score   = synthesis.get("consensus_risk_score", 0.0)
    confidence   = synthesis.get("confidence", 0.0)
    should_escalate = synthesis.get("should_escalate", False)
    urgency      = synthesis.get("escalation_urgency", "ROUTINE")
    monitoring   = synthesis.get("monitoring_focus", [])
    dissenting   = synthesis.get("dissenting_opinions", [])

    logger.info(
        f"\n{'='*60}\n"
        f"  ⚕️  TRIAGENET RECOMMENDATION — Patient: {patient_id}\n"
        f"{'='*60}\n"
        f"  ESI Level:    {esi_level}\n"
        f"  Risk Score:   {risk_score:.2f} (confidence {confidence:.0%})\n"
        f"  Escalate:     {'YES — ' + urgency if should_escalate else 'NO'}\n"
        f"  Watch for:    {', '.join(monitoring[:2])}\n"
        f"  Conflicts:    {len(dissenting)} debate conflicts resolved\n"
        f"{'='*60}\n"
        f"  >>> Awaiting nurse CONFIRM or OVERRIDE <<<\n"
        f"{'='*60}"
    )

    # In production: langgraph.interrupt("Awaiting nurse decision")
    # For now we set the flag and let execution continue
    return {
        **state,
        "awaiting_human": True,
        "last_evaluation_time": datetime.now(timezone.utc).isoformat(),
    }