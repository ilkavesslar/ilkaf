import type { OverlayObservation, OverlayKeypoint } from "./DetectionOverlay";

export type PublicKeypoint = {
  x?: number | null;
  y?: number | null;
  confidence?: number;
  visibility?: number;
};

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
  local_track_id?: string | null;
  global_person_id?: string | null;
  moving?: boolean;
  waving?: boolean;
  activity_class?: string | null;
  activity_confidence?: number | null;
  movement_state?: string | null;
  tracking_status?: string | null;
  keypoints?: PublicKeypoint[];
  schema_version?: string | null;
};

function formatActivity(activity: string | null | undefined): string | null {
  if (!activity || activity === "unknown") {
    return null;
  }
  return activity.replaceAll("_", " ");
}

export function activityLabel(item: PublicObservation): string {
  const confidence = `${Math.round(item.confidence * 100)}%`;
  const trackLabel =
    typeof item.track_id === "number" && item.track_id >= 1
      ? `Person #${String(item.track_id).padStart(2, "0")}`
      : item.local_track_id
        ? item.local_track_id
        : item.object_class;
  const parts = [trackLabel];
  const activity = formatActivity(item.activity_class);
  if (activity) {
    parts.push(activity);
  } else {
    if (item.moving) {
      parts.push("Moving");
    }
    if (item.waving) {
      parts.push("Waving");
    }
  }
  if (item.global_person_id) {
    parts.push(`anon ${item.global_person_id.slice(0, 8)}`);
  }
  parts.push(confidence);
  return parts.join(" · ");
}

export function toOverlayObservation(item: PublicObservation): OverlayObservation {
  const keypoints: OverlayKeypoint[] = (item.keypoints ?? [])
    .filter((joint) => typeof joint.x === "number" && typeof joint.y === "number" && (joint.visibility ?? 0) > 0)
    .map((joint) => ({
      x: joint.x as number,
      y: joint.y as number,
      visibility: joint.visibility ?? 0,
    }));
  return {
    id:
      typeof item.track_id === "number"
        ? `track-${item.track_id}`
        : item.local_track_id || item.observation_id,
    label: activityLabel(item),
    confidence: item.confidence,
    box: {
      xMin: item.bounding_box.x_min,
      yMin: item.bounding_box.y_min,
      xMax: item.bounding_box.x_max,
      yMax: item.bounding_box.y_max,
    },
    observedAt: item.observed_at,
    keypoints,
    activityClass: item.activity_class ?? null,
  };
}
