from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Bed:
    bed_id: str
    bed_type: str  # "icu", "monitored", "general"
    occupied_by: Optional[int] = None  # patient_id or None


class EmergencyDepartment:
    """Digital Twin of an Emergency Department."""
    
    def __init__(self):
        # Initialize beds
        self.beds: Dict[str, Bed] = {}
        
        # ICU beds (1 bed)
        for i in range(1):
            bed_id = f"icu-{i}"
            self.beds[bed_id] = Bed(bed_id=bed_id, bed_type="icu")
        
        # Monitored beds (6 beds)
        for i in range(6):
            bed_id = f"monitored-{i}"
            self.beds[bed_id] = Bed(bed_id=bed_id, bed_type="monitored")
        
        # General beds (10 beds)
        for i in range(10):
            bed_id = f"general-{i}"
            self.beds[bed_id] = Bed(bed_id=bed_id, bed_type="general")
        
        # Waiting queue: list of (patient_id, risk_score) tuples, ordered by risk (high to low)
        self.waiting_queue: List[tuple] = []
    
    def admit_patient(self, patient_id: int, risk_score: float = 0.5) -> None:
        """Add patient to waiting queue."""
        self.waiting_queue.append((patient_id, risk_score))
        # Sort by risk score (descending)
        self.waiting_queue.sort(key=lambda x: x[1], reverse=True)
        print(f"[Digital Twin] Patient {patient_id} admitted to waiting queue (risk: {risk_score})")
    
    def assign_bed(self, patient_id: int, bed_type: str) -> Optional[str]:
        """Assign a patient to a specific bed type. Returns bed_id if successful."""
        available_beds = self.get_available_beds()
        
        if bed_type not in available_beds or not available_beds[bed_type]:
            print(f"[Digital Twin] No {bed_type} beds available for patient {patient_id}")
            return None
        
        bed_id = available_beds[bed_type][0]
        self.beds[bed_id].occupied_by = patient_id
        
        # Remove from waiting queue if present
        self.waiting_queue = [(pid, risk) for pid, risk in self.waiting_queue if pid != patient_id]
        
        print(f"[Digital Twin] Patient {patient_id} assigned to {bed_id}")
        return bed_id
    
    def get_occupancy(self) -> Dict[str, int]:
        """Get current occupancy count by bed type."""
        occupancy = {"icu": 0, "monitored": 0, "general": 0}
        
        for bed in self.beds.values():
            if bed.occupied_by is not None:
                occupancy[bed.bed_type] += 1
        
        return occupancy
    
    def get_available_beds(self) -> Dict[str, List[str]]:
        """Get available beds by type."""
        available = {"icu": [], "monitored": [], "general": []}
        
        for bed_id, bed in self.beds.items():
            if bed.occupied_by is None:
                available[bed.bed_type].append(bed_id)
        
        return available
    
    def find_best_allocation(self, patient_id: int, risk_score: float) -> Dict:
        """Find the best available bed for a patient based on risk."""
        available = self.get_available_beds()
        
        # High risk patients need ICU or monitored
        if risk_score > 0.7:
            if available["icu"]:
                return {"bed_type": "icu", "bed_id": available["icu"][0], "priority": "high"}
            elif available["monitored"]:
                return {"bed_type": "monitored", "bed_id": available["monitored"][0], "priority": "high"}
            else:
                return {"bed_type": None, "bed_id": None, "priority": "high", "message": "No appropriate beds available"}
        
        # Medium risk patients need monitored or general
        elif risk_score > 0.4:
            if available["monitored"]:
                return {"bed_type": "monitored", "bed_id": available["monitored"][0], "priority": "medium"}
            elif available["general"]:
                return {"bed_type": "general", "bed_id": available["general"][0], "priority": "medium"}
            else:
                return {"bed_type": None, "bed_id": None, "priority": "medium", "message": "No appropriate beds available"}
        
        # Low risk patients can go to general
        else:
            if available["general"]:
                return {"bed_type": "general", "bed_id": available["general"][0], "priority": "low"}
            else:
                return {"bed_type": None, "bed_id": None, "priority": "low", "message": "No general beds available"}
    
    def discharge_patient(self, patient_id: int) -> Optional[str]:
        """Discharge a patient and free their bed."""
        for bed_id, bed in self.beds.items():
            if bed.occupied_by == patient_id:
                bed.occupied_by = None
                print(f"[Digital Twin] Patient {patient_id} discharged from {bed_id}")
                return bed_id
        return None
    
    def get_status(self) -> Dict:
        """Get full ED status."""
        return {
            "occupancy": self.get_occupancy(),
            "available": self.get_available_beds(),
            "waiting_queue": [{"patient_id": pid, "risk_score": risk} for pid, risk in self.waiting_queue],
            "total_beds": len(self.beds)
        }
