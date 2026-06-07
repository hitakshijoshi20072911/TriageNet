"""
Escalation Handler

Classifies urgency, selects notification channels, builds the alert payload,
and appends an EscalationRecord to state["escalation_history"].

In production, channel dispatchers (Service Bus, push notifications, overhead page)
are wired here. For now we log loudly and return the full escalation payload.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.agents.state import EscalationRecord, TriageState

logger = logging.getLogger(__name__)

URGENCY_CHANNELS: Dict[str, List[str]] = {
    "IMMEDIATE": ["auditory_alarm", "overhead_page", "mobile_push", "nurse_station_popup"],
    "URGENT":    ["mobile_push", "nurse_station_popup"],
    "ROUTINE":   ["task_queue", "ehr_notification"],
}

URGENCY_DEADLINES_SECONDS: Dict[str, int] = {
    "IMMEDIATE": 300,    #  5 minutes
    "URGENT":    1800,   # 30 minutes
    "ROUTINE":   7200,   #  2 hours
}


def _build_alert_message(synthesis: Dict[str, Any], patient_id: str) -> str:
    esi    = synthesis.get("esi_level", "?")
    risk   = synthesis.get("consensus_risk_score", 0.0)
    focus  = synthesis.get("monitoring_focus", ["Assess immediately"])
    urgency = synthesis.get("escalation_urgency", "ROUTINE")

    return (
        f"[TriageNet {urgency}] Patient {patient_id} — ESI {esi}, "
        f"Risk {risk:.0%}. Action: {focus[0] if focus else 'Assess now'}."
    )


def escalation_handler(state: TriageState) -> TriageState:
    """
    LangGraph node — builds and dispatches escalation alert.
    Appends to escalation_history in state.
    """
    patient_id = state.get("patient_id", "unknown")
    synthesis  = state.get("synthesis_result") or {}
    vitals_out = (state.get("agent_outputs") or {}).get("vitals", {})

    urgency  = synthesis.get("escalation_urgency", "ROUTINE")
    channels = URGENCY_CHANNELS.get(urgency, ["task_queue"])
    deadline = URGENCY_DEADLINES_SECONDS.get(urgency, 7200)
    alert_msg = _build_alert_message(synthesis, patient_id)

    escalation_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    logger.warning(
        f"\n{'!'*60}\n"
        f"  🚨 ESCALATION — {urgency}\n"
        f"{'!'*60}\n"
        f"  Patient:    {patient_id}\n"
        f"  ESI Level:  {synthesis.get('esi_level', '?')}\n"
        f"  Risk Score: {synthesis.get('consensus_risk_score', 0.0):.2f}\n"
        f"  Channels:   {', '.join(channels)}\n"
        f"  Deadline:   {deadline // 60} minutes\n"
        f"  Message:    {alert_msg}\n"
        f"{'!'*60}"
    )

    record = EscalationRecord(
        escalation_id=escalation_id,
        urgency_level=urgency,
        trigger_type="AGENT_SYNTHESIS",
        timestamp=now,
        acknowledged=False,
        findings={
            "esi_level":     synthesis.get("esi_level"),
            "risk_score":    synthesis.get("consensus_risk_score"),
            "monitoring":    synthesis.get("monitoring_focus"),
            "vitals_flags":  vitals_out.get("flags", []),
            "alert_message": alert_msg,
            "channels":      channels,
            "deadline_s":    deadline,
        },
    )

    escalation_history = list(state.get("escalation_history") or [])
    escalation_history.append(record.model_dump())

    return {
        **state,
        "escalation_history": escalation_history,
        "monitoring_active": True,
        "awaiting_human": False,
    }