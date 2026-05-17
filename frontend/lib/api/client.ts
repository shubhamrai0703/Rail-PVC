import { toast } from "sonner";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

// ── Structured error shapes from services/errors.py ──────────────────────────

export type ApiProblem =
  | { code: "validation_error"; message: string }
  | { code: "engine_validation_error"; message: string; validation_errors: string[] }
  | { code: "conflict"; message: string }
  | { code: "idempotency_conflict"; message: string; run_id: string }
  | { code: "immutable_approved_run"; message: string; run_id: string }
  | { code: "not_found"; message: string }
  | { code: "unauthenticated"; message: string }
  | { code: string; message: string; [key: string]: unknown };

export class ApiError extends Error {
  status: number;
  body: unknown;
  /** Populated when the backend returned a structured ApiProblem payload. */
  detail?: ApiProblem;

  constructor(status: number, message: string, body: unknown, detail?: ApiProblem) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.detail = detail;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  /** Suppress the default error-toast — useful when the caller renders its own UI for failure. */
  silent?: boolean;
};

/**
 * Typed fetch wrapper. Phase 4 base — when openapi-typescript output lands,
 * we'll layer typed `get<"/api/contracts">()` helpers on top of this primitive.
 *
 * - 2xx → parsed JSON
 * - 4xx/5xx → throws ApiError (detail populated when backend returns ApiProblem);
 *             also surfaces a Sonner toast (unless silent)
 * - Network failure → throws ApiError(status=0); toast
 */
export async function apiFetch<T = unknown>(
  path: string,
  { body, silent, headers, ...init }: RequestOptions = {},
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

  const authHeader = await getAuthHeader();

  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        "content-type": "application/json",
        accept: "application/json",
        ...authHeader,
        ...headers, // caller-supplied headers win (e.g. explicit Authorization override)
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (cause) {
    const err = new ApiError(0, "Network error — is the API reachable?", { cause });
    if (!silent) {
      toast.error("Network error", {
        description: `${init.method ?? "GET"} ${path}`,
      });
    }
    throw err;
  }

  const text = await res.text();
  const json = text ? safeJSON(text) : null;

  if (!res.ok) {
    const structured = extractApiProblem(json);

    const message = structured?.message
      ?? (typeof json === "object" && json && "detail" in json && typeof (json as Record<string, unknown>).detail === "string"
          ? (json as Record<string, unknown>).detail as string
          : null)
      ?? res.statusText
      ?? "Request failed";

    const err = new ApiError(res.status, message, json, structured ?? undefined);

    if (!silent) {
      toast.error(`${res.status} · ${friendly(res.status)}`, {
        description: toastDescription(structured, message),
      });
    }
    throw err;
  }

  return json as T;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function getAuthHeader(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};
  try {
    const { createClient } = await import("@/lib/supabase/client");
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session?.access_token) return {};
    return { Authorization: `Bearer ${session.access_token}` };
  } catch {
    return {};
  }
}

function extractApiProblem(json: unknown): ApiProblem | null {
  if (
    typeof json !== "object" ||
    json === null ||
    !("detail" in json) ||
    typeof (json as Record<string, unknown>).detail !== "object" ||
    (json as Record<string, unknown>).detail === null
  ) {
    return null;
  }
  const d = (json as Record<string, unknown>).detail as Record<string, unknown>;
  if (typeof d.code !== "string" || typeof d.message !== "string") return null;
  return d as ApiProblem;
}

function toastDescription(problem: ApiProblem | null, fallback: string): string {
  if (!problem) return fallback;
  switch (problem.code) {
    case "engine_validation_error": {
      const errors = (problem as { validation_errors?: unknown[] }).validation_errors;
      return (Array.isArray(errors) ? errors[0] as string | undefined : undefined) ?? problem.message;
    }
    case "idempotency_conflict":
    case "immutable_approved_run":
      return `${problem.message} (run ${problem.run_id})`;
    default:
      return problem.message;
  }
}

function safeJSON(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function friendly(status: number): string {
  if (status === 401) return "Not signed in";
  if (status === 403) return "Forbidden";
  if (status === 404) return "Not found";
  if (status === 409) return "Conflict";
  if (status === 422) return "Validation failed";
  if (status >= 500) return "Server error";
  return "Request failed";
}
