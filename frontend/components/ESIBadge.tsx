import React from "react";
import { cn } from "@/lib/utils";
import type { ESILevel } from "@/lib/types";

interface ESIBadgeProps {
  level: ESILevel;
  size?: "sm" | "md" | "lg";
  className?: string;
  pulse?: boolean;
}

const ESI_CONFIG = {
  1: {
    label: "ESI 1",
    name: "Resuscitation",
    symbol: "▲",
    bg: "bg-red-950/60",
    border: "border-red-500/50",
    text: "text-red-400",
    dot: "bg-red-500",
    glow: "shadow-[0_0_8px_rgba(239,68,68,0.5)]",
  },
  2: {
    label: "ESI 2",
    name: "Emergent",
    symbol: "■",
    bg: "bg-amber-950/60",
    border: "border-amber-500/50",
    text: "text-amber-400",
    dot: "bg-amber-500",
    glow: "shadow-[0_0_8px_rgba(245,158,11,0.5)]",
  },
  3: {
    label: "ESI 3",
    name: "Urgent",
    symbol: "●",
    bg: "bg-yellow-950/50",
    border: "border-yellow-500/40",
    text: "text-yellow-400",
    dot: "bg-yellow-500",
    glow: "",
  },
  4: {
    label: "ESI 4",
    name: "Less Urgent",
    symbol: "◆",
    bg: "bg-emerald-950/40",
    border: "border-emerald-500/35",
    text: "text-emerald-400",
    dot: "bg-emerald-500",
    glow: "",
  },
  5: {
    label: "ESI 5",
    name: "Non-Urgent",
    symbol: "✓",
    bg: "bg-blue-950/40",
    border: "border-blue-500/30",
    text: "text-blue-400",
    dot: "bg-blue-500",
    glow: "",
  },
};

const SIZE_CLASSES = {
  sm: "px-1.5 py-0.5 text-[10px] gap-1",
  md: "px-2 py-1 text-xs gap-1.5",
  lg: "px-3 py-1.5 text-sm gap-2",
};

export function ESIBadge({
  level,
  size = "md",
  className,
  pulse = false,
}: ESIBadgeProps) {
  const cfg = ESI_CONFIG[level];

  return (
    <span
      className={cn(
        "inline-flex items-center font-mono font-bold rounded-md border transition-all duration-300",
        cfg.bg,
        cfg.border,
        cfg.text,
        SIZE_CLASSES[size],
        (level === 1 || level === 2) && cfg.glow,
        pulse && level <= 2 && "animate-alert-glow",
        className
      )}
      role="img"
      aria-label={`${cfg.label}: ${cfg.name}`}
    >
      <span className="leading-none" aria-hidden="true">
        {cfg.symbol}
      </span>
      <span>{cfg.label}</span>
    </span>
  );
}