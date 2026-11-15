import { mapNormalizedBox, type NormalizedBox } from "./detectionGeometry";

export type { NormalizedBox };

export type OverlayObservation = {
  id: string;
  label: string;
  confidence: number;
  box: NormalizedBox;
  observedAt?: string;
};

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
    <ul className="detect-overlay">
      {observations.map((item) => (
        <li key={item.id} style={mapNormalizedBox(item.box, imageWidth, imageHeight)}>
          <span>
            {item.label}
          </span>
        </li>
      ))}
    </ul>
  );
}
