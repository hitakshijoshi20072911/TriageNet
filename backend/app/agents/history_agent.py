"""
History Synthesis Agent

Parses FHIR R4 bundles to extract:
  - Active conditions and comorbidity burden
  - Current medications and high-risk drug flags
  - Allergies and adverse reactions
  - Recent observations (labs, previous vitals)
  - High-risk clinical flags (anticoagulated, immunocompromised, etc.)

Returns an AgentOutput with a baseline comorbidity risk score and flags
that the debate node will use to contextualise the vitals findings.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.agents.state import AgentOutput, TriageState

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# High-risk flag definitions
# ─────────────────────────────────────────────────────────────────────────────

# Condition SNOMED/ICD keywords → flag name
HIGH_RISK_CONDITIONS: Dict[str, str] = {
    "anticoagul": "ANTICOAGULATED",
    "warfarin":   "ANTICOAGULATED",
    "apixaban":   "ANTICOAGULATED",
    "rivaroxaban":"ANTICOAGULATED",
    "immunocomp": "IMMUNOCOMPROMISED",
    "transplant": "IMMUNOCOMPROMISED",
    "chemotherapy":"ACTIVE_MALIGNANCY",
    "malignancy": "ACTIVE_MALIGNANCY",
    "cancer":     "ACTIVE_MALIGNANCY",
    "cirrhosis":  "CIRRHOSIS",
    "renal fail": "CHRONIC_KIDNEY_DISEASE",
    "ckd":        "CHRONIC_KIDNEY_DISEASE",
    "dialysis":   "CHRONIC_KIDNEY_DISEASE",
    "heart fail": "CONGESTIVE_HEART_FAILURE",
    "chf":        "CONGESTIVE_HEART_FAILURE",
    "copd":       "CHRONIC_LUNG_DISEASE",
    "diabetes":   "DIABETES",
    "insulin":    "DIABETES",
    "steroid":    "STEROID_DEPENDENT",
    "prednisolon":"STEROID_DEPENDENT",
    "hiv":        "IMMUNOCOMPROMISED",
    "aids":       "IMMUNOCOMPROMISED",
    "pneumonia":  "RECENT_RESPIRATORY_ILLNESS",
    "surgery":    "RECENT_SURGERY",
    "pacemaker":  "CARDIAC_DEVICE",
    "icd":        "CARDIAC_DEVICE",
}

# Risk weights per flag (added to baseline)
FLAG_RISK_WEIGHTS: Dict[str, float] = {
    "ANTICOAGULATED":          0.15,
    "IMMUNOCOMPROMISED":       0.18,
    "ACTIVE_MALIGNANCY":       0.12,
    "CIRRHOSIS":               0.14,
    "CHRONIC_KIDNEY_DISEASE":  0.10,
    "CONGESTIVE_HEART_FAILURE":0.16,
    "CHRONIC_LUNG_DISEASE":    0.10,
    "DIABETES":                0.05,
    "STEROID_DEPENDENT":       0.08,
    "RECENT_RESPIRATORY_ILLNESS":0.10,
    "RECENT_SURGERY":          0.12,
    "CARDIAC_DEVICE":          0.06,
}


# ─────────────────────────────────────────────────────────────────────────────
# FHIR parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_conditions(bundle: Dict[str, Any]) -> List[str]:
    conditions = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Condition":
            code = resource.get("code", {})
            text = code.get("text", "")
            coding = code.get("coding", [{}])
            display = coding[0].get("display", "") if coding else ""
            conditions.append((text or display).lower())
    return [c for c in conditions if c]


def _extract_medications(bundle: Dict[str, Any]) -> List[str]:
    meds = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType", "")
        if rtype in ("MedicationRequest", "MedicationStatement"):
            med = resource.get("medicationCodeableConcept", {})
            text = med.get("text", "")
            coding = med.get("coding", [{}])
            display = coding[0].get("display", "") if coding else ""
            meds.append((text or display).lower())
    return [m for m in meds if m]


def _extract_allergies(bundle: Dict[str, Any]) -> List[str]:
    allergies = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "AllergyIntolerance":
            code = resource.get("code", {})
            text = code.get("text", code.get("coding", [{}])[0].get("display", "Unknown"))
            severity = resource.get("reaction", [{}])[0].get("severity", "unknown")
            allergies.append(f"{text} ({severity})")
    return allergies


def _extract_patient_demographics(bundle: Dict[str, Any]) -> Dict[str, Any]:
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            from datetime import datetime
            birth_str = resource.get("birthDate", "")
            age = None
            if birth_str:
                try:
                    birth = datetime.strptime(birth_str, "%Y-%m-%d")
                    age = (datetime.now() - birth).days // 365
                except Exception:
                    pass
            return {
                "age": age,
                "sex": resource.get("gender", "unknown"),
                "name": resource.get("name", [{}])[0].get("text", "Unknown"),
            }
    return {}


def _flag_high_risk(conditions: List[str], medications: List[str]) -> List[str]:
    flags = set()
    combined = conditions + medications
    for text in combined:
        for keyword, flag in HIGH_RISK_CONDITIONS.items():
            if keyword in text:
                flags.add(flag)
    return list(flags)


def _compute_baseline_risk(age: Optional[int], flags: List[str]) -> float:
    """
    Baseline comorbidity risk before considering current vitals.
    Age > 65 adds 0.05; each flag adds its weight.
    """
    risk = 0.05  # baseline
    if age and age >= 65:
        risk += 0.05
    if age and age >= 75:
        risk += 0.05
    for flag in flags:
        risk += FLAG_RISK_WEIGHTS.get(flag, 0.03)
    return round(min(risk, 0.9), 3)


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph node
# ─────────────────────────────────────────────────────────────────────────────

def history_synthesis_agent(state: TriageState) -> TriageState:
    """
    LangGraph node — parses FHIR bundle and writes structured history
    analysis into state["agent_outputs"]["history"].
    """
    patient_id = state.get("patient_id", "unknown")
    fhir_bundle = state.get("fhir_bundle") or {}

    logger.info(f"[HistoryAgent] Processing FHIR bundle for {patient_id}")

    # No FHIR data available
    if not fhir_bundle:
        output = AgentOutput(
            agent_name="history",
            risk_score=0.05,
            confidence=0.2,
            findings=["No FHIR / EHR data available — history unknown"],
            recommendation="Obtain full medication list and past medical history from patient or family",
            data_quality=0.0,
            flags=["NO_HISTORY_AVAILABLE"],
        )
        return _merge(state, "history", output)

    # Parse FHIR
    demographics = _extract_patient_demographics(fhir_bundle)
    conditions   = _extract_conditions(fhir_bundle)
    medications  = _extract_medications(fhir_bundle)
    allergies    = _extract_allergies(fhir_bundle)

    # Flag analysis
    flags = _flag_high_risk(conditions, medications)

    age = demographics.get("age")
    baseline_risk = _compute_baseline_risk(age, flags)

    # Data quality
    completeness_score = min(
        (len(conditions) > 0) * 0.35
        + (len(medications) > 0) * 0.35
        + (len(allergies) >= 0) * 0.15  # documented "no known allergies" counts
        + (age is not None) * 0.15,
        1.0,
    )

    # Findings
    findings = []
    if demographics:
        findings.append(
            f"Patient: {demographics.get('name', 'Unknown')}, "
            f"Age: {age or 'Unknown'}, Sex: {demographics.get('sex', 'unknown')}"
        )

    if conditions:
        findings.append(f"Active conditions ({len(conditions)}): {', '.join(conditions[:5])}"
                        + (f" +{len(conditions)-5} more" if len(conditions) > 5 else ""))
    else:
        findings.append("No documented conditions in FHIR bundle")

    if medications:
        findings.append(f"Current medications ({len(medications)}): {', '.join(medications[:5])}"
                        + (f" +{len(medications)-5} more" if len(medications) > 5 else ""))

    if allergies:
        findings.append(f"Allergies: {', '.join(allergies)}")
    else:
        findings.append("No known allergies documented")

    if flags:
        findings.append(f"⚠️  High-risk flags: {', '.join(flags)}")

    # Recommendation
    if "ANTICOAGULATED" in flags:
        recommendation = "⚠️ ANTICOAGULATED patient — extra caution with any invasive procedure; assess bleeding risk"
    elif "IMMUNOCOMPROMISED" in flags:
        recommendation = "⚠️ IMMUNOCOMPROMISED — low threshold for sepsis workup; isolate if respiratory symptoms"
    elif "CONGESTIVE_HEART_FAILURE" in flags and "ANTICOAGULATED" in flags:
        recommendation = "⚠️ CHF + ANTICOAGULATED — reassess cardiac status; telemetry recommended"
    elif baseline_risk >= 0.4:
        recommendation = "HIGH comorbidity burden — lower threshold for escalation and senior clinician review"
    elif baseline_risk >= 0.2:
        recommendation = "MODERATE comorbidity burden — standard monitoring with flag awareness"
    else:
        recommendation = "LOW comorbidity burden — proceed with standard triage protocol"

    output = AgentOutput(
        agent_name="history",
        risk_score=baseline_risk,
        confidence=max(completeness_score, 0.1),
        findings=findings,
        recommendation=recommendation,
        data_quality=completeness_score,
        flags=flags,
        supporting_evidence={
            "demographics": demographics,
            "conditions": conditions,
            "medications": medications,
            "allergies": allergies,
            "high_risk_flags": flags,
            "baseline_risk": baseline_risk,
            "data_completeness": completeness_score,
        },
    )

    return _merge(state, "history", output)


def _merge(state: TriageState, agent_name: str, output: AgentOutput) -> TriageState:
    agent_outputs = dict(state.get("agent_outputs") or {})
    agent_outputs[agent_name] = output.model_dump()
    completed = list(state.get("agents_completed") or [])
    if agent_name not in completed:
        completed.append(agent_name)
    return {**state, "agent_outputs": agent_outputs, "agents_completed": completed}