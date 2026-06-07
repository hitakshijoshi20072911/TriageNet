"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import type { Bed, Patient } from "@/lib/types";  // ← import Patient

const ZONE_CONFIG = {
  icu:       { label: "Zone A · Critical ICU",       color: "text-red-400",    border: "border-red-900/50",    dot: "bg-red-500"    },
  monitored: { label: "Zone B · Monitored Tracking",  color: "text-amber-400",  border: "border-amber-900/50",  dot: "bg-amber-500"  },
  general:   { label: "Zone C · General Waiting",     color: "text-teal-400",   border: "border-teal-900/50",   dot: "bg-teal-500"   },
  isolation: { label: "Zone D · Isolation",           color: "text-purple-400", border: "border-purple-900/50", dot: "bg-purple-500" },
};

const BED_STATUS_CONFIG = {
  empty:    { bg: "bg-slate-800/40 hover:bg-slate-800/70", border: "border-slate-700/40 hover:border-teal-500/40" },
  occupied: { bg: "bg-slate-800/70 hover:bg-slate-700/80", border: "border-slate-600/60 hover:border-teal-500/50" },
  cleaning: { bg: "bg-yellow-950/30",                      border: "border-yellow-900/40" },
  reserved: { bg: "bg-teal-950/30",                        border: "border-teal-900/40" },
};

const ESI_BED_COLOR: Record<number, string> = {
  1: "bg-red-500",
  2: "bg-amber-500",
  3: "bg-yellow-500",
  4: "bg-emerald-500",
  5: "bg-blue-500",
};

// ─── Individual Bed Cell ──────────────────────────────────────

function BedCell({ bed, patient }: { bed: Bed; patient?: Patient }) {
  const router = useRouter();
  const statusCfg = BED_STATUS_CONFIG[bed.status];
  const isEmpty   = bed.status === "empty";

  return (
    <button
      onClick={() => {
        if (bed.patient_id) router.push(`/patient/${bed.patient_id}`);
      }}
      disabled={isEmpty || bed.status === "cleaning"}
      className={cn(
        "relative group w-full aspect-square rounded-lg border transition-all duration-200",
        "flex flex-col items-center justify-center gap-0.5 p-1",
        statusCfg.bg,
        statusCfg.border,
        !isEmpty && bed.status !== "cleaning" && "cursor-pointer",
        isEmpty && "cursor-default"
      )}
    >
      {/* Bed number */}
      <span className="text-[10px] font-mono font-bold text-slate-400 leading-none">
        {bed.number}
      </span>

      {/* Acuity dot */}
      {bed.acuity && bed.status === "occupied" && (
        <div className={cn("w-2 h-2 rounded-full", ESI_BED_COLOR[bed.acuity] ?? "bg-slate-500")} />
      )}

      {/* Status indicators */}
      {bed.status === "empty" && <span className="text-[9px] text-slate-700 font-mono">+</span>}
      {bed.status === "cleaning" && <span className="text-[8px] text-yellow-700 font-mono">CLN</span>}
      {bed.status === "reserved" && <span className="text-[8px] text-teal-700 font-mono">RSV</span>}

      {/* Patient HR */}
      {patient && bed.status === "occupied" && (
        <span className="text-[8px] font-mono text-slate-500 leading-none">
          {patient.vitals_latest.heart_rate}
        </span>
      )}

      {/* Tooltip on hover */}
      {!isEmpty && (
        <div className={cn(
          "absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 z-20",
          "bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5",
          "text-[10px] text-slate-300 whitespace-nowrap pointer-events-none",
          "opacity-0 group-hover:opacity-100 transition-opacity duration-150",
          "shadow-xl"
        )}>
          {patient && <div className="font-semibold">{patient.name}</div>}
          {bed.status === "occupied" && bed.acuity && (
            <div className="text-slate-500">ESI {bed.acuity}</div>
          )}
          {bed.status === "cleaning" && <div className="text-yellow-500">Being cleaned</div>}
          {bed.status === "reserved" && <div className="text-teal-500">Reserved for admission</div>}
        </div>
      )}
    </button>
  );
}

