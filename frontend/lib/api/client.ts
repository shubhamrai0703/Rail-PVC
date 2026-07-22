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

  const res = await authedFetch(url, {
    ...init,
    headers: {
      "content-type": "application/json",
      accept: "application/json",
      ...headers, // caller-supplied headers win (e.g. explicit Authorization override)
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  }, { silent, method: init.method ?? "GET", path });

  return parseJsonResponse<T>(res, { silent });
}

/** Authenticated multipart upload. The browser must set Content-Type itself so
 * the generated multipart boundary matches the FormData body. */
export async function apiUpload<T = unknown>(
  path: string,
  formData: FormData,
  { silent }: { silent?: boolean } = {},
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await authedFetch(
    url,
    {
      method: "POST",
      headers: { accept: "application/json" },
      body: formData,
    },
    { silent, method: "POST", path },
  );

  return parseJsonResponse<T>(res, { silent });
}

async function parseJsonResponse<T>(
  res: Response,
  { silent }: { silent?: boolean },
): Promise<T> {
  const text = await res.text();
  const json = text ? safeJSON(text) : null;

  if (!res.ok) {
    const structured = extractApiProblem(json);
    const message = resolveErrorMessage(json, structured, res.statusText);
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

/**
 * Authenticated file download (Phase 7, D-3b). `apiFetch` is JSON-only — it
 * reads the body as text — so binary exports need their own path: fetch as a
 * blob, honour the server's `Content-Disposition` filename, and trigger a
 * browser save. Errors surface a structured `ApiError` (so a 422
 * `run_not_approved` is catchable) and a toast unless `silent`.
 */
export async function apiDownload(
  path: string,
  fallbackFilename: string,
  { silent }: { silent?: boolean } = {},
): Promise<void> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

  const res = await authedFetch(url, {}, { silent, method: "GET", path });

  if (!res.ok) {
    const text = await res.text();
    const json = text ? safeJSON(text) : null;
    const structured = extractApiProblem(json);
    const message = resolveErrorMessage(json, structured, res.statusText);
    const err = new ApiError(res.status, message, json, structured ?? undefined);
    if (!silent) {
      toast.error(`${res.status} · ${friendly(res.status)}`, {
        description: toastDescription(structured, message),
      });
    }
    throw err;
  }

  let blob: Blob;
  try {
    blob = await res.blob();
  } catch (cause) {
    // P7-M2: connection dropped mid-body after 200 headers — without this
    // the click ends with no file and no feedback.
    const err = new ApiError(0, "Download interrupted — connection lost", { cause });
    if (!silent) toast.error("Download failed", { description: `GET ${path}` });
    throw err;
  }
  const filename = filenameFromDisposition(
    res.headers.get("content-disposition"),
    fallbackFilename,
  );
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(href);
}

/**
 * Shared fetch core: injects auth header, runs fetch() with network-failure
 * logging + optional toast, returns the raw Response. Both `apiFetch` and
 * `apiDownload` delegate here so their error paths stay in sync.
 */
async function authedFetch(
  url: string,
  init: RequestInit,
  { silent = false, method = "GET", path }: { silent?: boolean; method?: string; path: string },
): Promise<Response> {
  const authHeader = await getAuthHeader();
  try {
    return await fetch(url, {
      ...init,
      headers: { ...authHeader, ...(init.headers as Record<string, string> | undefined) },
    });
  } catch (cause) {
    console.error("[apiFetch] fetch() threw:", cause);
    const err = new ApiError(0, "Network error — is the API reachable?", { cause });
    if (!silent) {
      toast.error("Network error", { description: `${method} ${path}` });
    }
    throw err;
  }
}

function filenameFromDisposition(
  disposition: string | null,
  fallback: string,
): string {
  if (!disposition) return fallback;
  // Handles both `filename="x.pdf"` and RFC 5987 `filename*=UTF-8''x.pdf`.
  const star = /filename\*=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  if (star?.[1]) {
    // P7-M2: a malformed % sequence in the header must not abort the
    // download — fall back to the caller's filename.
    try {
      return decodeURIComponent(star[1]);
    } catch {
      return fallback;
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(disposition);
  return plain?.[1] ?? fallback;
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

/** Resolves the best error message from a failed response body. */
function resolveErrorMessage(
  json: unknown,
  structured: ApiProblem | null,
  statusText: string,
): string {
  return (
    structured?.message
    ?? (typeof json === "object" &&
        json !== null &&
        "detail" in json &&
        typeof (json as Record<string, unknown>).detail === "string"
      ? ((json as Record<string, unknown>).detail as string)
      : null)
    ?? statusText
    ?? "Request failed"
  );
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
