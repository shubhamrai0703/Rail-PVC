import type { LucideIcon } from "lucide-react";
import { FileText, LineChart, FolderClosed } from "lucide-react";

export type NavItem = {
  /** URL path. Active when the current pathname starts with this. */
  href: string;
  /** Visible label (sidebar expanded, palette, header crumb). */
  label: string;
  /** Lucide icon component. */
  icon: LucideIcon;
  /** Two-letter g-prefix shortcut: e.g. "c" → press `g` then `c`. */
  jump: string;
};

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/contracts", label: "Contracts",      icon: FileText,     jump: "c" },
  { href: "/indices",   label: "Index Manager",  icon: LineChart,    jump: "i" },
  { href: "/documents", label: "Document Vault", icon: FolderClosed, jump: "d" },
] as const;
