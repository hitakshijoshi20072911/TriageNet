import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

// Patients
export const postIntake = (payload: any) =>
  api.post("/api/v1/intake", payload);

export const getPatients = async () => {
  const res = await api.get("/api/v1/");
  return res.data; // already an array
};

export const getPatient = async (id: string) => {
  const res = await api.get(`/api/v1/${id}`);
  return res.data;
};

// HITL
export const postDecision = (payload: any) =>
  api.post("/api/v1/decision", payload);

export const getPendingDecisions = async (): Promise<any[]> => {
  // This endpoint doesn't exist yet - return empty array for now
  return [];
};

// Stats (for the top bar)
export const getEdStats = async () => {
  // We can compute stats from the patient list
  const patients = await getPatients();
  return {
    total_patients: patients.length,
    icu_beds_open: 1, // hard-coded for demo
    monitored_open: 4,
    general_open: 7,
    avg_wait_min: 34,
    critical_count: patients.filter((p: any) => p.esi_level <= 2).length,
    pending_decisions: 0,
  };
};

export default api;