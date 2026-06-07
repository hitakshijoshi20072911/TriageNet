"use client";

import React, { useEffect, useRef, useState } from "react";
import { useStore } from "@/lib/store";
import { cn, formatTime } from "@/lib/utils";
import type { AgentType, AgentMessage } from "@/lib/types";
import {
  Activity, Database, Layers, Bot, Users, AlertOctagon, ChevronDown,
} from "lucide-react";

const AGENT_CONFIG: Record<AgentType, { label: string; icon: React.ReactNode; color: string; bg: string; border: string; badge: string }> = {
  vitals: { label: "Vitals Agent", icon: <Activity className="h-3 w-3" />, color: "text-cyan-400", bg: "bg-cyan-950/30", border: "border-cyan-500/30", badge: "bg-cyan-950/60 text-cyan-400 border-cyan-500/30" },
  history: { label: "History Agent", icon: <Database className="h-3 w-3" />, color: "text-emerald-400", bg: "bg-emerald-950/30", border: "border-emerald-500/30", badge: "bg-emerald-950/60 text-emerald-400 border-emerald-500/30" },
  context: { label: "Context Agent", icon: <Layers className="h-3 w-3" />, color: "text-blue-400", bg: "bg-blue-950/30", border: "border-blue-500/25", badge: "bg-blue-950/60 text-blue-400 border-blue-500/25" },
  supervisor: { label: "Supervisor", icon: <Bot className="h-3 w-3" />, color: "text-slate-300", bg: "bg-slate-800/60", border: "border-slate-700/60", badge: "bg-slate-800 text-slate-300 border-slate-700" },
  consensus: { label: "Consensus", icon: <Users className="h-3 w-3" />, color: "text-teal-400", bg: "bg-teal-950/30", border: "border-teal-500/35", badge: "bg-teal-950/60 text-teal-400 border-teal-500/35" },
  escalation: { label: "Escalation", icon: <AlertOctagon className="h-3 w-3" />, color: "text-red-400", bg: "bg-red-950/30", border: "border-red-500/30", badge: "bg-red-950/60 text-red-400 border-red-500/30" },
};

type FilterType = "all" | AgentType;

