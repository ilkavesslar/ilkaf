import type { OverlayObservation } from "./DetectionOverlay";

export type PipelineStatus = "loading" | "not_connected" | "ready" | "processing" | "error";

export type CapabilityStatus = {
  label: string;
  status: string;
  detail: string;
};

export function insightMessage(status: PipelineStatus, detail: string, count: number): string {
  if (status === "loading") {
    return "Checking AI status…";
  }
  if (status === "not_connected") {
    return "Live AI detection is not currently connected.";
  }
  if (status === "processing") {
    return "Detection is processing.";
  }
  if (status === "error") {
    return detail || "Live AI detection reported an error.";
  }
  if (count === 0) {
    return "No active observations.";
  }
  return `${count} active observations.`;
}

export function SafetyInsights({
  status,
  detail,
  cameraName,
  observations,
  capabilities,
}: {
  status: PipelineStatus;
  detail: string;
  cameraName: string | null;
  observations: OverlayObservation[];
  capabilities: CapabilityStatus[];
}) {
  const message = insightMessage(status, detail, observations.length);
  return (
    <section className="insights" aria-live="polite">
      <h2>Live safety insights</h2>
      <p>{message}</p>
      <p>Camera: {cameraName ?? "No camera selected."}</p>
      {status === "ready"
        ? observations.map((item) => (
            <article key={item.id} className="observation">
              <p>{item.label}</p>
              <p>{Math.round(item.confidence * 100)}% confidence</p>
              <p>Time: {item.observedAt ?? "not reported"}</p>
            </article>
          ))
        : null}
      {capabilities.length > 0 ? (
        <ul className="capability-list">
          {capabilities.map((item) => (
            <li key={item.label}>
              {item.label}: {item.status}. {item.detail}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
