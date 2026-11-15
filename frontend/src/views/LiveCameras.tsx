import { useEffect, useRef, useState, type ReactNode } from "react";
import { DetectionOverlay, type OverlayObservation } from "../components/DetectionOverlay";
import { toOverlayObservation, type PublicObservation } from "../components/publicObservation";
import { SafetyInsights, type CapabilityStatus, type PipelineStatus } from "../components/SafetyInsights";
import type { AccessTokenProvider } from "../services/api";

export type LiveCameraStatus = "loading" | "live" | "disconnected" | "error" | "unauthorized" | "idle";

export type LiveCameraInfo = {
  camera_id: string;
  name: string;
  host: string;
  source_id: string;
  state: string;
  last_frame_at: string | null;
  error: string | null;
  frame_width?: number | null;
  frame_height?: number | null;
};

const CAMERAS = [
  { cameraId: "vigi-c320i-192.168.1.17", name: "Camera 01", host: "192.168.1.13" },
  { cameraId: "vigi-c320i-192.168.1.18", name: "Camera 02", host: "192.168.1.15" },
];

function origin(baseUrl: string): string {
  return baseUrl.replace(/\/api\/v1\/?$/, "");
}

function concat(
  left: Uint8Array<ArrayBufferLike>,
  right: Uint8Array<ArrayBufferLike>,
): Uint8Array<ArrayBuffer> {
  const merged = new Uint8Array(left.byteLength + right.byteLength);
  merged.set(left);
  merged.set(right, left.byteLength);
  return merged;
}

function findHeaderEnd(buffer: Uint8Array<ArrayBufferLike>): number {
  for (let index = 0; index < buffer.length - 3; index += 1) {
    if (
      buffer[index] === 13 &&
      buffer[index + 1] === 10 &&
      buffer[index + 2] === 13 &&
      buffer[index + 3] === 10
    ) {
      return index;
    }
  }
  return -1;
}

export function LiveCameraCard({
  name,
  host,
  sourceId,
  status,
  lastFrame,
  connection,
  message,
  onRetry,
  onFocus,
  focusLabel,
  showControls = true,
  site,
  aiStatus,
  observations = [],
  imageWidth,
  imageHeight,
  children,
}: {
  name: string;
  host: string;
  sourceId: string;
  status: LiveCameraStatus;
  lastFrame: string | null;
  connection?: string;
  message?: string;
  onRetry?: () => void;
  onFocus?: () => void;
  focusLabel?: string;
  showControls?: boolean;
  site?: string | null;
  aiStatus?: string;
  observations?: OverlayObservation[];
  imageWidth?: number | null;
  imageHeight?: number | null;
  children?: ReactNode;
}) {
  let stageNote = "";
  if (status === "loading") stageNote = "Loading live preview…";
  if (status === "idle") stageNote = "The live stream is not open from this page.";
  if (status === "disconnected") stageNote = message ?? "Live preview is unavailable.";
  if (status === "error") stageNote = message ?? "The camera stream reported an error.";
  if (status === "unauthorized") stageNote = "Sign in is required to view this camera.";
  return (
    <article className="live-card">
      <h2>
        {name} — {host}
      </h2>
      <p>Source: {sourceId}</p>
      <p>Site: {site ?? "not reported"}</p>
      <p>Status: {status}</p>
      {connection ? <p>Connection: {connection}</p> : null}
      <p>Last frame: {lastFrame ?? "none"}</p>
      {aiStatus ? <p>AI: {aiStatus}</p> : null}
      <div className="stage">
        {children}
        <DetectionOverlay observations={observations} imageWidth={imageWidth} imageHeight={imageHeight} />
        {stageNote ? <p className="stage-note">{stageNote}</p> : null}
      </div>
      {onFocus ? (
        <button type="button" onClick={onFocus}>
          {focusLabel ?? "Focus"}
        </button>
      ) : null}
      {showControls ? (
        <>
          <button type="button" onClick={onRetry} disabled={!onRetry}>
            Retry
          </button>
          <button
            type="button"
            onClick={(event) => {
              const card = event.currentTarget.closest("article");
              if (card && document.fullscreenElement === card) {
                void document.exitFullscreen();
              } else if (card) {
                void card.requestFullscreen();
              }
            }}
          >
            Full screen
          </button>
        </>
      ) : null}
    </article>
  );
}

