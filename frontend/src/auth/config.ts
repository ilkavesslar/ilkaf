/** Public ILKA authentication configuration. No secrets belong here. */

export type AuthPublicConfig = {
  apiBaseUrl: string;
};

export type AuthEnv = {
  VITE_API_BASE_URL?: string;
};

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export function authPublicConfig(env: AuthEnv = import.meta.env): AuthPublicConfig {
  return {
    apiBaseUrl: env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL,
  };
}
