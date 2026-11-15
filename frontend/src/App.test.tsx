import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { DashboardView } from "./views/DashboardPlaceholder";
import { NotFound } from "./views/NotFound";

describe("dashboard", () => {
  it("labels the local demo and does not invent detections while loading", () => {
    const html = renderToStaticMarkup(<DashboardView state={{ kind: "loading" }} />);
    expect(html).toContain("ILKA demo mode");
    expect(html).toContain("[MOCK / SYNTHETIC]");
    expect(html).toContain("Loading demo observations");
  });
});

describe("not found", () => {
  it("offers a way back to the dashboard", () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>,
    );
    expect(html).toContain("Page not found");
    expect(html).toContain("Back to dashboard");
  });
});