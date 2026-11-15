export type HealthResponse = { status?: string; service?: string };

export type HealthResult =
  | { ok: true; label: string }
  | { ok: false; label: string };

export type MeSite = {
  id: string;
  name: string;
  code?: string | null;
  role?: string | null;
};

export type MeResponse = {
  id: string;
  email: string;
  name: string;
  roles: string[];
  sites: MeSite[];
};

function apiOrigin(baseUrl: string): string {
  return baseUrl.replace(/\/api\/v1\/?$/, "");
}

export async function fetchHealth(
  baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
): Promise<HealthResult> {
  const healthUrl = `${apiOrigin(baseUrl)}/health`;
  try {
    const response = await fetch(healthUrl);
    if (!response.ok) {
      return { ok: false, label: "API offline" };
    }
    const body = (await response.json()) as HealthResponse;
    return {
      ok: true,
      label: body.status === "healthy" || body.status === "ok" ? "API online" : "API degraded",
    };
  } catch {
    return { ok: false, label: "API offline" };
  }
}

export type DemoBoundingBox = {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
};

export type DemoObservation = {
  observation_id: string;
  object_class: string;
  confidence: number;
  bounding_box: DemoBoundingBox;
  source_id: string;
  model_id: string;
  model_version: string;
  observed_at: string;
  media_timestamp: string | null;
  frame_index: number;
  is_synthetic: boolean;
  mock_label: string;
};

export type DemoSnapshot = {
  record_kind: string;
  demo_status: "empty" | "ready";
  source_status: string;
  source_id: string | null;
  source_kind: string;
  is_synthetic: boolean;
  mock_label: string;
  frames_processed: number;
  model_id: string | null;
  model_version: string | null;
  observations: DemoObservation[];
};

export type AccessTokenProvider = () => Promise<string>;

export type DemoClientResult =
  | { kind: "unauthorized" }
  | { kind: "forbidden" }
  | { kind: "offline" }
  | { kind: "error"; message: string }
  | { kind: "ok"; snapshot: DemoSnapshot };

function demoUrl(baseUrl: string, suffix = ""): string {
  const origin = apiOrigin(baseUrl);
  return `${origin}/api/v1/demo/person-observations${suffix}`;
}

async function demoResult(response: Response): Promise<DemoClientResult> {
  if (response.status === 401) {
    return { kind: "unauthorized" };
  }
  if (response.status === 403) {
    return { kind: "forbidden" };
  }
  if (!response.ok) {
    let message = "The demo observations request failed";
    try {
      const body = (await response.json()) as { error?: { message?: string } };
      if (typeof body.error?.message === "string" && body.error.message.length < 200) {
        message = body.error.message;
      }
    } catch {
      message = "The demo observations request failed";
    }
    return { kind: "error", message };
  }
  const snapshot = (await response.json()) as DemoSnapshot;
  return { kind: "ok", snapshot };
}

async function authorized(
  getAccessToken: AccessTokenProvider,
  request: (token: string) => Promise<Response>,
): Promise<DemoClientResult> {
  let token = "";
  try {
    token = await getAccessToken();
  } catch {
    return { kind: "unauthorized" };
  }
  if (!token) {
    // Sessions are HTTP-only cookies; send the request with credentials.
    try {
      return await demoResult(await request(token));
    } catch {
      return { kind: "offline" };
    }
  }
  try {
    return await demoResult(
      await request(token),
    );
  } catch {
    return { kind: "offline" };
  }
}

export async function fetchDemoObservations(
  getAccessToken: AccessTokenProvider,
  baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
): Promise<DemoClientResult> {
  return authorized(getAccessToken, (token) =>
    fetch(demoUrl(baseUrl), {
      credentials: "include",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }),
  );
}

export async function runDemoObservations(
  getAccessToken: AccessTokenProvider,
  baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
): Promise<DemoClientResult> {
  return authorized(getAccessToken, (token) =>
    fetch(demoUrl(baseUrl, "/runs"), {
      method: "POST",
      credentials: "include",
      headers: token
        ? {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          }
        : { "Content-Type": "application/json" },
      body: JSON.stringify({ max_frames: 30 }),
    }),
  );
}

export async function fetchMe(
  getAccessToken: AccessTokenProvider,
  baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
): Promise<MeResponse | null> {
  const origin = apiOrigin(baseUrl);
  let token = "";
  try {
    token = await getAccessToken();
  } catch {
    return null;
  }
  if (!token) {
    try {
      const response = await fetch(`${origin}/api/v1/me`, {
        credentials: "include",
      });
      if (!response.ok) {
        return null;
      }
      return (await response.json()) as MeResponse;
    } catch {
      return null;
    }
  }
  try {
    const response = await fetch(`${origin}/api/v1/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as MeResponse;
  } catch {
    return null;
  }
}
