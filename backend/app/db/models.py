"""
SQLAlchemy ORM models for TriageNet.

Tables:
  - TriageEncounter  — one row per ED visit
  - AgentPerformance — metrics per agent run per encounter
  - EscalationEvent  — escalation records linked to an encounter
  - AuditLog         — immutable action log
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ── TriageEncounter ───────────────────────────────────────────────────────────

class TriageEncounter(Base):
    """
    Core encounter record created when a patient arrives at the ED.
    The `langgraph_state` JSONB column stores the full LangGraph
    TriageState so the graph can be resumed at any point.
    """
    __tablename__ = "triage_encounters"

    encounter_id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=_new_uuid
    )
    patient_mrn: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    patient_name: Mapped[str | None] = mapped_column(String(200))
    patient_age: Mapped[int | None] = mapped_column(Integer)
    patient_sex: Mapped[str | None] = mapped_column(String(10))

    chief_complaint: Mapped[str | None] = mapped_column(Text)
    arrival_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.now()
    )
    triage_time: Mapped[datetime | None] = mapped_column(DateTime)

    initial_esi_level: Mapped[int | None] = mapped_column(Integer)
    ai_recommended_esi: Mapped[int | None] = mapped_column(Integer)
    nurse_confirmed_esi: Mapped[int | None] = mapped_column(Integer)
    nurse_override_reason: Mapped[str | None] = mapped_column(Text)

    risk_score: Mapped[float | None] = mapped_column(Float)
    monitoring_active: Mapped[bool] = mapped_column(default=True)

    # LangGraph full state persisted as JSON so we can resume the graph
    langgraph_state: Mapped[dict | None] = mapped_column(JSON)
    langgraph_thread_id: Mapped[str | None] = mapped_column(String(100))

    disposition: Mapped[str | None] = mapped_column(String(50))
    disposition_time: Mapped[datetime | None] = mapped_column(DateTime)
    department_id: Mapped[str] = mapped_column(String(50), default="ED-01")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    agent_performances: Mapped[list["AgentPerformance"]] = relationship(
        "AgentPerformance", back_populates="encounter", cascade="all, delete-orphan"
    )
    escalation_events: Mapped[list["EscalationEvent"]] = relationship(
        "EscalationEvent", back_populates="encounter", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="encounter", cascade="all, delete-orphan"
    )


# ── AgentPerformance ──────────────────────────────────────────────────────────

class AgentPerformance(Base):
    """
    Records one agent invocation: which agent ran, how long, how confident,
    and how many tokens were consumed. Used for cost tracking and evaluation.
    """
    __tablename__ = "agent_performance"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    encounter_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("triage_encounters.encounter_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    analysis_type: Mapped[str | None] = mapped_column(String(50))

    confidence_score: Mapped[float | None] = mapped_column(Float)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage: Mapped[int | None] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)

    data_quality_score: Mapped[float | None] = mapped_column(Float)
    raw_output: Mapped[dict | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now()
    )

    encounter: Mapped["TriageEncounter"] = relationship(
        "TriageEncounter", back_populates="agent_performances"
    )


# ── EscalationEvent ───────────────────────────────────────────────────────────

class EscalationEvent(Base):
    """
    An escalation triggered when risk score crosses a threshold.
    Tracks acknowledgment and response time for quality metrics.
    """
    __tablename__ = "escalation_events"

    escalation_id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=_new_uuid
    )
    encounter_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("triage_encounters.encounter_id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    urgency_level: Mapped[str] = mapped_column(String(20), nullable=False)
    # "IMMEDIATE" | "URGENT" | "ROUTINE"

    trigger_type: Mapped[str | None] = mapped_column(String(50))
    # "VITALS_DETERIORATION" | "PATTERN_MATCH" | "MANUAL" | "MONITORING_LOOP"

    vitals_at_trigger: Mapped[dict | None] = mapped_column(JSON)
    agent_findings: Mapped[dict | None] = mapped_column(JSON)
    notification_channels: Mapped[list | None] = mapped_column(JSON)

    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime)
    acknowledged_by: Mapped[str | None] = mapped_column(String(100))
    response_time_seconds: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now()
    )

    encounter: Mapped["TriageEncounter"] = relationship(
        "TriageEncounter", back_populates="escalation_events"
    )


# ── AuditLog ──────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Append-only audit trail. Every agent action, nurse decision, and system
    event is logged here for compliance and retrospective analysis.
    """
    __tablename__ = "audit_log"

    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    encounter_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("triage_encounters.encounter_id", ondelete="SET NULL"),
        index=True
    )

    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # "AGENT" | "NURSE" | "PHYSICIAN" | "SYSTEM"

    actor_id: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON)
    patient_state_snapshot: Mapped[dict | None] = mapped_column(JSON)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=func.now()
    )

    encounter: Mapped["TriageEncounter"] = relationship(
        "TriageEncounter", back_populates="audit_logs"
    )