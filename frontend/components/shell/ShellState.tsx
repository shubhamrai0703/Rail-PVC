"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

/* ───────────────────────────────────────────────────────────────
   ShellState — sidebar collapsed/expanded + command-palette open.
   Sidebar mode is "auto" by default: tracks viewport width
   (< 1280px → collapsed). `Cmd+\` flips into manual mode and
   pins whichever state the user wants.
   ─────────────────────────────────────────────────────────────── */

type SidebarMode = "auto" | "manual";
type SidebarState = { mode: SidebarMode; collapsed: boolean };

type ShellCtx = {
  sidebar: SidebarState;
  toggleSidebar: () => void;
  paletteOpen: boolean;
  setPaletteOpen: (open: boolean) => void;
};

const Ctx = createContext<ShellCtx | null>(null);

const NARROW_BREAKPOINT = 1280;

export function ShellStateProvider({ children }: { children: React.ReactNode }) {
  const [sidebar, setSidebar] = useState<SidebarState>(() => ({
    mode: "auto",
    // SSR default: assume wide. Hydration effect immediately corrects.
    collapsed: false,
  }));
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Auto-mode: track viewport width via matchMedia.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia(`(max-width: ${NARROW_BREAKPOINT - 1}px)`);
    const apply = () => {
      setSidebar((prev) =>
        prev.mode === "auto" ? { mode: "auto", collapsed: mq.matches } : prev,
      );
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebar((prev) => ({ mode: "manual", collapsed: !prev.collapsed }));
  }, []);

  // Global keys: Cmd/Ctrl+\ collapses, Cmd/Ctrl+K opens palette.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      if (e.key === "\\") {
        e.preventDefault();
        toggleSidebar();
      } else if (e.key === "k" || e.key === "K") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggleSidebar]);

  const value = useMemo<ShellCtx>(
    () => ({ sidebar, toggleSidebar, paletteOpen, setPaletteOpen }),
    [sidebar, toggleSidebar, paletteOpen],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useShellState(): ShellCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useShellState must be used inside <ShellStateProvider>");
  return ctx;
}
