import type { CSSProperties } from "react";
import { mapNormalizedBox, type NormalizedBox } from "./detectionGeometry";

export type { NormalizedBox };

export type OverlayKeypoint = {
  x: number;
  y: number;
  visibility: number;
};

export type OverlayObservation = {
  id: string;
  label: string;
  confidence: number;
  box: NormalizedBox;
  observedAt?: string;
  keypoints?: OverlayKeypoint[];
  activityClass?: string | null;
};

/** COCO-17 bone pairs for optional skeleton overlay. */
const SKELETON_EDGES: Array<[number, number]> = [
  [5, 6],
  [5, 7],
  [7, 9],
  [6, 8],
  [8, 10],
  [5, 11],
  [6, 12],
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
  [0, 1],
  [0, 2],
  [1, 3],
  [2, 4],
];

function jointStyle(
  joint: OverlayKeypoint,
  imageWidth: number,
  imageHeight: number,
): CSSProperties {
  const mapped = mapNormalizedBox(
    { xMin: joint.x, yMin: joint.y, xMax: joint.x, yMax: joint.y },
    imageWidth,
    imageHeight,
  );
  return { left: mapped.left, top: mapped.top };
}

export function DetectionOverlay({
  observations,
  imageWidth,
  imageHeight,
}: {
  observations: OverlayObservation[];
  imageWidth?: number | null;
  imageHeight?: number | null;
}) {
  if (observations.length === 0 || !imageWidth || !imageHeight) {
    return null;
  }
  return (
    <div className="detect-overlay">
      <ul className="detect-boxes">
        {observations.map((item) => (
          <li key={item.id} style={mapNormalizedBox(item.box, imageWidth, imageHeight)}>
            <span>{item.label}</span>
          </li>
        ))}
      </ul>
      <svg className="detect-skeleton" viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden>
        {observations.flatMap((item) =>
          SKELETON_EDGES.map(([a, b]) => {
            const left = item.keypoints?.[a];
            const right = item.keypoints?.[b];
            if (!left || !right || left.visibility <= 0 || right.visibility <= 0) {
              return null;
            }
            return (
              <line
                key={`${item.id}-${a}-${b}`}
                x1={left.x}
                y1={left.y}
                x2={right.x}
                y2={right.y}
                className="detect-bone"
              />
            );
          }),
        )}
      </svg>
      {observations.flatMap((item) =>
        (item.keypoints ?? []).map((joint, index) =>
          joint.visibility > 0 ? (
            <i
              key={`${item.id}-kp-${index}`}
              className="detect-joint"
              style={jointStyle(joint, imageWidth, imageHeight)}
            />
          ) : null,
        ),
      )}
    </div>
  );
}
