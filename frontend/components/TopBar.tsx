'use client'

import React from 'react'
import { cn } from '@/lib/utils'
import { useStore } from '@/lib/store'
import {
  Activity,
  BedDouble,
  Clock,
  AlertTriangle,
  Eye,
  EyeOff,
  Moon,
  Sun,
  Zap,
} from 'lucide-react'

export function TopBar() {
  const { edStats, darkMode, colorBlindMode, setDarkMode, setColorBlindMode, wsConnected } = useStore()

  return (
    <header className={cn(
      'h-12 flex items-center gap-0 border-b border-slate-800/60',
      'bg-slate-950/80 backdrop-blur-xl',
      'fixed top-0 left-0 right-0 z-40',
    )}>
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 w-56 flex-shrink-0 border-r border-slate-800/60 h-full">
        <div className="relative">
          <div className="w-6 h-6 rounded-md bg-teal-500 flex items-center justify-center">
            <Activity className="h-3.5 w-3.5 text-slate-950" />
          </div>
          {wsConnected && (
            <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
          )}
        </div>
        <div>
          <div className="text-sm font-bold text-slate-100 tracking-tight">TriageNet</div>
          <div className="text-[9px] text-slate-500 font-mono -mt-0.5">Multi-Agent ED System</div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="flex items-center gap-1 px-3 flex-1 overflow-x-auto">
        {edStats && (
          <>
            <StatPill
              icon={<Activity className="h-3 w-3 text-teal-400" />}
              label="Active"
              value={edStats.total_patients}
              color="teal"
            />
            <StatPill
              icon={<BedDouble className="h-3 w-3 text-red-400" />}
              label="ICU Open"
              value={edStats.icu_beds_open}
              color={edStats.icu_beds_open === 0 ? 'red' : 'amber'}
            />
            <StatPill
              icon={<BedDouble className="h-3 w-3 text-amber-400" />}
              label="Monitored"
              value={edStats.monitored_open}
              color="slate"
            />
            <StatPill
              icon={<Clock className="h-3 w-3 text-blue-400" />}
              label="Avg Wait"
              value={`${edStats.avg_wait_min}m`}
              color="slate"
            />
            <StatPill
              icon={<AlertTriangle className="h-3 w-3 text-red-400" />}
              label="Critical"
              value={edStats.critical_count}
              color={edStats.critical_count > 0 ? 'red' : 'slate'}
            />
            {edStats.pending_decisions > 0 && (
              <StatPill
                icon={<Zap className="h-3 w-3 text-amber-400" />}
                label="Pending"
                value={edStats.pending_decisions}
                color="amber"
                pulse
              />
            )}
          </>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-1 px-3 flex-shrink-0 border-l border-slate-800/60 h-full">
        {/* WS Status */}
        <div className={cn(
          'flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-mono',
          wsConnected ? 'text-teal-400' : 'text-slate-500'
        )}>
          <span className={cn(
            'w-1.5 h-1.5 rounded-full',
            wsConnected ? 'bg-teal-500 animate-pulse' : 'bg-slate-700'
          )} />
          {wsConnected ? 'LIVE' : 'DEMO'}
        </div>

        {/* Color Blind Toggle */}
        <button
          onClick={() => setColorBlindMode(!colorBlindMode)}
          className={cn(
            'flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] border transition-all',
            colorBlindMode
              ? 'bg-purple-950/50 border-purple-500/40 text-purple-300'
              : 'border-slate-800 text-slate-500 hover:border-slate-600 hover:text-slate-400'
          )}
          title="Toggle Color-Blind Accessible Mode"
        >
          {colorBlindMode ? (
            <Eye className="h-3 w-3" />
          ) : (
            <EyeOff className="h-3 w-3" />
          )}
          <span>A11Y</span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="p-1.5 rounded-md border border-slate-800 text-slate-500 hover:border-slate-600 hover:text-slate-400 transition-all"
          title="Toggle Theme"
        >
          {darkMode ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
        </button>
      </div>
    </header>
  )
}

interface StatPillProps {
  icon:    React.ReactNode
  label:   string
  value:   number | string
  color:   'teal' | 'amber' | 'red' | 'blue' | 'slate'
  pulse?:  boolean
}

function StatPill({ icon, label, value, color, pulse }: StatPillProps) {
  const colorClasses = {
    teal:  'text-teal-400',
    amber: 'text-amber-400',
    red:   'text-red-400',
    blue:  'text-blue-400',
    slate: 'text-slate-300',
  }

  return (
    <div className={cn(
      'flex items-center gap-1.5 px-2.5 py-1 rounded-md',
      'bg-slate-900/60 border border-slate-800/60',
      'text-[10px] font-mono whitespace-nowrap flex-shrink-0',
      pulse && 'animate-pulse-teal',
    )}>
      {icon}
      <span className="text-slate-500">{label}</span>
      <span className={cn('font-bold', colorClasses[color])}>{value}</span>
    </div>
  )
}