import React, { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  Activity,
  Bell,
  FileWarning,
  Home,
  Map,
  Menu,
  PlusCircle,
  ShieldCheck,
  X,
} from "lucide-react";

export default function UserLayout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const links = [
    {
      path: "/",
      label: "Dashboard",
      icon: Home,
    },
    {
      path: "/map",
      label: "Live Map",
      icon: Map,
    },
    {
      path: "/report",
      label: "Report Issue",
      icon: PlusCircle,
    },
    {
      path: "/reports",
      label: "My Reports",
      icon: FileWarning,
    },
  ];

  return (
    <div className="user-app">
      <aside className={`user-sidebar ${mobileOpen ? "open" : ""}`}>
        
        {/* BRAND */}
        <div className="brand">
          <div className="brand-icon">
            <Activity size={22} />
          </div>

          <div>
            <strong>UrbanIQ</strong>
            <span>Citizen Portal</span>
          </div>

          <button
            className="mobile-close"
            onClick={() => setMobileOpen(false)}
          >
            <X size={20} />
          </button>
        </div>


        {/* NAVIGATION */}
        <nav>
          <p className="nav-label">NAVIGATION</p>

          {links.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === "/"}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
              onClick={() => setMobileOpen(false)}
            >
              <Icon size={19} />
              <span>{label}</span>
            </NavLink>
          ))}


          {/* GOVERNMENT PORTAL */}
          <p
            className="nav-label"
            style={{
              marginTop: "28px",
            }}
          >
            AUTHORITY ACCESS
          </p>

          <NavLink
            to="/government-login"
            className={({ isActive }) =>
              `nav-link government-nav-link ${
                isActive ? "active" : ""
              }`
            }
            onClick={() => setMobileOpen(false)}
          >
            <ShieldCheck size={19} />
            <span>Government Portal</span>
          </NavLink>
        </nav>


        {/* BOTTOM */}
        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot" />

            <div>
              <strong>UrbanIQ Network</strong>
              <small>System operational</small>
            </div>
          </div>
        </div>
      </aside>


      {/* MOBILE OVERLAY */}
      {mobileOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setMobileOpen(false)}
        />
      )}


      {/* MAIN */}
      <main className="user-main">
        <header className="topbar">

          <button
            className="mobile-menu"
            onClick={() => setMobileOpen(true)}
          >
            <Menu size={22} />
          </button>

          <div>
            <span className="topbar-label">
              URBAN INTELLIGENCE
            </span>

            <h1>Citizen Safety Portal</h1>
          </div>

          <div className="topbar-actions">

            <button className="notification-button">
              <Bell size={20} />
              <span />
            </button>

            <div className="user-avatar">
              C
            </div>

          </div>
        </header>


        <section className="page-content">
          {children}
        </section>
      </main>
    </div>
  );
}