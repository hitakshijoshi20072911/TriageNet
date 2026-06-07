'use client'

import React, { useState, useMemo } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceArea,
  ReferenceLine,
  Legend,
} from 'recharts'
import { Activity, Thermometer, Wind, Droplets } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { VitalReading } from '@/lib/types'

interface VitalsChartProps {
  data:        VitalReading[]
  className?:  string
}

type MetricKey = 'heart_rate' | 'spO2' | 'systolic_bp' | 'resp_rate'

const METRIC_CONFIG: Record<MetricKey, {
  label:     string
  unit:      string
  color:     string
  domain:    [number, number]
  normalMin: number
  normalMax: number
  icon:      React.ReactNode
}> = {
  heart_rate: {
    label:     'Heart Rate',
    unit:      'bpm',
    color:     '#2DD4BF',
    domain:    [40, 160],
    normalMin: 60,
    normalMax: 100,
    icon:      <Activity className="h-3 w-3" />,
  },
  spO2: {
    label:     'SpO₂',
    unit:      '%',
    color:     '#60A5FA',
    domain:    [82, 100],
    normalMin: 95,
    normalMax: 100,
    icon:      <Droplets className="h-3 w-3" />,
  },
  systolic_bp: {
    label:     'Systolic BP',
    unit:      'mmHg',
    color:     '#A78BFA',
    domain:    [70, 210],
    normalMin: 90,
    normalMax: 140,
    icon:      <Activity className="h-3 w-3" />,
  },
  resp_rate: {
    label:     'Resp Rate',
    unit:      '/min',
    color:     '#34D399',
    domain:    [8, 35],
    normalMin: 12,
    normalMax: 20,
    icon:      <Wind className="h-3 w-3" />,
  },
}

const ACTIVE_METRICS_DEFAULT: MetricKey[] = ['heart_rate', 'spO2']

function CustomTooltip({ active, payload, label }: {
  active?:  boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?:   string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl text-xs">
      <div className="text-slate-400 font-mono mb-2">{label}</div>
      {payload.map(p => {
        const key   = Object.entries(METRIC_CONFIG).find(([, v]) => v.color === p.color)?.[0] as MetricKey
        const cfg   = key ? METRIC_CONFIG[key] : null
        const isOob = cfg && (p.value < cfg.normalMin || p.value > cfg.normalMax)
        return (
          <div key={p.name} className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full" style={{ background: p.color }} />
            <span className="text-slate-400">{cfg?.label ?? p.name}:</span>
            <span className={cn(
              'font-mono font-bold',
              isOob ? 'text-red-400' : 'text-slate-100'
            )}>
              {p.value}
            </span>
            <span className="text-slate-600">{cfg?.unit}</span>
            {isOob && <span className="text-red-400 text-[9px]">⚠</span>}
          </div>
        )
      })}
    </div>
  )
}

