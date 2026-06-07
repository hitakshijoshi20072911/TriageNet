import "./globals.css";
import { ThemeInitializer } from "@/components/ThemeInitializer";
import { TopBar } from "@/components/TopBar";
import { Sidebar } from "@/components/Sidebar";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" data-accessibility="standard">
      <body className="bg-[#020617] text-slate-100 antialiased">
        <ThemeInitializer />
        <TopBar />
        <div className="flex pt-12 min-h-screen">
          <Sidebar />
          <main className="flex-1 ml-56 p-4">{children}</main>
        </div>
      </body>
    </html>
  );
}