"use client";

import React, { useState, useMemo } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragStartEvent,
  DragOverlay,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  GripVertical,
  AlertTriangle,
  Activity,
  Clock,
  ChevronRight,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { cn, formatMRN, formatDuration, getRiskTextColor, getRiskBgColor } from "@/lib/utils";
import { ESIBadge } from "./ESIBadge";
import { Sparkline } from "./Sparkline";
import { useStore } from "@/lib/store";
import type { Patient } from "@/lib/types";

// ─── Individual Patient Card ──────────────────────────────────

interface PatientCardProps {
  patient: Patient;
  isDragOverlay?: boolean;
}

function PatientCard({ patient: p, isDragOverlay }: PatientCardProps) {
  const router = useRouter();
  const riskText = getRiskTextColor(p.risk_score);
  const riskBg   = getRiskBgColor(p.risk_score);
  const isAlert  = p.esi_level <= 2 && p.risk_score >= 70;

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: p.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const cardClasses = cn(
    "group relative rounded-xl border transition-all duration-300 cursor-pointer",
    "bg-slate-900/60 backdrop-blur-md",
    // Left border accent
    p.esi_level === 1 && "border-l-2 border-l-red-500",
    p.esi_level === 2 && "border-l-2 border-l-amber-500",
    p.esi_level === 3 && "border-l-2 border-l-yellow-500",
    p.esi_level >= 4 && "border-l-2 border-l-emerald-500",
    // Glow for critical
    isAlert && "animate-alert-glow",
    // Drag states
    isDragging && "opacity-40",
    isDragOverlay && "rotate-1 scale-[1.02] shadow-2xl ring-2 ring-teal-500/40",
    // Hover
    !isDragging && "hover:border-slate-700/60 hover:bg-slate-900/80"
  );

  const sparkColor =
    p.esi_level === 1 ? "#EF4444" :
    p.esi_level === 2 ? "#F59E0B" :
    p.esi_level === 3 ? "#EAB308" : "#10B981";

  return (
    <div ref={setNodeRef} style={style} className={cardClasses}>
      <div className="p-3">
        {/* Header Row */}
        <div className="flex items-start gap-2 mb-2">
          {/* Drag Handle */}
          <button
            {...listeners}
            {...attributes}
            className="mt-0.5 p-1 -ml-1 rounded text-slate-600 hover:text-slate-400 cursor-grab active:cursor-grabbing touch-none"
            aria-label="Drag to reorder"
            tabIndex={-1}
          >
            <GripVertical className="h-3.5 w-3.5" />
          </button>

          {/* Patient Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <ESIBadge level={p.esi_level} size="sm" pulse={isAlert} />
              {p.flags.length > 0 && (
                <span className="flex items-center gap-1 text-[10px] font-mono text-orange-400/80">
                  <AlertTriangle className="h-2.5 w-2.5" />
                  {p.flags.length} flag{p.flags.length > 1 ? "s" : ""}
                </span>
              )}
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-[10px] font-mono text-slate-500 tracking-wider">
                {formatMRN(p.mrn)}
              </span>
              <span className="text-xs font-semibold text-slate-200 truncate">
                {p.name}
              </span>
              <span className="text-[10px] text-slate-500">
                {p.age}y {p.gender}
              </span>
            </div>
          </div>

          {/* Risk Score */}
          <div
            className="flex flex-col items-end gap-0.5 cursor-pointer"
            onClick={() => router.push(`/patient/${p.id}`)}
          >
            <div className={cn("font-mono font-bold text-lg leading-none", riskText)}>
              {p.risk_score}
            </div>
            <div className="text-[9px] text-slate-500 uppercase tracking-wider">
              Risk
            </div>
          </div>
        </div>

        {/* Chief Complaint */}
        <p className="text-[11px] text-slate-400 line-clamp-1 mb-2.5 pl-5 leading-relaxed">
          {p.chief_complaint}
        </p>

        {/* Vitals Row */}
        <div className="flex items-center gap-2 pl-5 mb-2.5">
          <div className="flex items-center gap-1 bg-slate-800/60 px-1.5 py-0.5 rounded text-[10px] font-mono">
            <Activity className="h-2.5 w-2.5 text-teal-400" />
            <span className="text-slate-300">{p.vitals_latest.heart_rate}</span>
            <span className="text-slate-600">bpm</span>
          </div>
          <div className="flex items-center gap-1 bg-slate-800/60 px-1.5 py-0.5 rounded text-[10px] font-mono">
            <span className="text-blue-400">SpO₂</span>
            <span className={cn(p.vitals_latest.spO2 < 94 ? "text-red-400" : "text-slate-300")}>
              {p.vitals_latest.spO2}%
            </span>
          </div>
          <div className="flex items-center gap-1 ml-auto text-[10px] text-slate-500">
            <Clock className="h-2.5 w-2.5" />
            {formatDuration(p.arrival_time)}
          </div>
        </div>

        {/* Sparklines & Risk Bar */}
        <div className="flex gap-3 pl-5">
          <div>
            <div className="text-[9px] text-slate-600 mb-0.5 font-mono">HR</div>
            <Sparkline
              data={p.vitals_trend}
              metric="heart_rate"
              width={72}
              height={20}
              color={sparkColor}
              showDot
            />
          </div>
          <div>
            <div className="text-[9px] text-slate-600 mb-0.5 font-mono">SpO₂</div>
            <Sparkline
              data={p.vitals_trend}
              metric="spO2"
              width={72}
              height={20}
              color={p.vitals_latest.spO2 < 94 ? "#EF4444" : "#3B82F6"}
              showDot
            />
          </div>

          {/* Risk Score Bar */}
          <div className="ml-auto flex flex-col justify-end">
            <div className="text-[9px] text-slate-600 mb-0.5 font-mono text-right">Score</div>
            <div className="w-16 h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={cn("h-full rounded-full transition-all duration-500", riskBg)}
                style={{ width: `${p.risk_score}%` }}
              />
            </div>
          </div>
        </div>

        {/* Deep‑dive link */}
        <button
          onClick={() => router.push(`/patient/${p.id}`)}
          className="absolute right-2.5 bottom-2.5 flex items-center gap-0.5 text-[10px] text-slate-600 hover:text-teal-400 transition-colors opacity-0 group-hover:opacity-100"
        >
          Detail <ChevronRight className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

// ─── Full Queue ───────────────────────────────────────────────

export function PatientQueue() {
  const { patients, reorderPatients } = useStore();
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  const sortedPatients = useMemo(
    () => [...patients].sort((a, b) => b.risk_score - a.risk_score),
    [patients]
  );

  const activePatient = activeId
    ? sortedPatients.find((p) => p.id === activeId)
    : null;

  function handleDragStart(ev: DragStartEvent) {
    setActiveId(ev.active.id as string);
  }

  function handleDragEnd(ev: DragEndEvent) {
    setActiveId(null);
    const { active, over } = ev;
    if (!over || active.id === over.id) return;

    const oldIndex = sortedPatients.findIndex((p) => p.id === active.id);
    const newIndex = sortedPatients.findIndex((p) => p.id === over.id);
    const reordered = arrayMove(sortedPatients, oldIndex, newIndex);
    reorderPatients(reordered.map((p) => p.id));
  }

  const criticalCount = sortedPatients.filter((p) => p.esi_level <= 2).length;

  return (
    <div className="flex flex-col h-full">
      {/* Queue Header */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <div>
          <h2 className="text-xs font-bold text-slate-200 uppercase tracking-widest">
            Patient Queue
          </h2>
          <p className="text-[10px] text-slate-500 mt-0.5">
            {sortedPatients.length} active · {criticalCount} critical · drag to reprioritize
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
          <span className="text-[10px] text-teal-400 font-mono">LIVE</span>
        </div>
      </div>

      {/* Scrollable list */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 scrollbar-thin">
        {sortedPatients.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 py-12">
            <AlertTriangle className="h-8 w-8 mb-2 opacity-50" />
            <p className="text-sm">No active patients</p>
            <p className="text-xs mt-1">Use Patient Intake to add patients</p>
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={sortedPatients.map((p) => p.id)}
              strategy={verticalListSortingStrategy}
            >
              {sortedPatients.map((p) => (
                <div key={p.id} className="animate-fade-in">
                  <PatientCard patient={p} />
                </div>
              ))}
            </SortableContext>

            <DragOverlay dropAnimation={null}>
              {activePatient ? (
                <PatientCard patient={activePatient} isDragOverlay />
              ) : null}
            </DragOverlay>
          </DndContext>
        )}
      </div>
    </div>
  );
}