import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchDemoObservations, fetchHealth, fetchMe, runDemoObservations } from "./api";

describe("fetchHealth", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reports online when /health is healthy", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "healthy" }),
      }),
    );
    await expect(fetchHealth("http://localhost:8000")).resolves.toEqual({
      ok: true,
      label: "API online",
    });
  });

  it("reports offline when the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(fetchHealth("http://localhost:8000")).resolves.toEqual({
      ok: false,
      label: "API offline",
    });
  });

  it("reports offline when the status is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, json: async () => ({}) }));
    await expect(fetchHealth("http://localhost:8000")).resolves.toEqual({
      ok: false,
      label: "API offline",
    });
  });
});

describe("fetchMe", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the current user when authorized", async () => {
    const me = {
      id: "user-1",
      email: "user@example.com",
      name: "Example User",
      roles: ["VIEWER"],
      sites: [{ id: "site-1", name: "Main Factory", role: "VIEWER" }],
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => me,
    });
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchMe(async () => "token-value", "http://localhost:8000")).resolves.toEqual(me);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/me",
      expect.objectContaining({
        headers: { Authorization: "Bearer token-value" },
      }),
    );
  });

  it("returns null when unauthenticated", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({}) }),
    );
    await expect(fetchMe(async () => "bad", "http://localhost:8000")).resolves.toBeNull();
  });
});

describe("demo observations client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the session cookie when no bearer token is present", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({}),
    });
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchDemoObservations(async () => "", "http://localhost:8000")).resolves.toEqual({
      kind: "unauthorized",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/demo/person-observations",
      expect.objectContaining({ credentials: "include", headers: {} }),
    );
  });

  it("returns an empty snapshot from the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ demo_status: "empty", observations: [] }),
      }),
    );
    const result = await fetchDemoObservations(async () => "token-value", "http://localhost:8000");
    expect(result.kind).toBe("ok");
    if (result.kind === "ok") {
      expect(result.snapshot.demo_status).toBe("empty");
    }
  });

  it("reports offline when the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(runDemoObservations(async () => "token-value", "http://localhost:8000")).resolves.toEqual({
      kind: "offline",
    });
  });

  it("reports forbidden without inventing observations", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 403, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);
    const getAccessToken = vi.fn(async () => "api-access-token");
    await expect(fetchDemoObservations(getAccessToken, "http://localhost:8000")).resolves.toEqual({
      kind: "forbidden",
    });
    expect(getAccessToken).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/demo/person-observations",
      expect.objectContaining({
        headers: { Authorization: "Bearer api-access-token" },
      }),
    );
  });
});
