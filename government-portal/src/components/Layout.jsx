import React from "react";
import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  {
    to: "/government",
    label: "Dashboard",
  },
  {
    to: "/government/road-issues",
    label: "Road Issues",
  },
  {
    to: "/government/violations",
    label: "Traffic Violations",
  },
  {
    to: "/government/accidents",
    label: "Accidents",
  },
  {
    to: "/government/alerts",
    label: "Alerts",
  },
  {
    to: "/government/fleet",
    label: "Fleet Monitoring",
  },
  {
    to: "/government/analytics",
    label: "Analytics",
  },
];

function Layout() {
  return (
    <div className="app-shell">

      {/* =====================================================
          GOVERNMENT SIDEBAR
      ===================================================== */}

      <aside className="sidebar">

        <div className="sidebar-header">

          <div className="brand-mark">
            UI
          </div>

          <div>
            <h2>UrbanIQ</h2>
            <span>
              Government Command Center
            </span>
          </div>

        </div>


        {/* ===================================================
            GOVERNMENT NAVIGATION
        =================================================== */}

        <nav
          className="sidebar-nav"
          aria-label="Government navigation"
        >

          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/government"}
              className={({ isActive }) =>
                `nav-item ${
                  isActive ? "active" : ""
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}

        </nav>


        {/* ===================================================
            GOVERNMENT SYSTEM STATUS
        =================================================== */}

        <div className="sidebar-footer">

          <div className="network-label">
            AI Fleet Network
          </div>

          <div className="network-status">

            <span className="status-dot" />

            All systems operational

          </div>

        </div>

      </aside>


      {/* =====================================================
          GOVERNMENT CONTENT
      ===================================================== */}

      <main className="main-panel">

        <Outlet />

      </main>

    </div>
  );
}

export default Layout;