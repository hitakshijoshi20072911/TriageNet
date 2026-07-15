"""
LangGraph Graph Construction for TriageNet.

Creates the full agentic workflow:

  supervisor_router
      ↓  (conditional: which agent next?)
  vitals_analysis ──┐
  history_synthesis ─┤→ supervisor_router → (all_complete) → debate_synthesis
  context_analysis ──┘
      ↓
  debate_synthesis
      ↓
  human_checkpoint
      ↓  (conditional: escalate or monitor?)
  escalation_handler → END
  monitoring_loop    → (conditional: reevaluate → supervisor_router | continue | discharge → END)

State persistence uses MemorySaver (in-memory checkpointer) for now.
Replace with AsyncPostgresSaver or CosmosSaver in production.
"""
from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import TriageState
from app.agents.supervisor import (
    supervisor_router,
    route_to_agents,
    check_escalation_needed,
)
from app.agents.vitals_agent      import vitals_analysis_agent
from app.agents.history_agent     import history_synthesis_agent
from app.agents.context_agent     import context_analysis_agent
from app.agents.bed_allocation    import bed_allocation_agent
from app.agents.debate_node       import debate_synthesis_node
from app.agents.human_checkpoint  import human_in_the_loop_node
from app.agents.escalation_handler import escalation_handler
from app.agents.monitoring_loop   import monitoring_loop_node, should_reevaluate

logger = logging.getLogger(__name__)


def create_workflow():
    """
    Build, compile, and return the TriageNet LangGraph state machine.

    Returns a CompiledGraph with MemorySaver checkpointing.
    Pass a config with thread_id for per-patient state isolation:

        config = {"configurable": {"thread_id": encounter_id}}
        result = await graph.ainvoke(initial_state, config=config)
    """
    workflow = StateGraph(TriageState)

    # ── Register nodes ────────────────────────────────────────────────────────
    workflow.add_node("supervisor_router",    supervisor_router)
    workflow.add_node("vitals_analysis",      vitals_analysis_agent)
    workflow.add_node("history_synthesis",    history_synthesis_agent)
    workflow.add_node("context_analysis",     context_analysis_agent)
    workflow.add_node("bed_allocation",       bed_allocation_agent)
    workflow.add_node("debate_synthesis",     debate_synthesis_node)
    workflow.add_node("human_checkpoint",     human_in_the_loop_node)
    workflow.add_node("escalation_handler",   escalation_handler)
    workflow.add_node("monitoring_loop",      monitoring_loop_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    workflow.set_entry_point("supervisor_router")

    # ── Supervisor → specialist agents (conditional) ──────────────────────────
    workflow.add_conditional_edges(
        "supervisor_router",
        route_to_agents,
        {
            "vitals":       "vitals_analysis",
            "history":      "history_synthesis",
            "context":      "context_analysis",
            "all_complete": "debate_synthesis",
        },
    )

    # ── Each specialist loops back to supervisor ──────────────────────────────
    workflow.add_edge("vitals_analysis",   "supervisor_router")
    workflow.add_edge("history_synthesis", "supervisor_router")
    workflow.add_edge("context_analysis",  "supervisor_router")

    # ── Debate → bed allocation → HITL ───────────────────────────────────────
    workflow.add_edge("debate_synthesis", "bed_allocation")
    workflow.add_edge("bed_allocation",   "human_checkpoint")

    # ── HITL → escalate or monitor (conditional) ──────────────────────────────
    workflow.add_conditional_edges(
        "human_checkpoint",
        check_escalation_needed,
        {
            "escalate": "escalation_handler",
            "monitor":  "monitoring_loop",
        },
    )

    # ── Escalation always ends (nurse/physician takes over) ───────────────────
    workflow.add_edge("escalation_handler", END)

    # ── Monitoring loop re-evaluation or end ──────────────────────────────────
    workflow.add_conditional_edges(
        "monitoring_loop",
        should_reevaluate,
        {
            "reevaluate": "supervisor_router",   # fresh agent sweep
            "continue":   "monitoring_loop",     # wait and check again
            "discharge":  END,                   # patient left ED
        },
    )

    # ── Compile with MemorySaver checkpointer ────────────────────────────────
    checkpointer = MemorySaver()
    graph = workflow.compile(checkpointer=checkpointer)

    logger.info(" TriageNet LangGraph compiled successfully")
    logger.info(f"   Nodes: {list(workflow.nodes.keys())}")

    return graph


# Module-level singleton — import this in API routes
triage_graph = create_workflow()
