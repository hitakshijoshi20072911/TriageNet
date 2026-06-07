import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import TriageEncounter, EscalationEvent
from app.db.repository import create_escalation_event
from app.agents.graph import create_workflow
from app.agents.state import TriageState
from datetime import datetime
import copy
import json


# Global WebSocket connection manager (simple in-memory)
class WebSocketManager:
    def __init__(self):
        self.active_connections: dict = {}  # patient_id -> list of websockets
    
    async def connect(self, patient_id: str, websocket):
        if patient_id not in self.active_connections:
            self.active_connections[patient_id] = []
        self.active_connections[patient_id].append(websocket)
        print(f"[WebSocket Manager] Client connected for patient {patient_id}")
    
    def disconnect(self, patient_id: str, websocket):
        if patient_id in self.active_connections:
            self.active_connections[patient_id].remove(websocket)
            if not self.active_connections[patient_id]:
                del self.active_connections[patient_id]
        print(f"[WebSocket Manager] Client disconnected for patient {patient_id}")
    
    async def broadcast_to_patient(self, patient_id: str, message: dict):
        if patient_id in self.active_connections:
            for ws in self.active_connections[patient_id]:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    print(f"[WebSocket Manager] Error sending to client: {e}")


# Global manager instance
ws_manager = WebSocketManager()


async def monitor_patient(patient_id: int, db: AsyncSession):
    """Monitor a single patient and trigger re-evaluation if needed."""
    print(f"[Monitor Loop] Evaluating patient {patient_id}")
    
    # Get patient from DB
    result = await db.execute(
        select(TriageEncounter).where(TriageEncounter.encounter_id == patient_id)
    )
    encounter = result.scalar_one_or_none()
    
    if not encounter:
        print(f"[Monitor Loop] Patient {patient_id} not found")
        return
    
    if not encounter.monitoring_active:
        print(f"[Monitor Loop] Patient {patient_id} not in monitoring mode")
        return
    
    # Get current state
    current_state = encounter.langgraph_state or {}
    current_risk = current_state.get("synthesis_result", {}).get("consensus_risk_score", 0)
    
    print(f"[Monitor Loop] Patient {patient_id} current risk: {current_risk}")
    
    # Check if risk has crossed threshold (e.g., increased significantly)
    RISK_THRESHOLD = 0.7
    
    if current_risk > RISK_THRESHOLD:
        print(f"[Monitor Loop] Patient {patient_id} risk crossed threshold! Creating escalation event.")
        
        # Create escalation event
        await create_escalation_event(
            db,
            encounter_id=patient_id,
            urgency_level="high",
            trigger_type="risk_threshold"
        )
        
        # Broadcast to WebSocket clients
        await ws_manager.broadcast_to_patient(
            str(patient_id),
            {
                "type": "escalation",
                "patient_id": patient_id,
                "risk_score": current_risk,
                "message": f"Risk threshold crossed for patient {patient_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    else:
        # Broadcast monitoring update
        await ws_manager.broadcast_to_patient(
            str(patient_id),
            {
                "type": "monitoring_update",
                "patient_id": patient_id,
                "risk_score": current_risk,
                "message": f"Routine monitoring check for patient {patient_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    await db.commit()


async def monitoring_loop():
    """Background monitoring loop that runs every 15 seconds."""
    print("[Monitor Loop] Starting monitoring background task...")
    
    while True:
        try:
            print(f"[Monitor Loop] Running monitoring cycle at {datetime.utcnow()}")
            
            async with AsyncSessionLocal() as db:
                # Get all active patients with monitoring_active=True
                result = await db.execute(
                    select(TriageEncounter).where(TriageEncounter.monitoring_active == True)
                )
                patients = result.scalars().all()
                
                print(f"[Monitor Loop] Found {len(patients)} patients to monitor")
                
                # Monitor each patient
                for patient in patients:
                    await monitor_patient(patient.encounter_id, db)
            
            # Wait 15 seconds before next cycle
            await asyncio.sleep(15)
            
        except Exception as e:
            print(f"[Monitor Loop] Error in monitoring cycle: {e}")
            await asyncio.sleep(15)


async def start_monitoring():
    """Start the monitoring loop as a background task."""
    return asyncio.create_task(monitoring_loop())
