'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import type { VitalReading, AgentMessage } from '@/lib/types'
import { useStore } from '@/lib/store'
import { INITIAL_AGENT_MESSAGES } from '@/lib/mockData'

// Simulates live vitals updates and agent messages for demo purposes
export function useMockTelemetry(active = true) {
  const { patients, addAgentMessage, updatePatientRisk } = useStore()
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const msgIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [tick, setTick] = useState(0)
  const initializedRef = useRef(false)

  // Seed initial messages once
  useEffect(() => {
    if (initializedRef.current) return
    initializedRef.current = true
    INITIAL_AGENT_MESSAGES.forEach((msg, i) => {
      setTimeout(() => addAgentMessage(msg), i * 600)
    })
  }, [addAgentMessage])

  const generateVitalTick = useCallback((base: VitalReading): VitalReading => {
    const n = (v: number, range: number) => v + (Math.random() - 0.5) * range
    return {
      ...base,
      timestamp:   new Date().toISOString(),
      heart_rate:  Math.round(Math.max(40, Math.min(200, n(base.heart_rate, 6)))),
      systolic_bp: Math.round(Math.max(60, Math.min(220, n(base.systolic_bp, 8)))),
      spO2:        Math.min(100, Math.round(Math.max(70, n(base.spO2, 2)))),
      resp_rate:   Math.round(Math.max(8, Math.min(40, n(base.resp_rate, 2)))),
    }
  }, [])

  const MOCK_AGENT_EVENTS: AgentMessage[] = [
    {
      id:         `live-${Date.now()}-a`,
      agent:      'vitals',
      content:    'Monitoring loop cycle complete. All parameters within watch thresholds. CUSUM charts nominal.',
      timestamp:  new Date().toISOString(),
      type:       'info',
      confidence: 0.92,
    },
    {
      id:         `live-${Date.now()}-b`,
      agent:      'context',
      content:    'Bed 203 now available — monitored zone. Recommending transfer evaluation for pt-005 (stroke alert).',
      timestamp:  new Date().toISOString(),
      type:       'info',
      patient_id: 'pt-005',
    },
    {
      id:         `live-${Date.now()}-c`,
      agent:      'history',
      content:    'Cross-referencing pt-003 chart: Prior LVEF 35% (2023 echo), current presentation consistent with acute decompensated HF. Confidence 0.83.',
      timestamp:  new Date().toISOString(),
      type:       'analysis',
      confidence: 0.83,
      patient_id: 'pt-003',
    },
    {
      id:         `live-${Date.now()}-d`,
      agent:      'supervisor',
      content:    'Routing cross-examination: Risk scores differ by 12 pts between Vitals and History agents on pt-003. Initiating debate protocol.',
      timestamp:  new Date().toISOString(),
      type:       'debate',
      patient_id: 'pt-003',
    },
  ]

  let msgCursor = 0

  useEffect(() => {
    if (!active) return

    intervalRef.current = setInterval(() => {
      setTick(t => t + 1)
    }, 2_000)

    msgIntervalRef.current = setInterval(() => {
      const msg = {
        ...MOCK_AGENT_EVENTS[msgCursor % MOCK_AGENT_EVENTS.length],
        id:        `live-${Date.now()}`,
        timestamp: new Date().toISOString(),
      }
      addAgentMessage(msg)
      msgCursor++
    }, 8_000)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      if (msgIntervalRef.current) clearInterval(msgIntervalRef.current)
    }
  }, [active, addAgentMessage])

  return { tick, generateVitalTick }
}