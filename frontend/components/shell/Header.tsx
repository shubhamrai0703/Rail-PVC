"use client";

import { useEffect, useRef, useState } from "react";
import { Search, LogOut } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { NAV_ITEMS } from "@/components/shell/nav";
import { useShellState } from "@/components/shell/ShellState";
import { createClient } from "@/lib/supabase/client";

function currentSection(pathname: string) {
  return NAV_ITEMS.find((n) => pathname === n.href || pathname.startsWith(n.href + "/"));
}

function useUser() {
  const [email, setEmail] = useState<string | null>(null);
  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => setEmail(data.user?.email ?? null));
  }, []);
  return email;
}

function UserMenu({ email }: { email: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  const initial = email[0].toUpperCase();

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        title={email}
        className="h-7 w-7 rounded-full bg-slate-900 text-white text-[11px] font-semibold
                   flex items-center justify-center hover:bg-slate-700 transition-colors"
      >
        {initial}
      </button>

      {open && (
        <div className="absolute right-0 top-9 z-50 w-52 bg-white border border-slate-200 rounded-xl shadow-lg py-1.5 text-[13px]">
          <div className="px-3 py-2 text-slate-500 truncate border-b border-slate-100 text-[12px]">
            {email}
          </div>
          <button
            type="button"
            onClick={signOut}
            className="w-full flex items-center gap-2.5 px-3 py-2 text-slate-700
                       hover:bg-slate-50 transition-colors text-left"
          >
            <LogOut className="h-3.5 w-3.5 text-slate-400" strokeWidth={1.75} />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export function Header() {
  const pathname = usePathname();
  const { setPaletteOpen } = useShellState();
  const section = currentSection(pathname);
  const email = useUser();

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

      {/* Context-pill slot — wired per-route in later phases (contract + bill + quarter). */}
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

      {email && <UserMenu email={email} />}
    </header>
  );
}
