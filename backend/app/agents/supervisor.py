"""
Supervisor Agent — orchestrates routing between specialist agents.

The supervisor uses a simple completion-tracking pattern:
- It checks which agents have already run (stored in state["agents_completed"]).
- It routes to the next agent that hasn't run.
- Once all three specialist agents are done, it routes to debate_synthesis.

This will be enhanced with real LLM routing in a future iteration.
"""
from __future__ import annotations

import logging
from typing import Literal

from app.agents.state import TriageState

logger = logging.getLogger(__name__)

# The three specialist agents that must all complete before synthesis
REQUIRED_AGENTS = ["vitals", "history", "context"]


def supervisor_router(state: TriageState) -> TriageState:
    """
    Supervisor node: logs current state and decides what to do next.
    The actual routing decision is made by `route_to_agents` (used as
    the conditional edge function). This node just updates iteration count.
    """
    iteration = state.get("iteration_count", 0) + 1
    completed = state.get("agents_completed", [])

    logger.info(
        f"[Supervisor] Iteration {iteration} | "
        f"Agents completed: {completed} | "
        f"Patient: {state.get('patient_id', 'unknown')}"
    )

    return {
        **state,
        "iteration_count": iteration,
    }


def route_to_agents(
    state: TriageState,
) -> Literal["vitals", "history", "context", "all_complete"]:
    """
    Conditional edge function — tells LangGraph which node to visit next.

    Returns one of the agent keys or "all_complete" which maps to
    the debate_synthesis node.
    """
    completed = state.get("agents_completed", [])

    # Route to the first required agent that hasn't run yet
    for agent_name in REQUIRED_AGENTS:
        if agent_name not in completed:
            logger.info(f"[Supervisor] Routing to → {agent_name}_analysis")
            return agent_name

    # All specialist agents done → synthesise
    logger.info("[Supervisor] All agents complete → debate_synthesis")
    return "all_complete"


def check_escalation_needed(
    state: TriageState,
) -> Literal["escalate", "monitor"]:
    """
    Conditional edge after human_checkpoint.

    If the synthesis result recommends escalation AND the nurse has either
    confirmed or not yet responded, route to escalation_handler.
    Otherwise route to monitoring_loop.
    """
    synthesis = state.get("synthesis_result") or {}
    nurse = state.get("nurse_decision") or {}

    should_escalate = synthesis.get("should_escalate", False)
    nurse_decision = nurse.get("decision", "")

    # Nurse override to NOT escalate
    if nurse_decision == "override" and not nurse.get("override_escalate", True):
        logger.info("[Supervisor] Nurse overrode escalation → monitoring")
        return "monitor"

    if should_escalate:
        logger.info("[Supervisor] Escalation required → escalation_handler")
        return "escalate"

    logger.info("[Supervisor] No escalation needed → monitoring_loop")
    return "monitor"