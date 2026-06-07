"use client";

import { useEffect, useRef } from "react";
import { useStore } from "@/lib/store";
import type { AgentMessage } from "@/lib/types";
import { INITIAL_AGENT_MESSAGES } from "@/lib/mockData";

export function useMockTelemetry() {
  const { addAgentMessage, setWsConnected } = useStore();
  const initializedRef = useRef(false);
  const messageIdCounterRef = useRef(0);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    // Seed initial messages once
    INITIAL_AGENT_MESSAGES.forEach((msg, i) => {
      setTimeout(() => addAgentMessage(msg), i * 600);
    });

    // Simulate periodic agent messages with unique IDs
    const MOCK_EVENTS: AgentMessage[] = [
      {
        id: "live-1",
        agent: "vitals",
        content: "Monitoring loop complete. All parameters within thresholds.",
        timestamp: new Date().toISOString(),
        type: "info",
        confidence: 0.92,
      },
      {
        id: "live-2",
        agent: "context",
        content: "Bed 203 now available — monitored zone. Evaluate transfer.",
        timestamp: new Date().toISOString(),
        type: "info",
      },
      {
        id: "live-3",
        agent: "history",
        content: "Cross-referencing patient chart: Prior admissions consistent with current presentation pattern.",
        timestamp: new Date().toISOString(),
        type: "analysis",
        confidence: 0.85,
      },
      {
        id: "live-4",
        agent: "supervisor",
        content: "Routing cross-examination: Risk scores differ by 8 pts between agents. Initiating debate protocol.",
        timestamp: new Date().toISOString(),
        type: "debate",
      },
    ];

    let cursor = 0;
    const interval = setInterval(() => {
      const baseEvent = MOCK_EVENTS[cursor % MOCK_EVENTS.length];
      const event: AgentMessage = {
        ...baseEvent,
        id: `live-${Date.now()}-${messageIdCounterRef.current++}`,
        timestamp: new Date().toISOString(),
      };
      addAgentMessage(event);
      cursor++;
    }, 8000);

    setWsConnected(true);

    return () => clearInterval(interval);
  }, [addAgentMessage, setWsConnected]);
}