import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "./auth/AuthProvider";
import App from "./App";

const fetchMock = vi.fn();

describe("authenticated shell", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("restores a viewer session and shows the lab cameras", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      const target = String(url);
      if (target.endsWith("/api/v1/me")) {
        return {
          ok: true,
          json: async () => ({
            id: "1",
            email: "ada@example.com",
            name: "Ada",
            roles: ["VIEWER"],
            sites: [],
          }),
        };
      }
      if (target.endsWith("/health")) {
        return { ok: true, json: async () => ({ status: "healthy" }) };
      }
      if (target.endsWith("/api/v1/demo/person-observations")) {
        return {
          ok: true,
          json: async () => ({
            record_kind: "person_observation_demo",
            demo_status: "empty",
            source_status: "local_mp4_demo",
            source_id: null,
            source_kind: "file",
            is_synthetic: true,
            mock_label: "[MOCK / SYNTHETIC]",
            frames_processed: 0,
            model_id: null,
            model_version: null,
            observations: [],
          }),
        };
      }
      if (target.endsWith("/api/v1/lab/cameras")) {
        return {
          ok: true,
          json: async () => ({
            cameras: [
              {
                camera_id: "vigi-c320i-192.168.1.17",
                name: "Camera 01",
                host: "192.168.1.13",
                source_id: "vigi-c320i-192.168.1.17",
                state: "idle",
                last_frame_at: null,
                error: null,
              },
              {
                camera_id: "vigi-c320i-192.168.1.18",
                name: "Camera 02",
                host: "192.168.1.15",
                source_id: "vigi-c320i-192.168.1.18",
                state: "idle",
                last_frame_at: null,
                error: null,
              },
            ],
          }),
        };
      }
      return { ok: false, status: 404, json: async () => ({}), body: null };
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Ada")).toBeTruthy();
    });
    expect(screen.getByText("VIEWER")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cameras" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Incidents" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Settings" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Sign in" })).toBeNull();
    await waitFor(() => {
      expect(screen.getByText("Camera 01 — 192.168.1.13")).toBeTruthy();
      expect(screen.getByText("Camera 02 — 192.168.1.15")).toBeTruthy();
    });
    const meCall = fetchMock.mock.calls.find((call) => String(call[0]).endsWith("/api/v1/me"));
    expect(meCall?.[1]).toEqual(expect.objectContaining({ credentials: "include" }));
  });

  it("shows the login form when the session cookie is missing", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 401, json: async () => ({}) });
    render(
      <MemoryRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in to ILKA" })).toBeTruthy();
    });
    expect(screen.queryByRole("link", { name: "Dashboard" })).toBeNull();
  });
});
