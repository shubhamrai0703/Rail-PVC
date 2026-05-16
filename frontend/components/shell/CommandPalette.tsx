"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { CornerDownLeft } from "lucide-react";
import { NAV_ITEMS } from "@/components/shell/nav";
import { useShellState } from "@/components/shell/ShellState";

/**
 * ⌘K palette — route-jump only for Phase 4.
 * Phase 5 will append an Actions group; Phase 7 will append Recent runs.
 *
 * Also wires `g`-prefix Vim-style nav: press `g`, then within 1s press the
 * jump key. Suppressed when the user is typing into a field.
 */
export function CommandPalette() {
  const router = useRouter();
  const { paletteOpen, setPaletteOpen } = useShellState();
  const [search, setSearch] = useState("");

  // g-prefix nav: track whether we just saw a bare `g` keypress.
  const gPressedAt = useRef<number | null>(null);
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Skip when typing
      const target = e.target as HTMLElement | null;
      const inField =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;
      if (inField) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const now = Date.now();
      const within = gPressedAt.current && now - gPressedAt.current < 1200;

      if (within) {
        const match = NAV_ITEMS.find((n) => n.jump === e.key.toLowerCase());
        if (match) {
          e.preventDefault();
          gPressedAt.current = null;
          router.push(match.href);
          return;
        }
        gPressedAt.current = null;
      }

      if (e.key === "g") {
        gPressedAt.current = now;
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  function go(href: string) {
    setPaletteOpen(false);
    setSearch("");
    router.push(href);
  }

  return (
    <Command.Dialog
      open={paletteOpen}
      onOpenChange={setPaletteOpen}
      label="Command palette"
      className="fixed inset-0 z-50"
      overlayClassName="fixed inset-0 bg-slate-900/40 backdrop-blur-[2px]"
      contentClassName="
        fixed top-[18%] left-1/2 -translate-x-1/2
        w-[min(560px,calc(100vw-32px))]
        bg-white border border-slate-200 rounded-xl
        shadow-[0_24px_60px_rgba(15,23,42,0.25)]
        overflow-hidden
      "
    >
      <div className="flex items-center gap-3 px-4 border-b border-slate-200">
        <Command.Input
          value={search}
          onValueChange={setSearch}
          placeholder="Jump to…"
          className="
            flex-1 h-12 bg-transparent outline-none border-0
            text-[14px] text-slate-900 placeholder:text-slate-400
          "
        />
        <kbd className="font-mono text-[10.5px] tabular-nums bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
          esc
        </kbd>
      </div>

      <Command.List className="max-h-[360px] overflow-y-auto p-1.5">
        <Command.Empty className="px-3 py-6 text-center text-[12.5px] text-slate-400">
          No matches.
        </Command.Empty>

        <Command.Group
          heading="Navigate"
          className="
            [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:pt-2 [&_[cmdk-group-heading]]:pb-1
            [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider
            [&_[cmdk-group-heading]]:text-slate-400 [&_[cmdk-group-heading]]:font-medium
          "
        >
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <Command.Item
                key={item.href}
                value={`${item.label} ${item.href}`}
                onSelect={() => go(item.href)}
                className="
                  flex items-center gap-2.5 px-2 h-9 rounded-md text-[13px] text-slate-700
                  cursor-pointer
                  data-[selected=true]:bg-slate-100 data-[selected=true]:text-slate-900
                "
              >
                <Icon className="h-4 w-4 text-slate-500" strokeWidth={1.75} />
                <span className="flex-1">{item.label}</span>
                <kbd className="font-mono text-[10.5px] tabular-nums bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
                  g {item.jump}
                </kbd>
                <CornerDownLeft className="h-3.5 w-3.5 text-slate-300" strokeWidth={1.75} />
              </Command.Item>
            );
          })}
        </Command.Group>

        <Command.Group
          heading="Recent runs"
          className="
            [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:pt-2 [&_[cmdk-group-heading]]:pb-1
            [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider
            [&_[cmdk-group-heading]]:text-slate-400 [&_[cmdk-group-heading]]:font-medium
          "
        >
          <div className="px-3 py-3 text-[12px] text-slate-400">
            No runs yet — waiting on Phase 5.
          </div>
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  );
}
