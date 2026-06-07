"use client";
import { useEffect } from "react";
import { BedMap } from "@/components/BedMap";
import { PatientQueue } from "@/components/PatientQueue";
import { AgentFeed } from "@/components/AgentFeed";
import { useMockTelemetry } from "@/hooks/useWebSocket";
import { useStore } from "@/lib/store";

export default function Dashboard() {
  const fetchPatients = useStore((s) => s.fetchPatients);
  useMockTelemetry();

  useEffect(() => {
    fetchPatients();       // load real patients from backend
  }, [fetchPatients]);

  return (
    <div className="grid grid-cols-12 gap-4 h-[calc(100vh-5rem)]">
      <div className="col-span-3 overflow-y-auto pr-1">
        <BedMap />
      </div>
      <div className="col-span-6 overflow-y-auto pr-1">
        <PatientQueue />
      </div>
      <div className="col-span-3 overflow-y-auto">
        <AgentFeed />
      </div>
    </div>
  );
}