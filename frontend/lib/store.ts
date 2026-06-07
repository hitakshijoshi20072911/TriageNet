"use client";
import { create } from "zustand";
import type { Patient, AgentMessage, Bed, EDStats, ESILevel } from "./types";
import { MOCK_BEDS } from "./mockData";
import { getPatients } from "./api";

interface AppState {
  darkMode: boolean;
  colorBlindMode: boolean;
  patients: Patient[];
  selectedPatient: string | null;
  agentMessages: AgentMessage[];
  beds: Bed[];
  edStats: EDStats | null;
  wsConnected: boolean;
  setDarkMode: (v: boolean) => void;
  setColorBlindMode: (v: boolean) => void;
  setPatients: (p: Patient[]) => void;
  addAgentMessage: (m: AgentMessage) => void;
  updatePatientRisk: (id: string, score: number, esi: ESILevel) => void;
  reorderPatients: (ids: string[]) => void;
  setWsConnected: (v: boolean) => void;
  fetchPatients: () => Promise<void>;
}

export const useStore = create<AppState>((set, get) => ({
  darkMode: true,
  colorBlindMode: false,
  patients: [],
  selectedPatient: null,
  agentMessages: [],
  beds: MOCK_BEDS,
  edStats: null,
  wsConnected: false,
  setDarkMode: (v) => {
    set({ darkMode: v });
    if (typeof document !== "undefined") document.documentElement.setAttribute("data-theme", v ? "dark" : "light");
  },
  setColorBlindMode: (v) => {
    set({ colorBlindMode: v });
    if (typeof document !== "undefined") document.documentElement.setAttribute("data-accessibility", v ? "colorblind" : "standard");
  },
  setPatients: (patients) => set({ patients }),
  addAgentMessage: (msg) => set((s) => ({ agentMessages: [...s.agentMessages.slice(-150), msg] })),
  updatePatientRisk: (id, score, esi) => set((s) => ({
    patients: s.patients.map((p) => p.id === id ? { ...p, risk_score: score, esi_level: esi } : p),
  })),
  reorderPatients: (ids) => set((s) => {
    const map = new Map(s.patients.map((p) => [p.id, p]));
    return { patients: ids.map((id) => map.get(id)!) };
  }),
  setWsConnected: (v) => set({ wsConnected: v }),
  fetchPatients: async () => {
    try {
      const backendPatients = await getPatients();
      // Map backend patient to the frontend Patient type
      const mapped: Patient[] = backendPatients.map((p: any) => ({
        id: p.encounter_id,                     // use encounter_id as id
        mrn: p.patient_mrn,
        name: p.patient_name || p.patient_mrn,
        age: p.patient_age ?? 0,
        gender: p.patient_sex || "unknown",
        chief_complaint: p.chief_complaint || "",
        arrival_time: p.arrival_time,
        esi_level: p.esi_level || 3,
        risk_score: p.risk_score ? p.risk_score * 100 : 0,  // backend uses 0-1, frontend uses 0-100
        bed_id: undefined,
        monitoring: p.monitoring_active,
        vitals_latest: {},  // we'll populate from langgraph_state if available, otherwise empty
        vitals_trend: [],
        flags: [],
      }));
      // Assign the first 4 patients to beds (ICU / monitored)
      const updatedBeds = MOCK_BEDS.map((bed: Bed, index: number) => {
        if (index < mapped.length) {
          return { ...bed, status: "occupied" as const, patient_id: mapped[index].id, acuity: mapped[index].esi_level || 1 };
        }
        return { ...bed, status: "empty" as const, patient_id: undefined };
      });
      set({ patients: mapped, beds: updatedBeds });
    } catch (err) {
      console.error("Failed to fetch patients", err);
    }
  },
}));