import { Activity, Database, Layers, Users, ShieldCheck, Clock } from "lucide-react";

export default function HowItWorks() {
  return (
    <div className="max-w-4xl mx-auto py-12 px-4 text-slate-200">
      <h1 className="text-3xl font-bold mb-2">How TriageNet Works</h1>
      <p className="text-slate-400 mb-10">
        An AI‑powered emergency department assistant that never sleeps.
      </p>

      <div className="grid gap-8 md:grid-cols-2">
        <Step icon={<Activity className="h-8 w-8 text-teal-400" />} title="1. Patient Arrives" description="Nurse enters patient info and initial vitals. TriageNet instantly streams the data to its agent swarm." />
        <Step icon={<Database className="h-8 w-8 text-emerald-400" />} title="2. History Agent" description="FHIR‑compatible health records are scanned for high‑risk flags: allergies, medications, chronic conditions." />
        <Step icon={<Layers className="h-8 w-8 text-blue-400" />} title="3. Vitals & Context Agents" description="Modified Early Warning Score (MEWS) and CUSUM trend analysis detect subtle deterioration. Department load and shift changes are factored in." />
        <Step icon={<Users className="h-8 w-8 text-amber-400" />} title="4. Structured Debate" description="All three specialist agents present their findings. TriageNet moderates a multi‑round debate, resolves conflicts, and produces a unified ESI level." />
        <Step icon={<ShieldCheck className="h-8 w-8 text-teal-400" />} title="5. Human‑in‑the‑Loop" description="The nurse sees the recommendation with full evidence. They can confirm or override — ensuring AI augments, not replaces, clinical judgment." />
        <Step icon={<Clock className="h-8 w-8 text-purple-400" />} title="6. Continuous Monitoring" description="Every patient is re‑evaluated every few minutes. If vitals begin to deteriorate, TriageNet escalates automatically — long before a human might notice." />
      </div>
    </div>
  );
}

function Step({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="bg-slate-900/60 border border-slate-800/60 rounded-xl p-6 backdrop-blur">
      <div className="flex items-center gap-4 mb-3">
        {icon}
        <h3 className="text-lg font-semibold">{title}</h3>
      </div>
      <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
    </div>
  );
}
