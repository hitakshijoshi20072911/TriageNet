"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { postIntake } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function PatientIntake() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("Jane Smith");
  const [age, setAge] = useState("67");
  const [complaint, setComplaint] = useState("Shortness of breath and confusion");
  const [gender, setGender] = useState<"female" | "male">("female");
  const [vitals, setVitals] = useState({
    heart_rate: 102,
    systolic_bp: 110,
    diastolic_bp: 78,
    resp_rate: 22,
    spO2: 93,
    temperature: 37.8,
    consciousness: "A",
  });

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await postIntake({
        patient_mrn: `MRN-${Date.now()}`,
        patient_name: name,
        patient_age: parseInt(age),
        patient_sex: gender,
        chief_complaint: complaint,
        initial_vitals: vitals,
        vitals_profile: "deteriorating_sepsis",
      });
      console.log("Intake result:", res.data);
      router.push(`/patient/${res.data.encounter_id}`);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-lg mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>New Patient Intake</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <input className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <div className="flex gap-2">
            <input className="w-1/2 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" placeholder="Age" value={age} onChange={(e) => setAge(e.target.value)} />
            <select className="w-1/2 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" value={gender} onChange={(e) => setGender(e.target.value as any)}>
              <option value="female">Female</option>
              <option value="male">Male</option>
            </select>
          </div>
          <textarea className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" placeholder="Chief Complaint" rows={2} value={complaint} onChange={(e) => setComplaint(e.target.value)} />
          <Button onClick={handleSubmit} disabled={loading} className="w-full">
            {loading ? "Running Triage..." : "Admit Patient"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}