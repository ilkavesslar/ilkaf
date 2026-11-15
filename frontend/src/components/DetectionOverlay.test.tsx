import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { mapNormalizedBox } from "./detectionGeometry";
import { DetectionOverlay } from "./DetectionOverlay";
import { toOverlayObservation } from "./publicObservation";
import { insightMessage, SafetyInsights } from "./SafetyInsights";

describe("detection overlay", () => {
  it("renders nothing when there are no observations", () => {
    expect(renderToStaticMarkup(<DetectionOverlay observations={[]} />)).toBe("");
  });

  it("places a box on a matching 16:9 frame", () => {
    expect(mapNormalizedBox({ xMin: 0.1, yMin: 0.2, xMax: 0.4, yMax: 0.8 }, 1920, 1080)).toEqual({
      left: "10%",
      top: "20%",
      width: "30%",
      height: "60%",
    });
    const html = renderToStaticMarkup(
      <DetectionOverlay
        imageWidth={1920}
        imageHeight={1080}
        observations={[
          {
            id: "fixture",
            label: "Person #01 · 92%",
            confidence: 0.92,
            box: { xMin: 0.1, yMin: 0.2, xMax: 0.4, yMax: 0.8 },
          },
        ]}
      />,
    );
    expect(html).toContain("Person #01 · 92%");
    expect(html).toContain("left:10%");
  });

  it("letterboxes a wider frame inside the 16:9 stage", () => {
    expect(mapNormalizedBox({ xMin: 0, yMin: 0, xMax: 1, yMax: 1 }, 320, 90)).toEqual({
      left: "0%",
      top: "25%",
      width: "100%",
      height: "50%",
    });
  });

  it("keeps a square frame inside the 16:9 stage", () => {
    expect(mapNormalizedBox({ xMin: 0, yMin: 0, xMax: 1, yMax: 1 }, 1000, 1000)).toEqual({
      left: "21.875%",
      top: "0%",
      width: "56.25%",
      height: "100%",
    });
  });

  it("does not draw a box until the image size is known", () => {
    const html = renderToStaticMarkup(
      <DetectionOverlay
        observations={[
          {
            id: "fixture",
            label: "Person",
            confidence: 0.92,
            box: { xMin: 0, yMin: 0, xMax: 1, yMax: 1 },
          },
        ]}
      />,
    );
    expect(html).toBe("");
  });

  it("keeps waving off the moving label when the person is still", () => {
    expect(
      toOverlayObservation({
        observation_id: "obs-2",
        camera_id: "cam-1",
        object_class: "person",
        confidence: 0.91,
        bounding_box: { x_min: 0, y_min: 0, x_max: 1, y_max: 1 },
        observed_at: "2026-11-08T00:00:00+00:00",
        track_id: 2,
        moving: false,
        waving: true,
      }).label,
    ).toBe("Person #02 · Waving · 91%");
  });

  it("maps backend fields into the overlay", () => {
    expect(
      toOverlayObservation({
        observation_id: "obs-1",
        camera_id: "cam-1",
        object_class: "person",
        confidence: 0.5,
        bounding_box: { x_min: 0.1, y_min: 0.2, x_max: 0.4, y_max: 0.8 },
        observed_at: "2026-11-08T00:00:00+00:00",
        track_id: 1,
        moving: true,
        waving: true,
      }),
    ).toEqual({
      id: "track-1",
      label: "Person #01 · Moving · Waving · 50%",
      confidence: 0.5,
      box: { xMin: 0.1, yMin: 0.2, xMax: 0.4, yMax: 0.8 },
      observedAt: "2026-11-08T00:00:00+00:00",
    });
  });
});

describe("safety insights", () => {
  it("does not claim the scene is clear when AI is disconnected", () => {
    expect(insightMessage("not_connected", "", 0)).toBe(
      "Live AI detection is not currently connected.",
    );
    const html = renderToStaticMarkup(
      <SafetyInsights
        status="not_connected"
        detail=""
        cameraName={null}
        observations={[]}
        capabilities={[{ label: "PPE detection", status: "not_implemented", detail: "No PPE model is implemented." }]}
      />,
    );
    expect(html).toContain("Live AI detection is not currently connected.");
    expect(html).not.toContain("No active observations.");
    expect(html).toContain("PPE detection: not_implemented");
  });

  it("says there are no observations only when the pipeline is ready", () => {
    expect(insightMessage("ready", "", 0)).toBe("No active observations.");
  });
});