function AgentMessageBubble({ msg }: { msg: AgentMessage }) {
  const cfg = AGENT_CONFIG[msg.agent];
  return (
    <div className={cn("rounded-lg border p-2.5 transition-all duration-200 animate-slide-in-up", "bg-slate-900/50 backdrop-blur-sm",
      msg.type === "debate" && "resolve-shimmer border-amber-500/20",
      msg.type === "consensus" && "border-teal-500/30 bg-teal-950/15",
      msg.type === "alert" && "border-red-500/25 bg-red-950/10",
      msg.type === "analysis" && "border-slate-800/60",
      msg.type === "info" && "border-slate-800/50"
    )}>
      {msg.type === "debate" && (
        <div className="flex items-center gap-1.5 mb-2 pb-1.5 border-b border-amber-500/20">
          <div className="flex gap-0.5">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
            <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse delay-100" />
            <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse delay-200" />
          </div>
          <span className="text-[9px] font-bold uppercase tracking-widest text-amber-400">Agent Debate Active</span>
        </div>
      )}
      {msg.type === "consensus" && (
        <div className="flex items-center gap-1.5 mb-2 pb-1.5 border-b border-teal-500/25">
          <span className="text-[9px] font-bold uppercase tracking-widest text-teal-400">✓ Consensus Reached</span>
        </div>
      )}
      <div className="flex items-center gap-2 mb-1.5">
        <span className={cn("inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[9px] font-bold", cfg.badge)}>{cfg.icon}{cfg.label.toUpperCase()}</span>
        {msg.patient_id && <span className="text-[9px] font-mono text-slate-600">· {msg.patient_id}</span>}
        <span className="ml-auto text-[9px] font-mono text-slate-600">{formatTime(msg.timestamp)}</span>
      </div>
      <p className="text-[11px] text-slate-300 leading-relaxed">{msg.content}</p>
      {msg.confidence !== undefined && (
        <div className="flex items-center gap-1.5 mt-2 pt-1.5 border-t border-slate-800/50">
          <span className="text-[9px] text-slate-600 font-mono">Confidence</span>
          <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden"><div className="h-full bg-teal-500/70 rounded-full" style={{ width: `${msg.confidence * 100}%` }} /></div>
          <span className="text-[9px] font-mono text-teal-400">{(msg.confidence * 100).toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 px-3 py-2">
      <div className="flex items-center gap-1">
        <div className="w-1.5 h-1.5 rounded-full bg-teal-500/70 typing-dot" />
        <div className="w-1.5 h-1.5 rounded-full bg-teal-500/70 typing-dot" />
        <div className="w-1.5 h-1.5 rounded-full bg-teal-500/70 typing-dot" />
      </div>
      <span className="text-[10px] text-slate-600 font-mono">Agent processing...</span>
    </div>
  );
}

export function AgentFeed({ compact = false }: { compact?: boolean }) {
  const { agentMessages, wsConnected } = useStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<FilterType>("all");
  const [showTyping, setShowTyping] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [agentMessages, autoScroll]);

  useEffect(() => {
    const interval = setInterval(() => { setShowTyping(true); setTimeout(() => setShowTyping(false), 2500); }, 10000);
    return () => clearInterval(interval);
  }, []);

  const filtered = filter === "all" ? agentMessages : agentMessages.filter(m => m.agent === filter);
  const debateActive = agentMessages.slice(-6).some(m => m.type === "debate");
  const pendingAlerts = agentMessages.filter(m => m.type === "alert").length;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-start justify-between mb-3 flex-shrink-0">
        <div>
          <h2 className="text-xs font-bold text-slate-200 uppercase tracking-widest">Live Agent Feed</h2>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={cn("flex items-center gap-1 text-[10px]", wsConnected ? "text-teal-400" : "text-slate-500")}>
              <span className={cn("w-1.5 h-1.5 rounded-full", wsConnected ? "bg-teal-500 animate-pulse" : "bg-slate-600")} />
              {wsConnected ? "Connected" : "Mock mode"}
            </span>
            {debateActive && <span className="text-[10px] text-amber-400 font-mono">· Debate active</span>}
            {pendingAlerts > 0 && <span className="text-[10px] text-red-400">· {pendingAlerts} alert{pendingAlerts > 1 ? "s" : ""}</span>}
          </div>
        </div>
        <span className="text-[10px] font-mono text-slate-600">{filtered.length} msgs</span>
      </div>
      {!compact && (
        <div className="flex gap-1 mb-2 flex-wrap flex-shrink-0">
          {(["all", "vitals", "history", "context", "consensus"] as FilterType[]).map(f => {
            const cfg = f !== "all" ? AGENT_CONFIG[f] : null;
            return (
              <button key={f} onClick={() => setFilter(f)} className={cn(
                "px-2 py-0.5 rounded text-[9px] font-bold border transition-all duration-150",
                filter === f
                  ? cfg ? cfg.badge : "bg-slate-700 text-slate-200 border-slate-600"
                  : "bg-transparent text-slate-600 border-slate-800 hover:border-slate-600"
              )}>{f === "all" ? "ALL" : cfg!.label.replace(" Agent", "").toUpperCase()}</button>
            );
          })}
        </div>
      )}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 pr-1 scrollbar-thin"
        onScroll={(e) => { const el = e.currentTarget; const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60; setAutoScroll(atBottom); }}>
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-24 text-slate-600"><Bot className="h-6 w-6 mb-1.5 opacity-40" /><span className="text-xs">No messages yet</span></div>
        ) : filtered.map(msg => <AgentMessageBubble key={msg.id} msg={msg} />)}
        {showTyping && <TypingIndicator />}
      </div>
      {!autoScroll && filtered.length > 0 && (
        <button onClick={() => { setAutoScroll(true); if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }}
          className="mt-1 flex items-center justify-center gap-1 py-1 text-[10px] text-teal-400 hover:text-teal-300 border border-teal-900/40 rounded-md">
          <ChevronDown className="h-3 w-3" /> Jump to latest
        </button>
      )}
    </div>
  );
}