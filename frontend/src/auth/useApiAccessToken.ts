import { useCallback } from "react";
import type { AccessTokenProvider } from "../services/api";
import { useAuth } from "./useAuth";

export type ReadyApiAccess = {
  status: "loading" | "anonymous" | "ready";
  getAccessToken: AccessTokenProvider;
};

/** Bridges the custom auth context to the API client token provider interface. */
export function useConfiguredAccessToken(): ReadyApiAccess {
  const { status, getAccessToken } = useAuth();

  const provider = useCallback(async (): Promise<string> => {
    // An empty string means the session cookie is sent with the request.
    return getAccessToken();
  }, [getAccessToken]);

  if (status === "loading") {
    return { status: "loading", getAccessToken: provider };
  }
  if (status !== "authenticated") {
    return { status: "anonymous", getAccessToken: provider };
  }
  return { status: "ready", getAccessToken: provider };
}
