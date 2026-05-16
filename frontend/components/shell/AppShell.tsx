import { ShellStateProvider } from "@/components/shell/ShellState";
import { Sidebar } from "@/components/shell/Sidebar";
import { Header } from "@/components/shell/Header";
import { CommandPalette } from "@/components/shell/CommandPalette";

/**
 * App shell — wraps every authenticated page once P4-001 (auth) lands.
 *
 * Layout: sidebar (Option C — responsive auto-collapse) on the left,
 * header on top, main scrollable area below. The shell owns the
 * ⌘\ / ⌘K key handling and palette portal.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ShellStateProvider>
      <div className="grid grid-cols-[auto_1fr] h-screen bg-slate-50">
        <Sidebar />
        <div className="flex flex-col min-w-0 h-screen overflow-hidden">
          <Header />
          <main className="flex-1 overflow-auto">
            <div className="max-w-[1280px] mx-auto px-8 py-8">{children}</div>
          </main>
        </div>
      </div>
      <CommandPalette />
    </ShellStateProvider>
  );
}
