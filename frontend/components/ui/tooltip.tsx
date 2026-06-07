"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface TooltipContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}
const TooltipContext = React.createContext<TooltipContextValue | undefined>(undefined);

function Tooltip({
  children,
  delayDuration = 200,
}: {
  children: React.ReactNode;
  delayDuration?: number;
}) {
  const [open, setOpen] = React.useState(false);
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout>>();

  const show = () => {
    timeoutRef.current = setTimeout(() => setOpen(true), delayDuration);
  };
  const hide = () => {
    clearTimeout(timeoutRef.current);
    setOpen(false);
  };

  return (
    <TooltipContext.Provider value={{ open, setOpen }}>
      <div
        className="relative inline-block"
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
      >
        {children}
      </div>
    </TooltipContext.Provider>
  );
}

function TooltipTrigger({
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div {...props}>{children}</div>;
}

function TooltipContent({
  className,
  children,
  sideOffset = 4,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { sideOffset?: number }) {
  const { open } = React.useContext(TooltipContext)!;
  if (!open) return null;

  return (
    <div
      className={cn(
        "absolute left-1/2 -translate-x-1/2 bottom-full mb-1 z-50",
        className
      )}
      {...props}
    >
      <div
        className={cn(
          "rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 shadow-xl"
        )}
        style={{ marginBottom: sideOffset }}
      >
        {children}
      </div>
    </div>
  );
}

export { Tooltip, TooltipTrigger, TooltipContent };