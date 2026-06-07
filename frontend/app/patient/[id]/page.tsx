"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getPatient } from "@/lib/api";
import { VitalsChart } from "@/components/VitalsChart";
import { NurseDecision } from "@/components/NurseDecision";

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const [patient, setPatient] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    getPatient(id)
      .then(setPatient)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-6 text-slate-400">Loading patient data...</div>;
  if (!patient) return <div className="p-6 text-red-400">Patient not found</div>;

  const synthesis = patient.synthesis || {};
  const vitalsStream = patient.langgraph_state?.vitals_stream || [];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{patient.patient_name}</h1>
        <p className="text-slate-400">{patient.chief_complaint}</p>
        <div className="flex gap-4 mt-2">
          <div className="text-sm"><span className="text-slate-500">ESI:</span> <span className="font-bold text-red-400">{synthesis.esi_level}</span></div>
          <div className="text-sm"><span className="text-slate-500">Risk:</span> <span className="font-bold text-red-400">{synthesis.consensus_risk_score?.toFixed(2)}</span></div>
          <div className="text-sm"><span className="text-slate-500">Confidence:</span> {synthesis.confidence?.toFixed(2)}</div>
        </div>
      </div>
      {vitalsStream.length > 0 && <VitalsChart data={vitalsStream} />}
      <NurseDecision patient={{ id: patient.encounter_id, ...patient }} />
      {synthesis.monitoring_focus && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-2">Monitoring Focus</h3>
          <ul className="list-disc list-inside text-xs text-slate-400">
            {synthesis.monitoring_focus.map((f: string) => <li key={f}>{f}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}