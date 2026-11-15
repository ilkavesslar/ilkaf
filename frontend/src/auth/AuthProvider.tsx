import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AuthContextProvider, type AuthContextValue, type AuthStatus, type AuthUser } from "./AuthContext";
import { authPublicConfig } from "./config";

async function postLogin(
  apiBaseUrl: string,
  email: string,
  password: string,
): Promise<AuthUser> {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    credentials: "include",
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { error?: { message?: string } };
    throw new Error(body.error?.message ?? "Sign in failed");
  }
  return (await response.json()) as AuthUser;
}

async function postLogout(apiBaseUrl: string): Promise<void> {
  await fetch(`${apiBaseUrl}/api/v1/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
    credentials: "include",
    signal: AbortSignal.timeout(5000),
  });
}

function toUser(body: AuthUser): AuthUser {
  return {
    id: body.id,
    email: body.email,
    name: body.name,
    roles: body.roles ?? [],
  };
}

async function fetchSession(apiBaseUrl: string): Promise<AuthUser | null> {
  const response = await fetch(`${apiBaseUrl}/api/v1/me`, {
    credentials: "include",
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) {
    return null;
  }
  return toUser((await response.json()) as AuthUser);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const apiBaseUrl = authPublicConfig().apiBaseUrl;
  const sessionEpoch = useRef(0);

  const getAccessToken = useCallback(async (): Promise<string> => {
    // Sessions are managed through HTTP-only cookies; no client token is needed.
    return "";
  }, []);

  const login = useCallback(
    async (email: string, password: string): Promise<void> => {
      setError(null);
      try {
        const authenticatedUser = await postLogin(apiBaseUrl, email, password);
        sessionEpoch.current += 1;
        setUser(toUser(authenticatedUser));
        setStatus("authenticated");
      } catch (err) {
        setStatus("unauthenticated");
        setUser(null);
        setError(err instanceof TypeError || err instanceof DOMException ? "The API is not reachable" : err instanceof Error ? err.message : "Sign in failed");
        throw err;
      }
    },
    [apiBaseUrl],
  );

  const logout = useCallback((): void => {
    sessionEpoch.current += 1;
    setUser(null);
    setStatus("unauthenticated");
    setError(null);
    void postLogout(apiBaseUrl);
  }, [apiBaseUrl]);

  const clearError = useCallback((): void => {
    setError(null);
  }, []);

  useEffect(() => {
    const epoch = sessionEpoch.current;
    let cancelled = false;
    void (async () => {
      try {
        const existing = await fetchSession(apiBaseUrl);
        if (cancelled || sessionEpoch.current !== epoch) {
          return;
        }
        if (existing) {
          setUser(existing);
          setStatus("authenticated");
          return;
        }
      } catch {
        // A failed restore leaves the visitor on the login form.
      }
      if (!cancelled && sessionEpoch.current === epoch) {
        setUser(null);
        setStatus("unauthenticated");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiBaseUrl]);

  const value: AuthContextValue = useMemo(
    () => ({
      status,
      user,
      error,
      getAccessToken,
      login,
      logout,
      clearError,
    }),
    [status, user, error, getAccessToken, login, logout, clearError],
  );

  return <AuthContextProvider value={value}>{children}</AuthContextProvider>;
}
