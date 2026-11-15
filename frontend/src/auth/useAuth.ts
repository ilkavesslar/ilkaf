import { useAuthContext, type AuthContextValue } from "./AuthContext";

/** React hook for ILKA custom authentication state. */
export function useAuth(): AuthContextValue {
  return useAuthContext();
}
