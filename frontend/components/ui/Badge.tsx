import { cn } from "@/lib/cn";

export type BadgeVariant = "draft" | "approved" | "superseded" | "blocked" | "neutral";

type BadgeProps = {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
};

const variants: Record<BadgeVariant, { wrap: string; dot: string | null; strike?: boolean }> = {
  draft:     { wrap: "bg-slate-50  text-slate-600 border-slate-200", dot: "bg-slate-400" },
  approved:  { wrap: "bg-green-50  text-green-700 border-green-200", dot: "bg-green-600" },
  superseded:{ wrap: "bg-slate-100 text-slate-500 border-slate-200", dot: null, strike: true },
  blocked:   { wrap: "bg-red-50    text-red-700   border-red-200",   dot: "bg-red-600" },
  neutral:   { wrap: "bg-slate-50  text-slate-600 border-slate-200", dot: null },
};

export function Badge({ variant = "neutral", children, className }: BadgeProps) {
  const v = variants[variant];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border leading-5",
        v.wrap,
        v.strike && "line-through decoration-slate-400",
        className,
      )}
    >
      {v.dot && <span className={cn("h-1.5 w-1.5 rounded-full", v.dot)} />}
      {children}
    </span>
  );
}