export function LiveCameras({
  getAccessToken,
  baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  streams = true,
  workspace = false,
}: {
  getAccessToken: AccessTokenProvider | null;
  baseUrl?: string;
  streams?: boolean;
  workspace?: boolean;
}) {
  if (!getAccessToken) {
    return (
      <section className="live-section">
        <h2>Live camera monitoring</h2>
        <div className={workspace ? "monitor" : undefined}>
          <div className="live-grid">
            {CAMERAS.map((camera) => (
              <LiveCameraCard
                key={camera.cameraId}
                name={camera.name}
                host={camera.host}
                sourceId={camera.cameraId}
                status="unauthorized"
                lastFrame={null}
                message="Live preview is unavailable."
              />
            ))}
          </div>
          {workspace ? (
            <SafetyInsights
              status="not_connected"
              detail="Live AI detection is not currently connected."
              cameraName={null}
              observations={[]}
              capabilities={[]}
            />
          ) : null}
        </div>
      </section>
    );
  }
  return (
    <LiveCameraSessions
      getAccessToken={getAccessToken}
      baseUrl={baseUrl}
      streams={streams}
      workspace={workspace}
    />
  );
}

type DetectionFeed = {
  pipeline: PipelineStatus;
  detail: string;
  capabilities: CapabilityStatus[];
  aiStatus: string;
};

