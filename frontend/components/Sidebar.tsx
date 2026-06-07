"use client";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, UserPlus, BookOpen, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/patient/intake", label: "Patient Intake", icon: UserPlus },
  { href: "/how-it-works", label: "How It Works", icon: BookOpen },
  { href: "/reference", label: "Reference Manual", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  return (
    <aside className="fixed top-12 left-0 bottom-0 w-56 bg-slate-900/70 backdrop-blur-md border-r border-slate-800/60 p-3 flex flex-col">
      <nav className="flex-1 space-y-1">
        {links.map((link) => (
          <button
            key={link.href}
            onClick={() => router.push(link.href)}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition",
              pathname === link.href ? "bg-teal-950/30 text-teal-300 border border-teal-500/30" : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
            )}
          >
            <link.icon className="w-4 h-4" />
            {link.label}
          </button>
        ))}
      </nav>
      <button className="flex items-center gap-2 text-xs text-slate-600 hover:text-slate-400 mt-2">
        <Settings className="w-4 h-4" /> Settings
      </button>
    </aside>
  );
}