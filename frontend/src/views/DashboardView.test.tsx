import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { IncidentsPlaceholder } from "./IncidentsPlaceholder";
import { DashboardView, type DashboardState } from "./DashboardPlaceholder";

const snapshot = {
  record_kind: "person_observation_demo",
  demo_status: "ready" as const,
  source_status: "local_mp4_demo",
  source_id: "people-detection (1).mp4",
  source_kind: "file",
  is_synthetic: true,
  mock_label: "[MOCK / SYNTHETIC]",
  frames_processed: 30,
  model_id: "torchvision-ssdlite320-mobilenet-v3-large",
  model_version: "0.20.1+cpu",
  observations: [
    {
      observation_id: "6f1b5c2a-0d3e-4f7a-9b8c-1d2e3f4a5b6c",
      object_class: "person",
      confidence: 0.82,
      bounding_box: { x_min: 0.1, y_min: 0.2, x_max: 0.4, y_max: 0.7 },
      source_id: "people-detection (1).mp4",
      model_id: "torchvision-ssdlite320-mobilenet-v3-large",
      model_version: "0.20.1+cpu",
      observed_at: "2026-10-18T00:00:00Z",
      media_timestamp: "2026-10-18T00:00:01Z",
      frame_index: 4,
      is_synthetic: true,
      mock_label: "[MOCK / SYNTHETIC]",
    },
  ],
};

function html(state: DashboardState): string {
  return renderToStaticMarkup(<DashboardView state={state} onRefresh={() => undefined} />);
}

describe("demo dashboard", () => {
  it("shows a loading state", () => {
    expect(html({ kind: "loading" })).toContain("Loading demo observations");
  });

  it("shows an empty demo run", () => {
    const markup = html({
      kind: "empty",
      snapshot: { ...snapshot, demo_status: "empty", observations: [], frames_processed: 0 },
    });
    expect(markup).toContain("No demo run yet");
    expect(markup).toContain("[MOCK / SYNTHETIC]");
    expect(markup).not.toContain("0.82");
  });

  it("shows unauthorized without calling detections into the page", () => {
    const markup = html({ kind: "unauthorized" });
    expect(markup).toContain("Sign in is required");
    expect(markup).toContain("[MOCK / SYNTHETIC]");
    expect(markup).not.toContain("0.82");
  });

  it("shows forbidden without inventing detections", () => {
    const markup = html({ kind: "forbidden" });
    expect(markup).toContain("cannot read or run demo person observations");
    expect(markup).toContain("[MOCK / SYNTHETIC]");
    expect(markup).not.toContain("0.82");
  });

  it("shows an error state without inventing detections", () => {
    const markup = html({ kind: "error", message: "The demo observations request failed" });
    expect(markup).toContain("The demo observations request failed");
    expect(markup).not.toContain("0.82");
  });

  it("renders API observations as synthetic person records", () => {
    const markup = html({ kind: "ready", snapshot });
    expect(markup).toContain("ILKA demo mode");
    expect(markup).toContain("[MOCK / SYNTHETIC]");
    expect(markup).toContain("people-detection (1).mp4");
    expect(markup).toContain("Frames processed");
    expect(markup).toContain("0.82");
    expect(markup).toContain("torchvision-ssdlite320-mobilenet-v3-large");
    expect(markup).toContain("2026-10-18T00:00:01Z");
    expect(markup).toContain("not incidents");
  });

  it("keeps incidents separate from person observations", () => {
    const markup = renderToStaticMarkup(<IncidentsPlaceholder />);
    expect(markup).toContain("not implemented");
    expect(markup).toContain("must not appear here as facts");
    expect(markup).not.toContain("[MOCK / SYNTHETIC]");
    expect(markup).not.toContain("0.82");
  });
});