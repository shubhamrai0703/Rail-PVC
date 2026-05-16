import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type EmptyStateProps = {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
};

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "bg-white border border-dashed border-slate-300 rounded-xl",
        "px-6 py-12 text-center",
        className,
      )}
    >
      {icon ? (
        <div className="mx-auto mb-3 grid place-items-center h-9 w-9 rounded-lg border border-slate-300 text-slate-500">
          {icon}
        </div>
      ) : null}
      <h3 className="text-[15px] font-semibold text-slate-900">{title}</h3>
      {description ? (
        <p className="mt-1 text-[13px] text-slate-500 max-w-md mx-auto">{description}</p>
      ) : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}
