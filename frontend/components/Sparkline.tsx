import React, { useMemo } from "react";
import type { VitalReading } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SparklineProps {
  data: VitalReading[];
  metric: "heart_rate" | "spO2" | "systolic_bp" | "resp_rate";
  width?: number;
  height?: number;
  color?: string;
  className?: string;
  showDot?: boolean;
}

const METRIC_RANGES = {
  heart_rate: { min: 40, max: 160, normal: [60, 100] },
  spO2: { min: 80, max: 100, normal: [95, 100] },
  systolic_bp: { min: 80, max: 200, normal: [90, 140] },
  resp_rate: { min: 8, max: 30, normal: [12, 20] },
};

export function Sparkline({
  data,
  metric,
  width = 80,
  height = 24,
  color = "#2DD4BF",
  className,
  showDot = true,
}: SparklineProps) {
  const points = useMemo(() => {
    if (!data || data.length === 0) return "";
    const range = METRIC_RANGES[metric];
    const values = data.map((d) => d[metric] as number);
    const padding = 2;
    const w = width - padding * 2;
    const h = height - padding * 2;
    const minVal = Math.min(...values, range.min);
    const maxVal = Math.max(...values, range.max);
    const span = maxVal - minVal || 1;

    return values
      .map((v, i) => {
        const x = padding + (i / (values.length - 1 || 1)) * w;
        const y = padding + h - ((v - minVal) / span) * h;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [data, metric, width, height]);

  const lastValue = data?.[data.length - 1]?.[metric] as number | undefined;
  const range = METRIC_RANGES[metric];
  const isAbnormal =
    lastValue !== undefined &&
    (lastValue < range.normal[0] || lastValue > range.normal[1]);

  if (!data || data.length < 2) {
    // Fallback: placeholder bars
    return (
      <div
        className={cn("flex items-end gap-[2px]", className)}
        style={{ width, height }}
      >
        {Array.from({ length: 8 }, (_, i) => (
          <div
            key={i}
            className="bg-slate-700/60 rounded-sm flex-1"
            style={{ height: `${30 + Math.random() * 50}%` }}
          />
        ))}
      </div>
    );
  }

  const lastPointArr = points.split(" ").pop()?.split(",");
  const dotX = lastPointArr ? parseFloat(lastPointArr[0]) : width - 2;
  const dotY = lastPointArr ? parseFloat(lastPointArr[1]) : height / 2;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={cn("overflow-visible", className)}
      aria-hidden="true"
    >
      {isAbnormal && (
        <rect
          x={0}
          y={0}
          width={width}
          height={height}
          fill={color === "#EF4444" ? "rgba(239,68,68,0.06)" : "rgba(245,158,11,0.06)"}
          rx={2}
        />
      )}
      <path
        d={`M ${points.split(" ")[0].split(",")[0]},${height} L ${points} L ${width - 2},${height} Z`}
        fill={`${color}18`}
      />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {showDot && (
        <>
          <circle cx={dotX} cy={dotY} r={3.5} fill={color} opacity={0.25} className="animate-ping" />
          <circle cx={dotX} cy={dotY} r={2} fill={color} />
        </>
      )}
    </svg>
  );
}
// Mini bar sparkline variant
interface BarSparklineProps {
  data:    VitalReading[]
  metric:  'heart_rate' | 'spO2'
  width?:  number
  height?: number
  color?:  string
  className?: string
}
 
export function BarSparkline({
  data,
  metric,
  width   = 64,
  height  = 20,
  color   = '#2DD4BF',
  className,
}: BarSparklineProps) {
  const bars = useMemo(() => {
    if (!data || data.length === 0) return []
    const values  = data.slice(-12).map(d => d[metric] as number)
    const minVal  = Math.min(...values)
    const maxVal  = Math.max(...values)
    const span    = maxVal - minVal || 1
    return values.map(v => ({
      pct: 0.2 + (0.8 * (v - minVal)) / span,
    }))
  }, [data, metric])
 
  const barWidth = bars.length > 0 ? (width / bars.length) - 1 : 4
 
  return (
    <div
      className={cn('flex items-end gap-[1px]', className)}
      style={{ width, height }}
      aria-hidden="true"
    >
      {bars.map((bar, i) => (
        <div
          key={i}
          className="rounded-sm flex-1 transition-all duration-300"
          style={{
            height:     `${bar.pct * 100}%`,
            background: i === bars.length - 1
              ? color
              : `${color}80`,
            maxWidth:   barWidth,
          }}
        />
      ))}
    </div>
  )
}