import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "approve" | "danger";
type Size = "sm" | "md";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

const base =
  "inline-flex items-center justify-center gap-2 rounded-md font-medium " +
  "transition-colors disabled:cursor-not-allowed disabled:opacity-50 " +
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600";

const variants: Record<Variant, string> = {
  primary:
    "bg-slate-900 text-white border border-slate-900 hover:bg-slate-800",
  secondary:
    "bg-white text-slate-900 border border-slate-200 hover:bg-slate-50",
  ghost:
    "bg-transparent text-slate-700 hover:bg-slate-100",
  approve:
    // The loud green from option 5c — used for the single irreversible Approve action.
    "bg-green-600 text-white border border-green-700 hover:bg-green-700",
  danger:
    "bg-white text-red-700 border border-red-200 hover:bg-red-50",
};

const sizes: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs",
  md: "h-9 px-3.5 text-[13px]",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "secondary", size = "md", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      className={cn(base, variants[variant], sizes[size], className)}
      {...rest}
    />
  );
});
