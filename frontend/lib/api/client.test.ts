import { afterEach, describe, expect, it, vi } from "vitest";

import { apiUpload } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiUpload", () => {
  it("sends FormData without overriding the browser multipart boundary", async () => {
    const form = new FormData();
    form.append("file_type", "agreement");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "document-1" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiUpload("/api/contracts/contract-1/documents", form);

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.body).toBe(form);
    expect(init.headers).not.toHaveProperty("content-type");
  });
});