export function VitalsChart({ data, className }: VitalsChartProps) {
  const [activeMetrics, setActiveMetrics] = useState<MetricKey[]>(ACTIVE_METRICS_DEFAULT)
  const [timeRange, setTimeRange] = useState<'15m' | '30m' | '1h' | 'all'>('30m')

  const filteredData = useMemo(() => {
    const now = Date.now()
    const cutoff = {
      '15m': 15 * 60_000,
      '30m': 30 * 60_000,
      '1h':  60 * 60_000,
      'all': Infinity,
    }[timeRange]

    return data
      .filter(d => now - new Date(d.timestamp).getTime() <= cutoff)
      .map(d => ({
        ...d,
        time: new Date(d.timestamp).toLocaleTimeString('en-US', {
          hour:   '2-digit',
          minute: '2-digit',
          hour12: false,
        }),
      }))
  }, [data, timeRange])

  function toggleMetric(m: MetricKey) {
    setActiveMetrics(prev =>
      prev.includes(m)
        ? prev.length > 1 ? prev.filter(x => x !== m) : prev
        : [...prev, m]
    )
  }

  // Latest stats
  const latest = data[data.length - 1]

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Stat Cards */}
      <div className="grid grid-cols-4 gap-2">
        {(Object.entries(METRIC_CONFIG) as [MetricKey, (typeof METRIC_CONFIG)[MetricKey]][]).map(
          ([key, cfg]) => {
            if (!latest) return null
            const val    = latest[key]
            const isOob  = val < cfg.normalMin || val > cfg.normalMax
            return (
              <button
                key={key}
                onClick={() => toggleMetric(key)}
                className={cn(
                  'p-2.5 rounded-lg border transition-all duration-200 text-left',
                  activeMetrics.includes(key)
                    ? 'bg-slate-800/80 border-slate-600/50'
                    : 'bg-slate-900/40 border-slate-800/50 opacity-50',
                )}
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <div className="w-2 h-2 rounded-full" style={{ background: cfg.color }} />
                  <span className="text-[9px] text-slate-500 uppercase tracking-wide">
                    {cfg.label}
                  </span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className={cn(
                    'font-mono font-bold text-xl leading-none',
                    isOob ? 'text-red-400' : 'text-slate-100'
                  )}>
                    {val}
                  </span>
                  <span className="text-[10px] text-slate-500">{cfg.unit}</span>
                  {isOob && (
                    <span className="text-red-400 text-xs ml-auto">⚠</span>
                  )}
                </div>
                <div className="text-[9px] text-slate-600 mt-0.5">
                  Normal: {cfg.normalMin}–{cfg.normalMax}
                </div>
              </button>
            )
          }
        )}
      </div>

      {/* Time Range Picker */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-slate-500 font-mono">Range:</span>
        {(['15m', '30m', '1h', 'all'] as const).map(r => (
          <button
            key={r}
            onClick={() => setTimeRange(r)}
            className={cn(
              'px-2 py-0.5 rounded text-[10px] font-mono border transition-all',
              timeRange === r
                ? 'bg-teal-950/60 text-teal-400 border-teal-500/40'
                : 'text-slate-500 border-slate-800 hover:border-slate-600'
            )}
          >
            {r}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={filteredData}
            margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(71,85,105,0.2)"
              vertical={false}
            />
            <XAxis
              dataKey="time"
              tick={{ fill: '#475569', fontSize: 9, fontFamily: 'monospace' }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: '#475569', fontSize: 9, fontFamily: 'monospace' }}
              axisLine={false}
              tickLine={false}
              width={28}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Normal range shading */}
            {activeMetrics.map(key => {
              const cfg = METRIC_CONFIG[key]
              return (
                <ReferenceArea
                  key={`area-${key}`}
                  y1={cfg.normalMin}
                  y2={cfg.normalMax}
                  fill={`${cfg.color}06`}
                  strokeOpacity={0}
                />
              )
            })}

            {/* Lines */}
            {activeMetrics.map(key => {
              const cfg = METRIC_CONFIG[key]
              return (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  name={cfg.label}
                  stroke={cfg.color}
                  strokeWidth={1.5}
                  dot={false}
                  activeDot={{
                    r: 3,
                    fill: cfg.color,
                    stroke: 'rgba(15,23,42,0.8)',
                    strokeWidth: 2,
                  }}
                  isAnimationActive={false}
                />
              )
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Metric Legend */}
      <div className="flex flex-wrap gap-3">
        {(Object.entries(METRIC_CONFIG) as [MetricKey, (typeof METRIC_CONFIG)[MetricKey]][]).map(
          ([key, cfg]) => (
            <button
              key={key}
              onClick={() => toggleMetric(key)}
              className={cn(
                'flex items-center gap-1.5 text-[10px] transition-opacity',
                !activeMetrics.includes(key) && 'opacity-30'
              )}
            >
              <div className="w-3 h-0.5 rounded" style={{ background: cfg.color }} />
              <span className="text-slate-400">{cfg.label}</span>
            </button>
          )
        )}
      </div>
    </div>
  )
}