// ─── Full Bed Map ─────────────────────────────────────────────

export function BedMap() {
  const beds     = useStore((s) => s.beds);
  const patients = useStore((s) => s.patients);
  const patientMap = new Map(patients.map((p) => [p.id, p]));

  // Group beds by zone
  const bedsByZone = {
    icu:       beds.filter((b) => b.zone === "icu"),
    monitored: beds.filter((b) => b.zone === "monitored"),
    general:   beds.filter((b) => b.zone === "general"),
    isolation: beds.filter((b) => b.zone === "isolation"),
  };

  const stats = {
    icu:       { total: bedsByZone.icu.length,       open: bedsByZone.icu.filter(b => b.status === "empty").length },
    monitored: { total: bedsByZone.monitored.length, open: bedsByZone.monitored.filter(b => b.status === "empty").length },
    general:   { total: bedsByZone.general.length,   open: bedsByZone.general.filter(b => b.status === "empty").length },
    isolation: { total: bedsByZone.isolation.length, open: bedsByZone.isolation.filter(b => b.status === "empty").length },
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <div>
          <h2 className="text-xs font-bold text-slate-200 uppercase tracking-widest">
            ED Bed Map
          </h2>
          <p className="text-[10px] text-slate-500 mt-0.5">
            {beds.filter(b => b.status === "occupied").length}/{beds.length} occupied
          </p>
        </div>
        <div className="text-[10px] text-slate-500 font-mono">
          <span className="text-teal-400">{stats.icu.open + stats.monitored.open}</span> beds open
        </div>
      </div>

      {/* Zones */}
      <div className="flex-1 overflow-y-auto space-y-3 scrollbar-thin">
        {(Object.keys(bedsByZone) as Array<keyof typeof bedsByZone>).map((zone) => {
          const zoneBeds = bedsByZone[zone];
          const cfg      = ZONE_CONFIG[zone];
          const st       = stats[zone];

          return (
            <div
              key={zone}
              className={cn(
                "rounded-lg border p-2.5 transition-all duration-200",
                "bg-slate-900/40",
                cfg.border
              )}
            >
              {/* Zone Header */}
              <div className="flex items-center gap-2 mb-2">
                <div className={cn("w-1.5 h-1.5 rounded-full", cfg.dot)} />
                <span className={cn("text-[10px] font-bold uppercase tracking-wider", cfg.color)}>
                  {cfg.label}
                </span>
                <span className="ml-auto text-[9px] font-mono text-slate-500">
                  <span className={cn(st.open > 0 ? "text-teal-400" : "text-red-400")}>
                    {st.open}
                  </span>/{st.total}
                </span>
              </div>

              {/* Bed Grid */}
              <div className={cn(
                "grid gap-1.5",
                zone === "isolation" ? "grid-cols-2" :
                zone === "icu"       ? "grid-cols-4" :
                                       "grid-cols-5"
              )}>
                {zoneBeds.map((bed) => (
                  <BedCell
                    key={bed.id}
                    bed={bed}
                    patient={bed.patient_id ? patientMap.get(bed.patient_id) : undefined}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-2 pt-2 border-t border-slate-800/50 flex-shrink-0">
        <div className="flex items-center gap-3 flex-wrap">
          {[
            { color: "bg-red-500", label: "ESI 1" },
            { color: "bg-amber-500", label: "ESI 2" },
            { color: "bg-yellow-500", label: "ESI 3" },
            { color: "bg-emerald-500", label: "ESI 4-5" },
            { color: "bg-slate-700", label: "Empty" },
            { color: "bg-yellow-900", label: "Cleaning" },
          ].map(({ color, label }) => (
            <div key={label} className="flex items-center gap-1">
              <div className={cn("w-2 h-2 rounded-sm", color)} />
              <span className="text-[9px] text-slate-500">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}