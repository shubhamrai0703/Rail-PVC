import { toast } from "sonner";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
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
 * - 4xx/5xx → throws ApiError; also surfaces a Sonner toast (unless silent)
 * - Network failure → throws ApiError(status=0); toast
 */
export async function apiFetch<T = unknown>(
  path: string,
  { body, silent, headers, ...init }: RequestOptions = {},
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        "content-type": "application/json",
        accept: "application/json",
        ...headers,
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
    const detail =
      (typeof json === "object" && json && "detail" in json && typeof json.detail === "string"
        ? json.detail
        : null) ?? res.statusText ?? "Request failed";
    const err = new ApiError(res.status, detail, json);
    if (!silent) {
      toast.error(`${res.status} · ${friendly(res.status)}`, {
        description: detail,
      });
    }
    throw err;
  }

  return json as T;
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
