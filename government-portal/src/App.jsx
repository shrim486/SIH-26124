import React from "react";
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