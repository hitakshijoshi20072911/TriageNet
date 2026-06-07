"""
TriageNet core state schema.

`TriageState` is the single TypedDict that flows through every node
in the LangGraph state machine. Every agent reads from it, writes its
output into `agent_outputs[agent_name]`, and returns the merged dict.

`VitalReading` is the atomic unit of physiological data — one timestamp
worth of vitals from a monitor, wearable, or the simulator.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models (used for validation / serialisation)
# ─────────────────────────────────────────────────────────────────────────────

class VitalReading(BaseModel):
    """One timestamped snapshot of patient vitals."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    heart_rate: float           # bpm
    systolic_bp: float          # mmHg
    diastolic_bp: float         # mmHg
    resp_rate: float            # breaths/min
    spO2: float                 # %
    temperature: float          # °C
    consciousness: str = "A"   # AVPU: A | V | P | U

    @property
    def pulse_pressure(self) -> float:
        return self.systolic_bp - self.diastolic_bp

    @property
    def shock_index(self) -> float:
        """Shock index = HR / SBP. >1.0 is concerning."""
        return self.heart_rate / max(self.systolic_bp, 1)

    @property
    def map(self) -> float:
        """Mean arterial pressure."""
        return self.diastolic_bp + (self.pulse_pressure / 3)


class AgentOutput(BaseModel):
    """Standardised wrapper every agent must return."""
    agent_name: str
    risk_score: float               # 0.0 – 1.0
    confidence: float               # 0.0 – 1.0
    findings: List[str]             # human-readable bullet points
    recommendation: str             # short clinical recommendation
    data_quality: float = 1.0      # 0.0 – 1.0; affects debate weighting
    supporting_evidence: Dict[str, Any] = Field(default_factory=dict)
    flags: List[str] = Field(default_factory=list)   # e.g. "ANTICOAGULATED"
    raw: Dict[str, Any] = Field(default_factory=dict)


class SynthesisOutput(BaseModel):
    """Result of the multi-agent debate node."""
    esi_level: int                          # 1 (most urgent) – 5 (least)
    confidence: float
    consensus_risk_score: float
    evidence: Dict[str, List[str]]          # agent_name → findings list
    dissenting_opinions: List[str]
    reassessment_interval_seconds: int
    monitoring_focus: List[str]             # what to watch next
    debate_rounds: List[Dict[str, Any]] = Field(default_factory=list)
    should_escalate: bool = False
    escalation_urgency: str = "ROUTINE"    # IMMEDIATE | URGENT | ROUTINE


class NurseDecision(BaseModel):
    """Captured nurse confirmation or override."""
    decision: str           # "confirm" | "override"
    confirmed_esi: Optional[int] = None
    reason: Optional[str] = None
    nurse_id: str = "nurse-unknown"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EscalationRecord(BaseModel):
    """One entry in the escalation history list."""
    escalation_id: str
    urgency_level: str
    trigger_type: str
    timestamp: datetime
    acknowledged: bool = False
    findings: Dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph TypedDict state
# ─────────────────────────────────────────────────────────────────────────────

class TriageState(TypedDict, total=False):
    """
    Canonical state object passed between every node in the LangGraph graph.

    Keys marked Optional may be None at various stages of processing —
    guard all reads with `state.get("key")`.
    """
    # Patient identity
    patient_id: str
    encounter_id: str
    department_id: str

    # Physiological data stream (list grows as new readings arrive)
    vitals_stream: List[Dict[str, Any]]     # serialised VitalReading dicts

    # Clinical context
    fhir_bundle: Optional[Dict[str, Any]]   # raw FHIR R4 bundle or None
    department_context: Optional[Dict[str, Any]]

    # Per-agent outputs keyed by agent name
    agent_outputs: Dict[str, Dict[str, Any]]   # serialised AgentOutput dicts

    # Orchestration metadata
    agents_completed: List[str]     # tracks which agents have finished
    iteration_count: int            # how many supervisor loops we've done

    # Debate & decision
    synthesis_result: Optional[Dict[str, Any]]  # serialised SynthesisOutput
    nurse_decision: Optional[Dict[str, Any]]    # serialised NurseDecision

    # Monitoring lifecycle
    monitoring_active: bool
    last_evaluation_time: Optional[str]     # ISO datetime string
    next_evaluation_time: Optional[str]

    # Escalation history
    escalation_history: List[Dict[str, Any]]

    # Human-in-the-loop interrupt flag
    awaiting_human: bool

    # Error propagation
    error: Optional[str]