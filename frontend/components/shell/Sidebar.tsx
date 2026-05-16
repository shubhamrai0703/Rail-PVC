"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { NAV_ITEMS } from "@/components/shell/nav";
import { useShellState } from "@/components/shell/ShellState";
import { cn } from "@/lib/cn";

const ORG_NAME = "Acme Infra";    // TODO P4-001: pull from session
const USER_INITIALS = "SM";        // TODO P4-001: pull from session

export function Sidebar() {
  const pathname = usePathname();
  const { sidebar, toggleSidebar } = useShellState();
  const collapsed = sidebar.collapsed;

  return (
    <aside
      data-collapsed={collapsed ? "true" : "false"}
      className={cn(
        "flex flex-col bg-slate-900 text-slate-300 border-r border-slate-800",
        "transition-[width] duration-200 ease-out",
        collapsed ? "w-[52px]" : "w-[220px]",
      )}
    >
      {/* Brand row */}
      <div
        className={cn(
          "h-14 flex items-center border-b border-slate-800",
          collapsed ? "justify-center px-0" : "px-3.5",
        )}
      >
        <div className="flex items-center gap-2.5">
          <span className="h-6 w-6 rounded-md bg-amber-600 grid place-items-center text-white text-[10px] font-bold tracking-widest">
            R
          </span>
          {!collapsed && (
            <span className="text-slate-50 font-semibold text-[13px] tracking-tight">
              RailPVC
            </span>
          )}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2">
        <ul className="flex flex-col gap-0.5">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  title={collapsed ? item.label : undefined}
                  className={cn(
                    "group relative flex items-center gap-3 text-[13px]",
                    collapsed ? "justify-center mx-1.5 h-9" : "mx-1.5 h-9 px-2.5",
                    "rounded-md",
                    active
                      ? "bg-slate-800 text-slate-50"
                      : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60",
                  )}
                >
                  {active && (
                    <span className="absolute left-0 top-1.5 bottom-1.5 w-[2px] rounded-r bg-amber-500" />
                  )}
                  <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer: org + user + collapse toggle */}
      <div
        className={cn(
          "border-t border-slate-800 py-2.5",
          collapsed ? "px-0" : "px-2.5",
        )}
      >
        <div
          className={cn(
            "flex items-center gap-2.5",
            collapsed ? "justify-center" : "px-1",
          )}
        >
          <span className="h-7 w-7 shrink-0 grid place-items-center rounded-full bg-slate-700 text-slate-100 text-[10px] font-semibold">
            {USER_INITIALS}
          </span>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <div className="text-slate-200 text-[12px] truncate">Saqlain</div>
              <div className="text-slate-500 text-[10.5px] truncate">{ORG_NAME}</div>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={`${collapsed ? "Expand" : "Collapse"} sidebar  ⌘\\`}
          className={cn(
            "mt-2 flex items-center text-slate-500 hover:text-slate-200 text-[11px]",
            collapsed ? "justify-center w-full" : "gap-1.5 px-1",
          )}
        >
          {collapsed ? (
            <PanelLeftOpen className="h-4 w-4" strokeWidth={1.75} />
          ) : (
            <>
              <PanelLeftClose className="h-4 w-4" strokeWidth={1.75} />
              <span>Collapse</span>
              <span className="ml-auto font-mono text-[10px] text-slate-600">⌘\</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
