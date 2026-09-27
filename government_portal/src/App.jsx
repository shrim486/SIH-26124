import React, { useState } from "react";
import { governmentApi } from "./api/governmentApi";
import { NavLink, Outlet } from "react-router-dom";
import useGovernmentAccess from '../../shared/useGovernmentAccess';
import {
  LayoutDashboard,
  Construction,
  ShieldAlert,
  CarFront,
  Bell,
  Bus,
  BarChart3,
  Film,
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
  { to: '/detections', label: 'Detected Issues Map', icon: CarFront },
  { to: '/ai-results', label: 'Videos & Images', icon: Film },
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

const access = {
  getToken:()=>sessionStorage.getItem('government_token'),
  verify:signal=>governmentApi.checkSession(signal),
  clear:()=>sessionStorage.removeItem('government_token'),
};

function Layout() {
  const {status,check,signOut} = useGovernmentAccess(access);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function login(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true); setError('');
    try {
      await governmentApi.login(data.get('username'), data.get('password'));
      if (!await check()) throw new Error('Government session verification failed');
    } catch (error) { setError(error.message || 'Sign-in failed. Check your credentials and backend connection.'); }
    finally { setBusy(false); }
  }
  if (status==='checking') return <main className="civic-signin civic-ui"><p role="status">Checking government session…</p></main>;
  if (status!=='verified') return (
    <main className="civic-signin civic-ui"><span className="civic-kicker">UrbanIQ · Government portal</span>
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
            <span>Government portal</span>
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
          <button onClick={signOut}>Sign out</button>

          <div className="network-label">
            Fleet operations
          </div>

          <div className="network-status">
            <span className="status-dot" />
            <span>
              Status in Fleet Monitoring
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
