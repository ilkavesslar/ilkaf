import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { LiveCameraCard, LiveCameras } from "./LiveCameras";

describe("live camera cards", () => {
  it("shows loading without claiming the camera is connected", () => {
    const html = renderToStaticMarkup(
      <LiveCameraCard
        name="Camera 01"
        host="192.168.1.17"
        sourceId="vigi-c320i-192.168.1.17"
        status="loading"
        lastFrame={null}
      />,
    );
    expect(html).toContain("Loading live preview");
    expect(html).toContain("Status: loading");
    expect(html).not.toContain("Status: live");
  });

  it("shows a disconnected state", () => {
    const html = renderToStaticMarkup(
      <LiveCameraCard
        name="Camera 02"
        host="192.168.1.18"
        sourceId="vigi-c320i-192.168.1.18"
        status="disconnected"
        lastFrame={null}
        message="Camera disconnected."
      />,
    );
    expect(html).toContain("Camera disconnected.");
    expect(html).toContain("vigi-c320i-192.168.1.18");
  });

  it("requires sign-in instead of showing a fake feed", () => {
    const html = renderToStaticMarkup(<LiveCameras getAccessToken={null} />);
    expect(html).toContain("Sign in is required to view this camera.");
    expect(html).toContain("192.168.1.13");
    expect(html).toContain("192.168.1.15");
    expect(html).not.toContain("Status: live");
  });
});
