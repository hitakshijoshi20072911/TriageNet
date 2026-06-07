import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          teal: "#0D9488",
          cyan: "#06B6D4",
        },
        esi: {
          1: "#EF4444",
          2: "#F59E0B",
          3: "#EAB308",
          4: "#10B981",
          5: "#3B82F6",
        },
      },
      backgroundColor: {
        "slate-925": "#060f1e",
        "slate-875": "#111827",
        "slate-850": "#141c2e",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "alert-glow": "alertGlow 2s ease-in-out infinite",
        "pulse-teal": "pulseTeal 1.5s ease-in-out infinite",
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-in-up": "slideInUp 0.3s ease-out",
      },
      keyframes: {
        alertGlow: {
          "0%, 100%": { boxShadow: "0 0 4px rgba(239,68,68,0.2)" },
          "50%": { boxShadow: "0 0 16px rgba(239,68,68,0.6)" },
        },
        pulseTeal: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;