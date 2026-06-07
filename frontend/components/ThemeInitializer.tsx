"use client";
import { useEffect } from "react";
import { useStore } from "@/lib/store";

export function ThemeInitializer() {
  const darkMode = useStore((s) => s.darkMode);
  const colorBlindMode = useStore((s) => s.colorBlindMode);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
    document.documentElement.setAttribute("data-accessibility", colorBlindMode ? "colorblind" : "standard");
  }, [darkMode, colorBlindMode]);

  return null;
}
