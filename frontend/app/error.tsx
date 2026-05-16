"use client";

// Route-level error boundary for the app router.
// Per Next.js 16, the reset prop is `unstable_retry`.

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function RouteError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  useEffect(() => {
    // In a real backend we'd ship this to Sentry / equivalent.
    // For now: surface in dev tools so the cause is reachable.
    // eslint-disable-next-line no-console
    console.error("[route-error]", error);
  }, [error]);

  return (
    <div className="grid place-items-center min-h-[60vh] px-6">
      <div className="max-w-md w-full bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-start gap-3">
          <span className="grid place-items-center h-9 w-9 rounded-md bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="h-4 w-4" strokeWidth={1.75} />
          </span>
          <div className="min-w-0">
            <h2 className="text-[15px] font-semibold text-slate-900">
              Something went wrong on this page.
            </h2>
            <p className="text-[13px] text-slate-500 mt-1">
              The rest of RailPVC is still reachable — try again, or jump elsewhere from the sidebar.
            </p>

            {process.env.NODE_ENV === "development" && (
              <pre className="mt-3 font-mono text-[11px] bg-slate-50 border border-slate-200 rounded-md p-2.5 text-slate-700 overflow-auto max-h-[160px]">
                {error.message}
                {error.digest ? `\n\ndigest: ${error.digest}` : ""}
              </pre>
            )}
          </div>
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => unstable_retry()}>
            Try again
          </Button>
        </div>
      </div>
    </div>
  );
}
