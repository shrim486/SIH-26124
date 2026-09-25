import React, { useState, useEffect } from "react";
import { governmentApi } from "./api/governmentApi";
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Construction,
  ShieldAlert,
  CarFront,
  Bell,
  Bus,
  BarChart3,
} from "lucide-react";

const navItems = [
  {
    to: "/",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  {
    to: "/road-issues",
    label: "Road Issues",
    icon: Construction,
  },
  {
    to: "/violations",
    label: "Traffic Violations",
    icon: ShieldAlert,
  },
  {
    to: "/accidents",
    label: "Accidents",
    icon: CarFront,
  },
  {
    to: "/alerts",
    label: "Alerts",
    icon: Bell,
  },
  {
    to: "/fleet",
    label: "Fleet Monitoring",
    icon: Bus,
  },
  {
    to: "/analytics",
    label: "Analytics",
    icon: BarChart3,
  },
];

function Layout() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(sessionStorage.getItem('government_token')));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const expired = () => setAuthenticated(false);
    window.addEventListener('government-unauthorized', expired);
    return () => window.removeEventListener('government-unauthorized', expired);
  }, []);
  async function login(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true); setError('');
    try {
      await governmentApi.login(data.get('username'), data.get('password'));
      setAuthenticated(true);
    } catch { setError('Sign-in failed. Check your credentials and backend connection.'); }
    finally { setBusy(false); }
  }
  if (!authenticated) return (
    <main style={{ maxWidth: 420, margin: '12vh auto', padding: 28 }}>
      <h1>Government sign in</h1>
      <form onSubmit={login} style={{ display: 'grid', gap: 16 }}>
        <label>Username <input name="username" autoComplete="username" required /></label>
        <label>Password <input name="password" type="password" autoComplete="current-password" required /></label>
        {error && <p role="alert">{error}</p>}
        <button disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
    </main>
  );
  return (
    <div className="app-shell">

      {/* SIDEBAR */}
      <aside className="sidebar">

        {/* BRAND */}
        <div className="sidebar-header">
          <div className="brand-mark">
            UI
          </div>

          <div className="brand-text">
            <h2>UrbanIQ</h2>
            <span>Government Command Center</span>
          </div>
        </div>


        {/* NAVIGATION */}
        <nav
          className="sidebar-nav"
          aria-label="Government navigation"
        >
          {navItems.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `nav-item ${isActive ? "active" : ""}`
                }
              >
                <Icon
                  size={19}
                  strokeWidth={2}
                />

                <span>
                  {item.label}
                </span>
              </NavLink>
            );
          })}
        </nav>


        {/* FOOTER */}
        <div className="sidebar-footer">
          <button onClick={() => { sessionStorage.removeItem('government_token'); setAuthenticated(false); }}>Sign out</button>

          <div className="network-label">
            AI Fleet Network
          </div>

          <div className="network-status">
            <span className="status-dot" />
            <span>
              All systems operational
            </span>
          </div>

        </div>

      </aside>


      {/* MAIN CONTENT */}
      <main className="main-panel">
        <Outlet />
      </main>

    </div>
  );
}

export default Layout;
