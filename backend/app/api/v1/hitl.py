"""Human‑in‑the‑loop decision endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.repository import update_encounter_state
from app.agents.graph import triage_graph
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/decision")
async def submit_decision(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Record a nurse decision (confirm / override)."""
    patient_id = payload.get("encounter_id") or payload.get("patient_id")
    decision   = payload.get("decision", "confirm")
    reason     = payload.get("reason", "")

    # Update encounter with nurse decision
    if decision == "override":
        await update_encounter_state(
            db, patient_id,
            nurse_confirmed_esi=payload.get("esi_level"),
            nurse_override_reason=reason,
        )
    else:
        await update_encounter_state(db, patient_id, nurse_override_reason=reason)

    # If the graph is paused (human checkpoint), we would resume it here.
    # For now, just log it.
    logger.info(f"Nurse decision for {patient_id}: {decision} – {reason}")
    return {"status": "recorded"}
