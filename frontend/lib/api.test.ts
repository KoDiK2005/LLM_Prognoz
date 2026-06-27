import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch, ApiError, clearToken, getToken, setToken } from "./api";

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("token storage", () => {
  beforeEach(() => window.localStorage.clear());

  it("round-trips through localStorage", () => {
    expect(getToken()).toBeNull();
    setToken("abc123");
    expect(getToken()).toBe("abc123");
    clearToken();
    expect(getToken()).toBeNull();
  });
});

describe("apiFetch", () => {
  beforeEach(() => {
    window.localStorage.clear();
    Object.defineProperty(window, "location", {
      value: { href: "http://localhost:3000/dashboard" },
      writable: true,
    });
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => vi.restoreAllMocks());

  it("attaches the Authorization header when a token is set", async () => {
    setToken("my-token");
    vi.mocked(fetch).mockResolvedValue(jsonResponse(200, { ok: true }));

    await apiFetch("/datasets");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init!.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer my-token");
  });

  it("omits the Authorization header when there is no token", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(200, { ok: true }));

    await apiFetch("/datasets");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init!.headers as Headers;
    expect(headers.has("Authorization")).toBe(false);
  });

  it("sets JSON content-type for a plain object body but not for FormData", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(200, {})).mockResolvedValueOnce(jsonResponse(200, {}));

    await apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ a: 1 }) });
    const jsonHeaders = vi.mocked(fetch).mock.calls[0][1]!.headers as Headers;
    expect(jsonHeaders.get("Content-Type")).toBe("application/json");

    await apiFetch("/datasets/upload", { method: "POST", body: new FormData() });
    const formHeaders = vi.mocked(fetch).mock.calls[1][1]!.headers as Headers;
    expect(formHeaders.has("Content-Type")).toBe(false);
  });

  it("throws ApiError with the backend's detail message on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(400, { detail: "Bad input" }));

    await expect(apiFetch("/datasets")).rejects.toMatchObject(
      new ApiError(400, "Bad input")
    );
  });

  it("on a 401 with an active token, clears it and redirects to /login", async () => {
    setToken("expired-token");
    vi.mocked(fetch).mockResolvedValue(jsonResponse(401, { detail: "Invalid or expired token" }));

    await expect(apiFetch("/datasets")).rejects.toBeInstanceOf(ApiError);

    expect(getToken()).toBeNull();
    expect(window.location.href).toBe("/login");
  });

  it("on a 401 with no token (e.g. bad login credentials), does not redirect", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(401, { detail: "Invalid email or password" }));

    await expect(apiFetch("/auth/login", { method: "POST", body: "{}" })).rejects.toBeInstanceOf(
      ApiError
    );

    expect(window.location.href).toBe("http://localhost:3000/dashboard");
  });

  it("returns undefined for a 204 No Content response", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }));
    await expect(apiFetch("/forecasts/123")).resolves.toBeUndefined();
  });
});
