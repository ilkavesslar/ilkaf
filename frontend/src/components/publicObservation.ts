import type { OverlayObservation } from "./DetectionOverlay";

export type PublicObservation = {
  observation_id: string;
  camera_id: string;
  object_class: string;
  confidence: number;
  bounding_box: {
    x_min: number;
    y_min: number;
    x_max: number;
    y_max: number;
  };
  observed_at: string;
  track_id?: number | null;
  moving?: boolean;
  waving?: boolean;
};

export function activityLabel(item: PublicObservation): string {
  const confidence = `${Math.round(item.confidence * 100)}%`;
  if (typeof item.track_id !== "number" || item.track_id < 1) {
    return `${item.object_class} ${confidence}`;
  }
  const parts = [`Person #${String(item.track_id).padStart(2, "0")}`];
  if (item.moving) {
    parts.push("Moving");
  }
  if (item.waving) {
    parts.push("Waving");
  }
  parts.push(confidence);
  return parts.join(" · ");
}

export function toOverlayObservation(item: PublicObservation): OverlayObservation {
  return {
    id: typeof item.track_id === "number" ? `track-${item.track_id}` : item.observation_id,
    label: activityLabel(item),
    confidence: item.confidence,
    box: {
      xMin: item.bounding_box.x_min,
      yMin: item.bounding_box.y_min,
      xMax: item.bounding_box.x_max,
      yMax: item.bounding_box.y_max,
    },
    observedAt: item.observed_at,
  };
}
