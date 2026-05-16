"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ApiError } from "@/lib/api/client";

function buildQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: false,
        retry(failureCount, error) {
          // Don't retry on auth / validation / not-found / conflict.
          if (error instanceof ApiError && [401, 403, 404, 409, 422].includes(error.status)) {
            return false;
          }
          return failureCount < 2;
        },
      },
      mutations: {
        // The client wrapper already toasts; mutations re-throw so callers can branch.
        retry: false,
      },
    },
  });
}

export function Providers({ children }: { children: React.ReactNode }) {
  // One client per mount — survives StrictMode double-render.
  const [client] = useState(buildQueryClient);

  return (
    <QueryClientProvider client={client}>
      {children}
      {process.env.NODE_ENV === "development" ? (
        <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
      ) : null}
    </QueryClientProvider>
  );
}
