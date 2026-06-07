"""Patient intake and retrieval endpoints."""
from __future__ import annotations
import uuid
import logging
import copy
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.repository import create_encounter, get_encounter, get_active_encounters
from app.agents.graph import triage_graph
from app.agents.state import TriageState
from app.services.vitals_stream import generate_vitals_batch
from app.services.simulator import (
    DEMO_PATIENTS,
    generate_department_context,
    build_fhir_bundle,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _serialize_datetime(obj: Any) -> Any:
    """Recursively serialize datetime objects to ISO format strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_datetime(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_serialize_datetime(item) for item in obj)
    else:
        return obj


@router.post("/intake")
async def patient_intake(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Accept a new patient, run the multi‑agent triage pipeline, and return the synthesis."""
    patient_mrn     = payload.get("patient_mrn", "UNKNOWN")
    chief_complaint = payload.get("chief_complaint", "")
    age             = payload.get("age", 45)
    gender          = payload.get("gender", "unknown")
    initial_vitals  = payload.get("initial_vitals", {})

    encounter_id = str(uuid.uuid4())

    # ── Build the initial TriageState ─────────────────────────
    # 1. Generate a few baseline vitals for this patient
    vitals_list = generate_vitals_batch(
        patient_id=encounter_id,
        profile="deteriorating_sepsis",   # realistic demo profile
        n=6,
    )

    # 2. Department context
    dept_context = generate_department_context()

    # 3. FHIR bundle (use demo patient P001 if available, else build a minimal one)
    fhir_bundle = DEMO_PATIENTS.get(
        patient_mrn,
        build_fhir_bundle(
            patient_mrn=patient_mrn,
            name=f"{payload.get('name', 'Unknown')}",
            age=age,
            sex=gender.lower(),
        ),
    )

    initial_state: TriageState = {
        "patient_id":        patient_mrn,
        "encounter_id":      encounter_id,
        "department_id":     dept_context.get("department_id", "ED-01"),
        "vitals_stream":     [v.model_dump() for v in vitals_list],
        "fhir_bundle":       fhir_bundle,
        "department_context": dept_context,
        "agent_outputs":     {},
        "agents_completed":  [],
        "iteration_count":   0,
        "escalation_history": [],
        "monitoring_active": False,  # Disable monitoring for initial intake
        "awaiting_human":    False,
    }

    # ── Run the LangGraph pipeline ─────────────────────────────
    config = {"configurable": {"thread_id": encounter_id}}

    try:
        result = await triage_graph.ainvoke(initial_state, config=config)
        logger.info(f"Graph execution completed for {encounter_id}")
    except Exception as exc:
        logger.exception(f"Graph execution failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Triage pipeline failed: {str(exc)}")

    synthesis = result.get("synthesis_result", {})
    risk_score = synthesis.get("consensus_risk_score", 0.0)
    esi_level = synthesis.get("esi_level", 3)

    # ── Persist encounter to database ─────────────────────────
    try:
        await create_encounter(
            db,
            patient_mrn=patient_mrn,
            encounter_id=encounter_id,
            patient_name=payload.get("name", f"Patient-{patient_mrn}"),
            patient_age=age,
            patient_sex=gender,
            chief_complaint=chief_complaint,
            department_id=dept_context.get("department_id", "ED-01"),
            langgraph_thread_id=encounter_id,
            initial_esi_level=esi_level,
        )
        await db.commit()
        logger.info(f"Encounter created: {encounter_id}")
    except Exception as exc:
        logger.exception(f"Failed to create encounter: {exc}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create encounter: {str(exc)}")

    # Update with full state and risk score
    from app.db.repository import update_encounter_state
    try:
        # Serialize datetime objects for JSON storage
        state_to_store = _serialize_datetime(result)

        await update_encounter_state(
            db,
            encounter_id,
            langgraph_state=state_to_store,
            risk_score=risk_score,
            ai_recommended_esi=esi_level,
        )
        await db.commit()
        logger.info(f"Encounter state updated: {encounter_id}")
    except Exception as exc:
        logger.exception(f"Failed to update encounter state: {exc}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update encounter state: {str(exc)}")

    return {
        "encounter_id": encounter_id,
        "patient_mrn": patient_mrn,
        "esi_level": esi_level,
        "risk_score": risk_score,
        "synthesis": synthesis,
    }


@router.get("/")
async def list_patients(db: AsyncSession = Depends(get_db)):
    """Return all active encounters with current risk/ESI info."""
    encounters = await get_active_encounters(db)
    return [
        {
            "encounter_id": enc.encounter_id,
            "patient_mrn": enc.patient_mrn,
            "chief_complaint": enc.chief_complaint,
            "risk_score": enc.risk_score,
            "esi_level": enc.nurse_confirmed_esi or enc.ai_recommended_esi,
        }
        for enc in encounters
    ]


@router.get("/{patient_id}")
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Return full encounter details including LangGraph state."""
    enc = await get_encounter(db, patient_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "encounter_id": enc.encounter_id,
        "patient_mrn": enc.patient_mrn,
        "chief_complaint": enc.chief_complaint,
        "arrival_time": enc.arrival_time.isoformat() if enc.arrival_time else None,
        "risk_score": enc.risk_score,
        "esi_level": enc.nurse_confirmed_esi or enc.ai_recommended_esi,
        "langgraph_state": enc.langgraph_state,
    }
