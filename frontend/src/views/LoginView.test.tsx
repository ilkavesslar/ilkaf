import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthProvider";
import { LoginView } from "./LoginView";

const fetchMock = vi.fn();

describe("LoginView", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("renders an ILKA-branded email and password form", () => {
    render(
      <AuthProvider>
        <LoginView />
      </AuthProvider>,
    );
    expect(screen.getByRole("heading", { name: "Sign in to ILKA" })).toBeTruthy();
    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByLabelText("Password")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeTruthy();
  });

  it("does not enable sign in until both fields have values", () => {
    render(
      <AuthProvider>
        <LoginView />
      </AuthProvider>,
    );
    const button = screen.getByRole("button", { name: "Sign in" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "user@example.com" } });
    expect(button.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password" } });
    expect(button.disabled).toBe(false);
  });

  it("reports the skeleton status when the backend login endpoint is not implemented", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 501,
      json: async () => ({ error: { message: "Authentication setup in progress" } }),
    });
    render(
      <AuthProvider>
        <LoginView />
      </AuthProvider>,
    );
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toBe("Authentication setup in progress");
    });
  });

  it("does not write the password to browser storage", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    render(
      <AuthProvider>
        <LoginView />
      </AuthProvider>,
    );
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeTruthy();
    });
    expect(setItem).not.toHaveBeenCalled();
    setItem.mockRestore();
  });
});
