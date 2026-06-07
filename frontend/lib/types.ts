export type ESILevel = 1 | 2 | 3 | 4 | 5;

export interface VitalReading {
  timestamp: string;
  heart_rate: number;
  systolic_bp: number;
  diastolic_bp: number;
  resp_rate: number;
  spO2: number;
  temperature: number;
  gcs?: number;
}

export interface Patient {
  id: string;
  mrn: string;
  name: string;
  age: number;
  gender: "M" | "F" | "NB";
  chief_complaint: string;
  arrival_time: string;
  esi_level: ESILevel;
  risk_score: number;
  bed_id?: string;
  monitoring: boolean;
  vitals_latest: VitalReading;
  vitals_trend: VitalReading[];
  flags: string[];
}

export interface Bed {
  id: string;
  number: string;
  zone: "icu" | "monitored" | "general" | "isolation";
  status: "empty" | "occupied" | "cleaning" | "reserved";
  patient_id?: string;
  acuity?: ESILevel;
}

export type AgentType =
  | "vitals"
  | "history"
  | "context"
  | "supervisor"
  | "consensus"
  | "escalation";

export interface AgentMessage {
  id: string;
  agent: AgentType;
  content: string;
  timestamp: string;
  type: "analysis" | "debate" | "consensus" | "alert" | "info";
  confidence?: number;
  patient_id?: string;
}

export interface EDStats {
  total_patients: number;
  icu_beds_open: number;
  monitored_open: number;
  general_open: number;
  avg_wait_min: number;
  critical_count: number;
  pending_decisions: number;
}

export interface IntakePayload {
  name: string;
  mrn: string;
  age: number;
  gender: "M" | "F" | "NB";
  chief_complaint: string;
  initial_vitals: Partial<VitalReading>;
}

export interface HITLDecision {
  patient_id: string;
  decision: "confirm" | "override";
  reason?: string;
  nurse_id?: string;
  timestamp: string;
}