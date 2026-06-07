import * as React from "react";
import { cn } from "@/lib/utils";

function ScrollArea({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "overflow-y-auto pr-1 scrollbar-thin", // uses custom CSS from globals
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export { ScrollArea };