function LiveCameraSessions({
  getAccessToken,
  baseUrl,
  streams,
  workspace,
}: {
  getAccessToken: AccessTokenProvider;
  baseUrl: string;
  streams: boolean;
  workspace: boolean;
}) {
  const [cameras, setCameras] = useState<LiveCameraInfo[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  const [detection, setDetection] = useState<DetectionFeed>({
    pipeline: "not_connected",
    detail: "Live AI detection is not currently connected.",
    capabilities: [],
    aiStatus: "Live AI detection is not currently connected.",
  });
  const [feeds, setFeeds] = useState<
    Record<string, { pipeline: PipelineStatus; detail: string; items: OverlayObservation[] }>
  >({});

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    void (async () => {
      try {
        const token = await getAccessToken();
        const response = await fetch(`${origin(baseUrl)}/api/v1/lab/cameras`, {
          credentials: "include",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: controller.signal,
        });
        if (cancelled) {
          return;
        }
        if (response.status === 401) {
          setProblem("unauthorized");
          return;
        }
        if (!response.ok) {
          setProblem(
            response.status === 404
              ? "Live preview is not enabled on this server."
              : "Camera list is unavailable.",
          );
          return;
        }
        const body = (await response.json()) as { cameras?: LiveCameraInfo[] };
        setCameras(body.cameras ?? []);
      } catch {
        if (!cancelled && !controller.signal.aborted) {
          setProblem("Camera list is unavailable.");
        }
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [baseUrl, getAccessToken]);

  useEffect(() => {
    if (!workspace) {
      return;
    }
    const controller = new AbortController();
    let cancelled = false;
    void (async () => {
      try {
        const token = await getAccessToken();
        const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
        const capabilitiesResponse = await fetch(`${origin(baseUrl)}/api/v1/detection/capabilities`, {
          credentials: "include",
          headers,
          signal: controller.signal,
        });
        if (cancelled) {
          return;
        }
        if (!capabilitiesResponse.ok) {
          setDetection((current) => ({
            ...current,
            capabilities: [],
            aiStatus: "Live AI detection is not currently connected.",
          }));
          return;
        }
        const capabilitiesBody = (await capabilitiesResponse.json()) as {
          capabilities?: { label: string; status: string; detail: string }[];
        };
        const capabilities = capabilitiesBody.capabilities ?? [];
        const person = capabilities.find((item) => item.label === "Person detection");
        setDetection((current) => ({
          ...current,
          capabilities,
          aiStatus: person?.detail ?? "Live AI detection is not currently connected.",
        }));
      } catch {
        if (!cancelled && !controller.signal.aborted) {
          setDetection({
            pipeline: "not_connected",
            detail: "Live AI detection is not currently connected.",
            capabilities: [],
            aiStatus: "Live AI detection is not currently connected.",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [baseUrl, getAccessToken, workspace]);

  useEffect(() => {
    if (!workspace || !cameras || cameras.length === 0) {
      return;
    }
    const controller = new AbortController();
    let cancelled = false;
    let inFlight = false;
    const load = async () => {
      if (inFlight) {
        return;
      }
      inFlight = true;
      try {
        const token = await getAccessToken();
        const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
        const entries = await Promise.all(
          cameras.map(async (camera) => {
            try {
              const response = await fetch(
                `${origin(baseUrl)}/api/v1/detection/observations?camera_id=${encodeURIComponent(camera.camera_id)}`,
                { credentials: "include", headers, signal: controller.signal },
              );
              if (!response.ok) {
                return [
                  camera.camera_id,
                  { pipeline: "not_connected" as const, detail: "", items: [] },
                ] as const;
              }
              const body = (await response.json()) as {
                status?: PipelineStatus;
                detail?: string;
                items?: PublicObservation[];
              };
              const pipeline =
                body.status === "ready" || body.status === "error" ? body.status : "not_connected";
              const items = pipeline === "ready" ? (body.items ?? []).map(toOverlayObservation) : [];
              return [camera.camera_id, { pipeline, detail: body.detail ?? "", items }] as const;
            } catch {
              return [
                camera.camera_id,
                { pipeline: "not_connected" as const, detail: "", items: [] },
              ] as const;
            }
          }),
        );
        if (!cancelled) {
          setFeeds(Object.fromEntries(entries));
        }
      } finally {
        inFlight = false;
      }
    };
    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      controller.abort();
    };
  }, [baseUrl, cameras, getAccessToken, workspace]);

  if (problem === "unauthorized") {
    return (
      <section className="live-section">
        <h2>Live camera monitoring</h2>
        <div className="live-grid">
          {CAMERAS.map((camera) => (
            <LiveCameraCard
              key={camera.cameraId}
              name={camera.name}
              host={camera.host}
              sourceId={camera.cameraId}
              status="unauthorized"
              lastFrame={null}
            />
          ))}
        </div>
      </section>
    );
  }

  const visible = cameras?.filter((camera) => !focusId || camera.camera_id === focusId) ?? [];
  const focused = cameras?.find((camera) => camera.camera_id === focusId) ?? null;

  return (
    <section className="live-section">
      <h2>Live camera monitoring</h2>
      <p className="muted">Development MJPEG preview. RTSP credentials stay on the server.</p>
      {problem ? <p role="alert">{problem}</p> : null}
      {!problem && !cameras ? <p>Loading cameras…</p> : null}
      {cameras && cameras.length === 0 ? <p>No lab cameras are configured.</p> : null}
      {focusId ? (
        <button type="button" onClick={() => setFocusId(null)}>
          Back to grid
        </button>
      ) : null}
      <div className={workspace ? "monitor" : undefined}>
        <div className={focusId ? "live-grid focused" : "live-grid"}>
          {visible.map((camera) =>
            streams ? (
              <LiveCameraSession
                key={camera.camera_id}
                cameraId={camera.camera_id}
                name={camera.name}
                host={camera.host}
                connection={camera.state}
                getAccessToken={getAccessToken}
                baseUrl={baseUrl}
                observations={feeds[camera.camera_id]?.items ?? []}
                imageWidth={camera.frame_width}
                imageHeight={camera.frame_height}
                aiStatus={workspace ? detection.aiStatus : undefined}
                onFocus={
                  workspace
                    ? () => setFocusId(focusId === camera.camera_id ? null : camera.camera_id)
                    : undefined
                }
                focusLabel={focusId === camera.camera_id ? "Leave focus" : "Focus"}
              />
            ) : (
              <LiveCameraCard
                key={camera.camera_id}
                name={camera.name}
                host={camera.host}
                sourceId={camera.source_id}
                status={camera.state === "live" ? "live" : camera.state === "error" ? "error" : "idle"}
                connection={camera.state}
                lastFrame={camera.last_frame_at}
                message={camera.error ?? "Live preview is unavailable."}
                showControls={false}
                observations={feeds[camera.camera_id]?.items ?? []}
                imageWidth={camera.frame_width}
                imageHeight={camera.frame_height}
                aiStatus={workspace ? detection.aiStatus : undefined}
                onFocus={
                  workspace
                    ? () => setFocusId(focusId === camera.camera_id ? null : camera.camera_id)
                    : undefined
                }
                focusLabel={focusId === camera.camera_id ? "Leave focus" : "Focus"}
              />
            ),
          )}
        </div>
        {workspace ? (
          <SafetyInsights
            status={focused ? (feeds[focused.camera_id]?.pipeline ?? "not_connected") : "not_connected"}
            detail={focused ? (feeds[focused.camera_id]?.detail || detection.detail) : detection.detail}
            cameraName={focused?.name ?? null}
            observations={focused ? (feeds[focused.camera_id]?.items ?? []) : []}
            capabilities={detection.capabilities}
          />
        ) : null}
      </div>
    </section>
  );
}

function LiveCameraSession({
  cameraId,
  name,
  host,
  connection,
  getAccessToken,
  baseUrl,
  onFocus,
  focusLabel,
  aiStatus,
  observations = [],
  imageWidth,
  imageHeight,
}: {
  cameraId: string;
  name: string;
  host: string;
  connection: string;
  getAccessToken: AccessTokenProvider;
  baseUrl: string;
  onFocus?: () => void;
  focusLabel?: string;
  aiStatus?: string;
  observations?: OverlayObservation[];
  imageWidth?: number | null;
  imageHeight?: number | null;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState<LiveCameraStatus>("loading");
  const [lastFrame, setLastFrame] = useState<string | null>(null);
  const [message, setMessage] = useState<string | undefined>(undefined);
  const [seenSize, setSeenSize] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setStatus("loading");
    void (async () => {
      try {
        const token = await getAccessToken();
        const response = await fetch(`${origin(baseUrl)}/api/v1/lab/cameras/${cameraId}/mjpeg`, {
          credentials: "include",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: controller.signal,
        });
        if (response.status === 401) {
          if (!cancelled) setStatus("unauthorized");
          return;
        }
        if (!response.ok || !response.body) {
          if (!cancelled) {
            setStatus(response.status === 403 ? "error" : "disconnected");
            setMessage(response.status === 403 ? "This account cannot view this camera." : "Camera disconnected.");
          }
          return;
        }
        if (!cancelled) setStatus("live");
        const reader = response.body.getReader();
        let buffer = new Uint8Array(0);
        while (!cancelled) {
          const chunk = await reader.read();
          if (chunk.done) break;
          buffer = concat(buffer, chunk.value);
          if (buffer.length > 2_000_000) {
            buffer = buffer.slice(-1_000_000);
          }
          const headerEnd = findHeaderEnd(buffer);
          if (headerEnd < 0) continue;
          const header = new TextDecoder().decode(buffer.slice(0, headerEnd));
          const lengthMatch = /Content-Length:\s*(\d+)/i.exec(header);
          if (!lengthMatch) continue;
          const length = Number(lengthMatch[1]);
          const start = headerEnd + 4;
          if (buffer.length < start + length) continue;
          const jpeg = buffer.slice(start, start + length);
          buffer = buffer.slice(start + length);
          const blob = new Blob([jpeg], { type: "image/jpeg" });
          const bitmap = await createImageBitmap(blob);
          const canvas = canvasRef.current;
          if (canvas) {
            canvas.width = bitmap.width;
            canvas.height = bitmap.height;
            canvas.getContext("2d")?.drawImage(bitmap, 0, 0);
            setSeenSize((current) =>
              current?.width === bitmap.width && current.height === bitmap.height
                ? current
                : { width: bitmap.width, height: bitmap.height },
            );
          }
          bitmap.close();
          if (!cancelled) setLastFrame(new Date().toISOString());
        }
        if (!cancelled) setStatus("disconnected");
      } catch {
        if (!cancelled && !controller.signal.aborted) setStatus("disconnected");
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [attempt, baseUrl, cameraId, getAccessToken]);

  return (
    <LiveCameraCard
      name={name}
      host={host}
      sourceId={cameraId}
      status={status}
      connection={connection}
      lastFrame={lastFrame}
      message={message ?? "Live preview is unavailable."}
      onRetry={() => setAttempt((value) => value + 1)}
      onFocus={onFocus}
      focusLabel={focusLabel}
      aiStatus={aiStatus}
      observations={observations}
      imageWidth={seenSize?.width ?? imageWidth}
      imageHeight={seenSize?.height ?? imageHeight}
    >
      <canvas ref={canvasRef} className="live-canvas" />
    </LiveCameraCard>
  );
}
