from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.vitals_stream import generate_vitals
from app.services.monitor_loop import ws_manager
import json
import asyncio
import random

router = APIRouter()


@router.websocket("/ws/{patient_id}")
async def websocket_endpoint(websocket: WebSocket, patient_id: str):
    """WebSocket endpoint for real-time vitals and agent updates."""
    await websocket.accept()
    
    # Register with WebSocket manager
    await ws_manager.connect(patient_id, websocket)
    
    print(f"WebSocket connected for patient {patient_id}")
    
    try:
        # Start vitals streaming
        vitals_generator = generate_vitals(patient_id)
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to TriageNet real-time feed",
            "patient_id": patient_id
        })
        
        # Stream vitals and agent updates
        while True:
            # Get next vital reading
            try:
                vital = next(vitals_generator)
                
                # Send vital reading as JSON
                await websocket.send_json({
                    "type": "vital",
                    "patient_id": patient_id,
                    "data": {
                        "timestamp": vital.timestamp.isoformat(),
                        "heart_rate": vital.heart_rate,
                        "systolic_bp": vital.systolic_bp,
                        "diastolic_bp": vital.diastolic_bp,
                        "resp_rate": vital.resp_rate,
                        "spO2": vital.spO2,
                        "temperature": vital.temperature
                    }
                })
                
                # Periodically send mock agent feed updates
                if random.random() < 0.3:  # 30% chance to send agent update
                    await websocket.send_json({
                        "type": "agent_update",
                        "patient_id": patient_id,
                        "data": {
                            "agent": random.choice(["Triage Agent", "Risk Agent", "Resource Agent"]),
                            "message": f"Processing patient {patient_id}",
                            "timestamp": vital.timestamp.isoformat()
                        }
                    })
                
            except StopIteration:
                # Generator exhausted, create a new one
                vitals_generator = generate_vitals(patient_id)
            
            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for patient {patient_id}")
        ws_manager.disconnect(patient_id, websocket)
    except Exception as e:
        print(f"WebSocket error for patient {patient_id}: {e}")
        ws_manager.disconnect(patient_id, websocket)
        try:
            await websocket.close()
        except:
            pass
