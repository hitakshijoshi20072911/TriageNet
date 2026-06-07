import random
from typing import Dict
from app.digital_twin.twin import EmergencyDepartment


def run_allocation_simulation(
    ed_state: EmergencyDepartment,
    patient_id: int,
    risk_score: float,
    num_simulations: int = 10
) -> Dict:
    """
    Run Monte Carlo-like simulation to estimate risk for different bed allocations.
    Returns the safest allocation choice.
    """
    available = ed_state.get_available_beds()
    results = {}
    
    # Simulate each bed type
    for bed_type in ["icu", "monitored", "general"]:
        if available[bed_type]:
            # Run simulations for this bed type
            simulated_risks = []
            
            for _ in range(num_simulations):
                # Simulate risk adjustment based on bed type
                # ICU reduces risk by 40%, monitored by 20%, general by 0%
                risk_reduction = {
                    "icu": 0.4,
                    "monitored": 0.2,
                    "general": 0.0
                }[bed_type]
                
                # Add some random variation (±10%)
                variation = random.uniform(-0.1, 0.1)
                adjusted_risk = risk_score * (1 - risk_reduction + variation)
                simulated_risks.append(max(0, min(1, adjusted_risk)))
            
            # Calculate average risk for this bed type
            avg_risk = sum(simulated_risks) / len(simulated_risks)
            results[bed_type] = {
                "average_risk": avg_risk,
                "simulations": num_simulations,
                "risk_reduction": risk_reduction
            }
    
    # Find the safest option (lowest average risk)
    if results:
        safest = min(results.items(), key=lambda x: x[1]["average_risk"])
        return {
            "recommended_bed_type": safest[0],
            "expected_risk": safest[1]["average_risk"],
            "risk_reduction": safest[1]["risk_reduction"],
            "all_simulations": results,
            "confidence": 0.85  # Mock confidence score
        }
    else:
        return {
            "recommended_bed_type": None,
            "expected_risk": risk_score,
            "risk_reduction": 0.0,
            "all_simulations": {},
            "confidence": 0.0,
            "message": "No beds available for simulation"
        }
