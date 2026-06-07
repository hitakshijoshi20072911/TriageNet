import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMRN(mrn: string): string {
  return `MRN-****${mrn.slice(-4)}`;
}

export function formatTime(date: Date | string): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatDuration(arrivalTime: Date | string | null | undefined): string {
  if (!arrivalTime) return "0m";
  const arrival =
    typeof arrivalTime === "string" ? new Date(arrivalTime) : arrivalTime;
  if (isNaN(arrival.getTime())) return "0m";
  const diffMs = Date.now() - arrival.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 60) return `${diffMins}m`;
  const h = Math.floor(diffMins / 60);
  const m = diffMins % 60;
  return `${h}h ${m}m`;
}

export function getRiskBgColor(score: number): string {
  if (score >= 85) return "bg-red-500";
  if (score >= 65) return "bg-amber-500";
  if (score >= 45) return "bg-yellow-500";
  return "bg-emerald-500";
}

export function getRiskTextColor(score: number): string {
  if (score >= 85) return "text-red-400";
  if (score >= 65) return "text-amber-400";
  if (score >= 45) return "text-yellow-400";
  return "text-emerald-400";
}