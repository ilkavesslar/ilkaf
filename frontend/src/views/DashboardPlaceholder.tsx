import { useEffect, useState } from "react";
import { useAuth } from "../auth/useAuth";
import { useConfiguredAccessToken } from "../auth/useApiAccessToken";
import {
  type DemoClientResult,
  type DemoSnapshot,
  fetchDemoObservations,
  runDemoObservations,
} from "../services/api";
import { mapNormalizedBox } from "../components/detectionGeometry";
import { LiveCameras } from "./LiveCameras";

export type DashboardState =
  | { kind: "loading" }
  | { kind: "offline" }
  | { kind: "unauthorized" }
  | { kind: "forbidden" }
  | { kind: "error"; message: string }
  | { kind: "empty"; snapshot: DemoSnapshot }
  | { kind: "ready"; snapshot: DemoSnapshot };

function fromResult(result: DemoClientResult): DashboardState {
  if (result.kind === "ok") {
    return result.snapshot.demo_status === "ready"
      ? { kind: "ready", snapshot: result.snapshot }
      : { kind: "empty", snapshot: result.snapshot };
  }
  if (result.kind === "error") {
    return { kind: "error", message: result.message };
  }
  return { kind: result.kind };
}

export function DashboardView({
  state,
  onRefresh,
  onRerun,
  onSignOut,
}: {
  state: DashboardState;
  onRefresh?: () => void;
  onRerun?: () => void;
  onSignOut?: () => void;
}) {
  const snapshot = state.kind === "ready" || state.kind === "empty" ? state.snapshot : null;
  return (
    <section className="demo">
      <h2>Person observations</h2>
      <p className="demo-banner">
        ILKA demo mode. Local file demo. These person observations are not live camera detections.
      </p>
      <p>
        Source label: <strong>[MOCK / SYNTHETIC]</strong>
      </p>
      <p className="muted">Person observations are not incidents.</p>
      <div className="demo-actions">
        <button type="button" onClick={onRefresh} disabled={!onRefresh || state.kind === "loading"}>
          Refresh
        </button>
        <button type="button" onClick={onRerun} disabled={!onRerun || state.kind === "loading"}>
          Run 30-frame demo
        </button>
        {onSignOut ? (
          <button type="button" onClick={onSignOut}>
            Sign out
          </button>
        ) : null}
      </div>
      {state.kind === "loading" ? <p>Loading demo observations…</p> : null}
      {state.kind === "offline" ? <p>API offline. Demo observations are unavailable.</p> : null}
      {state.kind === "unauthorized" ? (
        <p>Sign in is required before this dashboard can load observations.</p>
      ) : null}
      {state.kind === "forbidden" ? (
        <p>This account cannot read or run demo person observations.</p>
      ) : null}
      {state.kind === "error" ? <p>{state.message}</p> : null}
      {snapshot ? (
        <>
          <p>
            Source status: {snapshot.source_status}. Source ID: {snapshot.source_id ?? "none"}.
            Frames processed: {snapshot.frames_processed}. Observations:{" "}
            {snapshot.observations.length}.
          </p>
          {snapshot.model_id ? (
            <p>
              Model: {snapshot.model_id} {snapshot.model_version}
            </p>
          ) : null}
        </>
      ) : null}
      {state.kind === "empty" ? <p>No demo run yet.</p> : null}
      {state.kind === "ready"
        ? state.snapshot.observations.map((item) => {
            const box = item.bounding_box;
            return (
              <article key={item.observation_id} className="observation">
                <h2>Person observation</h2>
                <p>{item.mock_label}</p>
                <p>Confidence: {item.confidence.toFixed(2)}</p>
                <p>
                  Model: {item.model_id} {item.model_version}
                </p>
                <p>Frame: {item.frame_index}</p>
                <p>Media timestamp: {item.media_timestamp ?? "unavailable"}</p>
                <p>
                  Box: {box.x_min.toFixed(3)}, {box.y_min.toFixed(3)}, {box.x_max.toFixed(3)},{" "}
                  {box.y_max.toFixed(3)}
                </p>
                <div className="box-preview" aria-hidden="true">
                  <span
                    className="box-preview-rect"
                    style={mapNormalizedBox(
                      { xMin: box.x_min, yMin: box.y_min, xMax: box.x_max, yMax: box.y_max },
                      16,
                      9,
                    )}
                  />
                </div>
              </article>
            );
          })
        : null}
    </section>
  );
}

export function DashboardPlaceholder() {
  const { status } = useAuth();
  if (status !== "authenticated") {
    return (
      <>
        <DashboardView state={{ kind: "unauthorized" }} />
        <LiveCameras getAccessToken={null} />
      </>
    );
  }
  return <DashboardSession showCameras />;
}

export function ObservationsPage() {
  const { status } = useAuth();
  if (status !== "authenticated") {
    return <DashboardView state={{ kind: "unauthorized" }} />;
  }
  return <DashboardSession showCameras={false} />;
}

function DashboardSession({ showCameras }: { showCameras: boolean }) {
  const access = useConfiguredAccessToken();
  const { logout } = useAuth();
  const [state, setState] = useState<DashboardState>({ kind: "loading" });
  const ready = access.status === "ready";
  const getAccessToken = access.getAccessToken;

  useEffect(() => {
    if (access.status === "loading") {
      setState({ kind: "loading" });
      return;
    }
    if (access.status !== "ready") {
      setState({ kind: "unauthorized" });
      return;
    }
    let cancelled = false;
    void fetchDemoObservations(getAccessToken).then((result) => {
      if (cancelled) {
        return;
      }
      if (result.kind === "unauthorized") {
        logout();
      }
      setState(fromResult(result));
    });
    return () => {
      cancelled = true;
    };
  }, [access.status, getAccessToken, logout]);

  async function refresh() {
    setState({ kind: "loading" });
    const result = await fetchDemoObservations(getAccessToken);
    if (result.kind === "unauthorized") {
      logout();
    }
    setState(fromResult(result));
  }

  async function rerun() {
    setState({ kind: "loading" });
    const result = await runDemoObservations(getAccessToken);
    if (result.kind === "unauthorized") {
      logout();
    }
    setState(fromResult(result));
  }

  return (
    <>
      <header className="page-header">
        <h1>{showCameras ? "Dashboard" : "Observations"}</h1>
        <p className="muted">
          Person observations are a local file demo. They are not incidents and they are not live
          camera detections.
        </p>
      </header>
      {showCameras ? (
        <LiveCameras getAccessToken={ready ? getAccessToken : null} streams={false} />
      ) : null}
      <DashboardView
        state={state}
        onRefresh={ready ? () => void refresh() : undefined}
        onRerun={ready ? () => void rerun() : undefined}
      />
    </>
  );
}
