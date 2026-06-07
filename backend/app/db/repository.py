"""
Async CRUD operations for TriageNet database models.

All functions accept an AsyncSession from the FastAPI dependency
and return typed model instances or raise on error.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentPerformance, AuditLog, EscalationEvent, TriageEncounter


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.utcnow()


# ── TriageEncounter ───────────────────────────────────────────────────────────

async def create_encounter(
    db: AsyncSession,
    *,
    patient_mrn: str,
    encounter_id: str | None = None,
    patient_name: str | None = None,
    patient_age: int | None = None,
    patient_sex: str | None = None,
    chief_complaint: str | None = None,
    department_id: str = "ED-01",
    langgraph_thread_id: str | None = None,
    initial_esi_level: int | None = None,
) -> TriageEncounter:
    """Create a new ED encounter row and return it."""
    encounter = TriageEncounter(
        encounter_id=encounter_id or str(uuid.uuid4()),
        patient_mrn=patient_mrn,
        patient_name=patient_name,
        patient_age=patient_age,
        patient_sex=patient_sex,
        chief_complaint=chief_complaint,
        department_id=department_id,
        langgraph_thread_id=langgraph_thread_id,
        initial_esi_level=initial_esi_level,
        arrival_time=_now(),
        monitoring_active=True,
    )
    db.add(encounter)
    await db.flush()   # get the PK without committing
    return encounter


async def get_encounter(db: AsyncSession, encounter_id: str) -> TriageEncounter | None:
    """Retrieve a single encounter by its primary key."""
    result = await db.execute(
        select(TriageEncounter).where(TriageEncounter.encounter_id == encounter_id)
    )
    return result.scalar_one_or_none()


async def get_active_encounters(db: AsyncSession) -> list[TriageEncounter]:
    """Return all encounters where monitoring is still active."""
    result = await db.execute(
        select(TriageEncounter)
        .where(TriageEncounter.monitoring_active == True)  # noqa: E712
        .order_by(TriageEncounter.arrival_time.desc())
    )
    return list(result.scalars().all())


async def update_encounter_state(
    db: AsyncSession,
    encounter_id: str,
    *,
    langgraph_state: dict | None = None,
    risk_score: float | None = None,
    ai_recommended_esi: int | None = None,
    nurse_confirmed_esi: int | None = None,
    nurse_override_reason: str | None = None,
    monitoring_active: bool | None = None,
    disposition: str | None = None,
) -> TriageEncounter | None:
    """Partial update — only supplied fields are written."""
    values: dict[str, Any] = {"updated_at": _now()}
    if langgraph_state is not None:
        values["langgraph_state"] = langgraph_state
    if risk_score is not None:
        values["risk_score"] = risk_score
    if ai_recommended_esi is not None:
        values["ai_recommended_esi"] = ai_recommended_esi
    if nurse_confirmed_esi is not None:
        values["nurse_confirmed_esi"] = nurse_confirmed_esi
    if nurse_override_reason is not None:
        values["nurse_override_reason"] = nurse_override_reason
    if monitoring_active is not None:
        values["monitoring_active"] = monitoring_active
    if disposition is not None:
        values["disposition"] = disposition
        values["disposition_time"] = _now()

    result = await db.execute(
        update(TriageEncounter)
        .where(TriageEncounter.encounter_id == encounter_id)
        .values(**values)
    )
    await db.flush()
    return await get_encounter(db, encounter_id)


# ── AgentPerformance ──────────────────────────────────────────────────────────

async def log_agent_performance(
    db: AsyncSession,
    *,
    encounter_id: str,
    agent_name: str,
    analysis_type: str | None = None,
    confidence_score: float | None = None,
    processing_time_ms: int | None = None,
    token_usage: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    data_quality_score: float | None = None,
    raw_output: dict | None = None,
) -> AgentPerformance:
    """Record one agent invocation for performance tracking."""
    perf = AgentPerformance(
        encounter_id=encounter_id,
        agent_name=agent_name,
        analysis_type=analysis_type,
        confidence_score=confidence_score,
        processing_time_ms=processing_time_ms,
        token_usage=token_usage,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        data_quality_score=data_quality_score,
        raw_output=raw_output,
    )
    db.add(perf)
    await db.flush()
    return perf


# ── EscalationEvent ───────────────────────────────────────────────────────────

async def create_escalation_event(
    db: AsyncSession,
    *,
    encounter_id: str,
    urgency_level: str,
    trigger_type: str | None = None,
    vitals_at_trigger: dict | None = None,
    agent_findings: dict | None = None,
    notification_channels: list[str] | None = None,
) -> EscalationEvent:
    """Record an escalation event and return it."""
    event = EscalationEvent(
        escalation_id=str(uuid.uuid4()),
        encounter_id=encounter_id,
        urgency_level=urgency_level,
        trigger_type=trigger_type,
        vitals_at_trigger=vitals_at_trigger,
        agent_findings=agent_findings,
        notification_channels=notification_channels,
    )
    db.add(event)
    await db.flush()
    return event


async def acknowledge_escalation(
    db: AsyncSession,
    escalation_id: str,
    *,
    acknowledged_by: str,
    outcome: str | None = None,
) -> EscalationEvent | None:
    """Mark an escalation as acknowledged and compute response time."""
    result = await db.execute(
        select(EscalationEvent).where(EscalationEvent.escalation_id == escalation_id)
    )
    event = result.scalar_one_or_none()
    if event is None:
        return None

    now = _now()
    response_time = int((now - event.created_at).total_seconds())
    await db.execute(
        update(EscalationEvent)
        .where(EscalationEvent.escalation_id == escalation_id)
        .values(
            acknowledged_at=now,
            acknowledged_by=acknowledged_by,
            response_time_seconds=response_time,
            outcome=outcome,
        )
    )
    await db.flush()
    return event


# ── AuditLog ──────────────────────────────────────────────────────────────────

async def write_audit_log(
    db: AsyncSession,
    *,
    actor_type: str,
    action: str,
    encounter_id: str | None = None,
    actor_id: str | None = None,
    details: dict | None = None,
    patient_state_snapshot: dict | None = None,
) -> AuditLog:
    """Append an immutable audit record."""
    log = AuditLog(
        encounter_id=encounter_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        details=details,
        patient_state_snapshot=patient_state_snapshot,
    )
    db.add(log)
    await db.flush()
    return log