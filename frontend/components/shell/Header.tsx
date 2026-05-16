"use client";

import { Search } from "lucide-react";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/components/shell/nav";
import { useShellState } from "@/components/shell/ShellState";

function currentSection(pathname: string) {
  return NAV_ITEMS.find((n) => pathname === n.href || pathname.startsWith(n.href + "/"));
}

export function Header() {
  const pathname = usePathname();
  const { setPaletteOpen } = useShellState();
  const section = currentSection(pathname);

  return (
    <header className="h-14 flex items-center gap-4 px-6 bg-white border-b border-slate-200">
      {/* Breadcrumbs — section-only for Phase 4. Deeper crumbs land per-route. */}
      <div className="flex items-center gap-2 text-[13px] min-w-0">
        <span className="text-slate-500">RailPVC</span>
        {section && (
          <>
            <span className="text-slate-300">/</span>
            <span className="text-slate-900 font-medium truncate">{section.label}</span>
          </>
        )}
      </div>

      {/* Context-pill slot — wired per-route in later phases (contract + bill + quarter).
          Keeping the structural placement here so children just need to render into it. */}
      <div id="header-context-slot" className="flex items-center gap-2 ml-2" />

      {/* Search / palette opener */}
      <button
        type="button"
        onClick={() => setPaletteOpen(true)}
        className="ml-auto inline-flex items-center gap-2.5 h-8 px-2.5 pr-2 rounded-md
                   border border-slate-200 bg-white text-slate-500 text-[12.5px]
                   hover:bg-slate-50 transition-colors"
      >
        <Search className="h-3.5 w-3.5" strokeWidth={1.75} />
        <span>Search…</span>
        <kbd className="font-mono text-[10.5px] tabular-nums bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded ml-2">
          ⌘K
        </kbd>
      </button>
    </header>
  );
}
