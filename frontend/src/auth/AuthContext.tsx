import { createContext, useContext, type ReactNode } from "react";

export type AuthStatus = "loading" | "unauthenticated" | "authenticated";

export type AuthUser = {
  id: string;
  email: string;
  name: string;
  roles: string[];
};

export type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  error: string | null;
  /** Request a bearer token for API calls. Throws when unauthenticated. */
  getAccessToken: () => Promise<string>;
  /** Start a session with email and password. Password is not retained. */
  login: (email: string, password: string) => Promise<void>;
  /** End the current session. */
  logout: () => void;
  /** Clear transient errors. */
  clearError: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuthContext(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuthContext must be used inside AuthProvider");
  }
  return value;
}

export function AuthContextProvider({
  value,
  children,
}: {
  value: AuthContextValue;
  children: ReactNode;
}) {
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
