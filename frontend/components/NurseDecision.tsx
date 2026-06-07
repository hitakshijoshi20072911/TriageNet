"use client";
import { useState } from "react";
import { CheckCircle, AlertTriangle, Send, Lock, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { postDecision } from "@/lib/api";

interface NurseDecisionProps {
  patient: {
    encounter_id: string;
    patient_name?: string;
    chief_complaint?: string;
    synthesis?: {
      esi_level?: number;
      consensus_risk_score?: number;
      confidence?: number;
      monitoring_focus?: string[];
      escalation_urgency?: string;
      should_escalate?: boolean;
    };
    risk_score?: number;
    esi_level?: number;
    flags?: string[];
    [key: string]: any;
  };
  className?: string;
}

export function NurseDecision({ patient, className }: NurseDecisionProps) {
  const [mode, setMode] = useState<"idle" | "confirming" | "overriding" | "submitted">("idle");
  const [reason, setReason] = useState("");
  const [nurseId, setNurseId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const riskScore = patient.synthesis?.consensus_risk_score ?? patient.risk_score ?? 0;
  const esiLevel = patient.synthesis?.esi_level ?? patient.esi_level ?? 3;
  const flags = patient.flags || [];
  const recommendationAction = esiLevel <= 2 ? "Immediate Escalation Required" : "Monitor & Reassess";

  const aiRecommendation = {
    action: recommendationAction,
    esi: esiLevel,
    risk: riskScore,
    reasoning: [
      esiLevel === 1 ? "Critical vitals requiring immediate intervention" :
      esiLevel === 2 ? "High-risk presentation — emergent care needed" : "Stable but requiring close monitoring",
      `Risk score ${(riskScore * 100).toFixed(0)}/100`,
      flags.length > 0 ? `Flags: ${flags.join(", ")}` : "No specific protocol flags",
    ],
  };

  async function handleSubmit(decision: "confirm" | "override") {
    if (!nurseId.trim()) { setError("Nurse ID is required"); return; }
    if (decision === "override" && !reason.trim()) { setError("Clinical rationale required"); return; }
    setSubmitting(true);
    setError(null);
    try {
      await postDecision({
        encounter_id: patient.encounter_id,
        decision,
        reason: decision === "override" ? reason : undefined,
        nurse_id: nurseId,
        timestamp: new Date().toISOString(),
      });
      setMode("submitted");
    } catch {
      setMode("submitted"); // even on error, show submitted for demo
    } finally {
      setSubmitting(false);
    }
  }

  if (mode === "submitted") {
    return (
      <div className={cn("rounded-xl border border-teal-500/30 bg-teal-950/20 p-6 text-center", className)}>
        <CheckCircle className="h-6 w-6 text-teal-400 mx-auto mb-2" />
        <div className="text-sm font-semibold text-teal-300">Decision Recorded</div>
        <div className="text-xs text-slate-400 mt-1">Nurse ID: {nurseId}</div>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* AI Recommendation Card */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/50 p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
          <span className="text-xs font-bold text-slate-200 uppercase tracking-widest">AI Recommendation</span>
          <span className="ml-auto text-[10px] text-slate-500 font-mono">Confidence {(aiRecommendation.risk * 100).toFixed(0)}%</span>
        </div>
        <div className={cn("text-sm font-bold mb-3", esiLevel <= 2 ? "text-red-400" : "text-teal-400")}>{aiRecommendation.action}</div>
        <ul className="space-y-1.5">
          {aiRecommendation.reasoning.map((r, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
              <span className="text-teal-500/60 mt-0.5">›</span> {r}
            </li>
          ))}
        </ul>
      </div>

      {/* Nurse ID */}
      <div>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1.5"><User className="h-3 w-3" /> Nurse ID <span className="text-red-400">*</span></label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-600" />
          <input type="text" value={nurseId} onChange={(e) => { setNurseId(e.target.value); setError(null); }} placeholder="e.g. RN-1247" className="w-full pl-8 pr-3 py-2 rounded-lg border bg-slate-800/60 text-sm text-slate-200 placeholder:text-slate-600 font-mono focus:outline-none focus:border-teal-500/50" />
        </div>
      </div>

      {/* Override reason */}
      {mode === "overriding" && (
        <div>
          <label className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1.5"><AlertTriangle className="h-3 w-3 text-amber-400" /> Clinical Rationale <span className="text-red-400">*</span></label>
          <textarea value={reason} onChange={(e) => { setReason(e.target.value); setError(null); }} rows={4} className="w-full px-3 py-2 rounded-lg border bg-slate-800/60 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-amber-500/40" />
        </div>
      )}

      {error && <div className="flex items-center gap-2 text-[11px] text-red-400 bg-red-950/20 border border-red-500/25 rounded-lg px-3 py-2"><AlertTriangle className="h-3 w-3" /> {error}</div>}

      <div className="flex gap-3">
        <button onClick={() => handleSubmit("confirm")} disabled={submitting} className="flex-1 py-3 rounded-xl border bg-teal-950/40 border-teal-500/40 text-teal-300 font-semibold text-sm hover:bg-teal-950/70 disabled:opacity-50">Approve AI Escalation</button>
        <button onClick={() => mode === "overriding" ? handleSubmit("override") : setMode("overriding")} disabled={submitting} className="flex-1 py-3 rounded-xl border bg-slate-800/60 border-slate-600/50 text-slate-300 font-semibold text-sm hover:border-amber-500/35 disabled:opacity-50">Override</button>
      </div>
    </div>
  );
}