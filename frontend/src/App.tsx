import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/useAuth";
import { useConfiguredAccessToken } from "./auth/useApiAccessToken";
import { SystemStatus } from "./components/SystemStatus";
import { DashboardPlaceholder, ObservationsPage } from "./views/DashboardPlaceholder";
import { IncidentsPlaceholder } from "./views/IncidentsPlaceholder";
import { LiveCameras } from "./views/LiveCameras";
import { LoginView } from "./views/LoginView";
import { NotFound } from "./views/NotFound";
import { SettingsPlaceholder } from "./views/SettingsPlaceholder";

// shortcut: nav uses the account's first role, upgrade when a site role should hide a different page
const SAFETY_ROLES = new Set([
  "SYSTEM_ADMIN",
  "ORG_ADMIN",
  "SITE_MANAGER",
  "SAFETY_OFFICER",
  "OPERATOR",
]);

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/cameras": "Live monitoring",
  "/observations": "Observations",
  "/incidents": "Incidents",
  "/settings": "Settings",
};

export default function App() {
  const { status, user, logout } = useAuth();
  const location = useLocation();
  const [narrow, setNarrow] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (status !== "authenticated") {
      document.title = "ILKA | Sign in";
      return;
    }
    const page = TITLES[location.pathname];
    document.title = page ? `ILKA | ${page}` : "ILKA | Not found";
  }, [location.pathname, status]);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") {
      return;
    }
    const query = window.matchMedia("(max-width: 800px)");
    const apply = () => setNarrow(query.matches);
    apply();
    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  if (status === "loading") {
    return (
      <div className="shell">
        <p className="session-check">Checking session…</p>
      </div>
    );
  }

  if (status !== "authenticated" || !user) {
    return (
      <div className="shell login-shell">
        <LoginView />
      </div>
    );
  }

  const role = user.roles[0] ?? "VIEWER";
  const showDrawer = narrow && menuOpen;

  return (
    <div className="shell">
      <div className="layout">
        {showDrawer ? (
          <button type="button" className="backdrop" aria-label="Close menu" onClick={() => setMenuOpen(false)} />
        ) : null}
        {narrow && !menuOpen ? null : (
          <nav className="nav" id="primary-nav" aria-label="Primary">
            <Link className="brand" to="/">
              ILKA
            </Link>
            <p className="eyebrow">Industrial safety</p>
            <NavLink to="/" end>
              Dashboard
            </NavLink>
            <NavLink to="/cameras">Cameras</NavLink>
            <NavLink to="/observations">Observations</NavLink>
            {SAFETY_ROLES.has(role) ? <NavLink to="/incidents">Incidents</NavLink> : null}
            {role === "SYSTEM_ADMIN" || role === "ORG_ADMIN" ? (
              <NavLink to="/settings">Settings</NavLink>
            ) : null}
            {narrow ? (
              <button type="button" onClick={() => setMenuOpen(false)}>
                Close
              </button>
            ) : null}
          </nav>
        )}
        <div className="workspace">
          <header className="topbar">
            {narrow ? (
              <button
                type="button"
                className="menu-button"
                aria-expanded={menuOpen}
                aria-controls="primary-nav"
                onClick={() => setMenuOpen(true)}
              >
                Menu
              </button>
            ) : null}
            <span className="identity">
              <span>{user.name}</span>
              <span className="badge">{role}</span>
              <button type="button" onClick={() => logout()} disabled={false}>
                Sign out
              </button>
            </span>
            <SystemStatus />
          </header>
          <main className="content">
            <Routes>
              <Route path="/" element={<DashboardPlaceholder />} />
              <Route path="/cameras" element={<CamerasRoute />} />
              <Route path="/observations" element={<ObservationsPage />} />
              <Route
                path="/incidents"
                element={SAFETY_ROLES.has(role) ? <IncidentsPlaceholder /> : <NotFound />}
              />
              <Route
                path="/settings"
                element={
                  role === "SYSTEM_ADMIN" || role === "ORG_ADMIN" ? (
                    <SettingsPlaceholder />
                  ) : (
                    <NotFound />
                  )
                }
              />
              <Route path="/login" element={<Navigate to="/" replace />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
        </div>
      </div>
    </div>
  );
}

function CamerasRoute() {
  const access = useConfiguredAccessToken();
  return (
    <section className="page">
      <header className="page-header">
        <h1>Live monitoring</h1>
        <p className="muted">
          Browser preview of the lab cameras. This is not a production video path. Live AI stays
          disconnected until the backend reports a connection.
        </p>
      </header>
      {access.status === "ready" ? (
        <LiveCameras getAccessToken={access.getAccessToken} workspace />
      ) : (
        <LiveCameras getAccessToken={null} workspace />
      )}
    </section>
  );
}
