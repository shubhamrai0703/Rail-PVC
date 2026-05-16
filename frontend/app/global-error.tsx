"use client";

// Replaces the root layout when even that crashes. Must include <html>/<body>.

import { useEffect } from "react";

export default function GlobalError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[global-error]", error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          background: "#f8fafc",
          color: "#0f172a",
          fontFamily:
            'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
          display: "grid",
          placeItems: "center",
          padding: "24px",
        }}
      >
        <div
          style={{
            maxWidth: 440,
            width: "100%",
            background: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: 12,
            padding: 24,
          }}
        >
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>
            RailPVC hit an unexpected error.
          </h2>
          <p style={{ marginTop: 6, fontSize: 13, color: "#64748b" }}>
            We couldn&apos;t render the page. The error has been logged.
          </p>
          <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end" }}>
            <button
              type="button"
              onClick={() => unstable_retry()}
              style={{
                background: "#0f172a",
                color: "#fff",
                border: 0,
                borderRadius: 6,
                fontSize: 13,
                padding: "8px 14px",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              Try again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
