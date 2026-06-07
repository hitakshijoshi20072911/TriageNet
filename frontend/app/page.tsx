import Link from "next/link";
import { Activity } from "lucide-react";
import { Button } from "@/components/ui";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-center px-4">
      <div className="flex flex-col items-center gap-8 max-w-2xl">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-teal-500/20 border border-teal-500/40 flex items-center justify-center">
            <Activity className="w-8 h-8 text-teal-400" />
          </div>
          <h1 className="text-5xl font-bold tracking-tight text-slate-100">TriageNet</h1>
        </div>
        
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold text-slate-300">
            AI-Powered Emergency Department Orchestration
          </h2>
          <p className="text-lg text-slate-400 max-w-xl">
            Multi-agent system for real-time patient risk assessment, bed management, and clinical decision support in emergency departments.
          </p>
        </div>

        <div className="flex gap-4">
          <Link href="/dashboard">
            <Button size="lg" className="px-8">
              Enter ED Dashboard
            </Button>
          </Link>
          <Link href="/reference">
            <Button size="lg" variant="outline" className="px-8">
              View Reference Manual
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}