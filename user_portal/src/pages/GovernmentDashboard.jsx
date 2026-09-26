import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Activity,
  AlertTriangle,
  Car,
  Droplets,
  LayoutDashboard,
  LogOut,
  Map,
  RefreshCw,
  ShieldAlert,
  Radio,
  Menu,
  X,
  Truck,
  Clock3,
  Video,
} from "lucide-react";

import { governmentApi } from "../api/userApi";
import IncidentMap from "../components/IncidentMap";
import VideoAnalysis from "./VideoAnalysis";


function StatCard({ icon: Icon, title, value, type }) {
  return (
    <div className={`gov-stat-card ${type || ""}`}>
      <div className="gov-stat-icon">
        <Icon size={21} />
      </div>

      <div className="gov-stat-content">
        <span>{title}</span>
        <strong>{value ?? 0}</strong>
      </div>
    </div>
  );
}


function AlertRow({ alert }) {
  const type = String(alert?.alert_type || "").toLowerCase();

  let icon = "⚠️";

  if (type === "pothole") {
    icon = "🚧";
  } else if (type === "accident") {
    icon = "🚑";
  } else if (type === "waterlogging") {
    icon = "💧";
  } else if (type === "helmet_violation") {
    icon = "🪖";
  } else if (type === "triple_riding") {
    icon = "🏍️";
  }

  const severity = String(
    alert?.severity || "medium"
  ).toLowerCase();

  const location =
    alert?.latitude != null &&
    alert?.longitude != null
      ? `${Number(alert.latitude).toFixed(4)}, ${Number(
          alert.longitude
        ).toFixed(4)}`
      : "Location unavailable";

  return (
    <div className="gov-alert-row">
      <div className={`gov-alert-icon ${type}`}>
        {icon}
      </div>

      <div className="gov-alert-info">
        <strong>
          {alert?.message ||
            alert?.alert_type ||
            "Urban incident"}
        </strong>

        <span>{location}</span>
      </div>

      <span className={`gov-severity ${severity}`}>
        {severity}
      </span>
    </div>
  );
}


function EmptyState({ icon: Icon, title, message }) {
  return (
    <div className="gov-page-empty">
      <div className="gov-empty-icon">
        <Icon size={28} />
      </div>

      <strong>{title}</strong>
      <span>{message}</span>
    </div>
  );
}


export default function GovernmentDashboard() {
  const navigate = useNavigate();

  /*
   * IMPORTANT:
   * These views are INTERNAL to the government portal.
   *
   * We intentionally do NOT navigate to:
   * /
   * /map
   * /report
   * /reports
   *
   * Those belong to the citizen portal.
   */
  const [activeView, setActiveView] = useState("dashboard");

  const [statistics, setStatistics] = useState({});
  const [events, setEvents] = useState([]);
  const [alerts, setAlerts] = useState([]);

  const [fleet, setFleet] = useState(null);

  const [loading, setLoading] = useState(true);
  const [fleetLoading, setFleetLoading] = useState(false);
  const [error, setError] = useState("");

  const [mobileOpen, setMobileOpen] = useState(false);


  /*
   * LOAD GOVERNMENT DATA
   */
  const loadGovernmentData = async () => {
    try {
      setLoading(true);
      setError("");

      const [
        statsData,
        eventsData,
        alertsData,
      ] = await Promise.all([
        governmentApi.getStatistics(),
        governmentApi.getMapEvents(),
        governmentApi.getAlerts(),
      ]);

      setStatistics(statsData || {});

      setEvents(
        Array.isArray(eventsData)
          ? eventsData
          : []
      );

      setAlerts(
        Array.isArray(alertsData)
          ? alertsData
          : []
      );

    } catch (err) {
      console.error(
        "Government dashboard error:",
        err
      );

      const message =
        err?.message ||
        "Failed to load government dashboard";

      /*
       * SECURITY:
       * If government authentication expires,
       * send ONLY to government login.
       */
      if (
        message.toLowerCase().includes("authentication") ||
        message.toLowerCase().includes("unauthorized") ||
        message.includes("401")
      ) {
        governmentApi.logout();

        navigate(
          "/government-login",
          { replace: true }
        );

        return;
      }

      setError(message);

    } finally {
      setLoading(false);
    }
  };


  /*
   * OPTIONAL FLEET DATA
   *
   * This checks whether your existing governmentApi
   * already contains getFleet().
   *
   * If it doesn't, the dashboard will not crash.
   */
  const loadFleetData = async () => {
    try {
      setFleetLoading(true);

      if (
        typeof governmentApi.getFleet !==
        "function"
      ) {
        setFleet(null);
        return;
      }

      const data =
        await governmentApi.getFleet();

      setFleet(data || null);

    } catch (err) {
      console.error(
        "Government fleet loading error:",
        err
      );

      setFleet(null);

    } finally {
      setFleetLoading(false);
    }
  };


  /*
   * INITIAL LOAD
   */
  useEffect(() => {
    loadGovernmentData();

    const interval = setInterval(
      loadGovernmentData,
      30000
    );

    return () =>
      clearInterval(interval);
  }, []);


  /*
   * LOAD FLEET ONLY WHEN OPENED
   */
  useEffect(() => {
    if (activeView === "fleet") {
      loadFleetData();
    }
  }, [activeView]);


  /*
   * LOGOUT
   */
  const handleLogout = () => {
    governmentApi.logout();

    navigate(
      "/government-login",
      { replace: true }
    );
  };


  /*
   * SIDEBAR NAVIGATION
   *
   * This is the important fix.
   *
   * These buttons change state instead of changing
   * the browser route.
   */
  const handleNavigation = (view) => {
    setActiveView(view);
    setMobileOpen(false);

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };


  const navigationItems = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: LayoutDashboard,
    },
    {
      id: "map",
      label: "Live Intelligence",
      icon: Map,
    },
    {
      id: "alerts",
      label: "Alerts",
      icon: ShieldAlert,
      badge: alerts.length,
    },
    {
      id: "fleet",
      label: "Fleet Monitoring",
      icon: Car,
    },
    {
      id: "video",
      label: "Video Analysis",
      icon: Video,
    },
  ];


  /*
   * PAGE TITLES
   */
  const pageTitle = {
    dashboard: "Urban Intelligence Command Center",
    map: "Live Intelligence",
    alerts: "Safety Alerts",
    fleet: "Fleet Monitoring",
  }[activeView];


  const pageDescription = {
    dashboard:
      "Real-time monitoring of road safety, incidents and urban infrastructure.",

    map:
      "Live incidents detected across the monitored urban network.",

    alerts:
      "Review active safety incidents detected by the UrbanIQ network.",

    fleet:
      "Monitor the public transport fleet connected to the UrbanIQ network.",

    video:
      "Run motorcycle and helmet detection on a raw traffic video.",
  }[activeView];


  /*
   * DASHBOARD VIEW
   */
  const renderDashboard = () => {
    return (
      <>
        <section className="gov-stats">

          <StatCard
            icon={ShieldAlert}
            title="Total Alerts"
            value={statistics?.total_alerts}
            type="alerts"
          />

          <StatCard
            icon={AlertTriangle}
            title="Open Issues"
            value={statistics?.open_issues}
            type="issues"
          />

          <StatCard
            icon={Map}
            title="Potholes"
            value={statistics?.potholes}
            type="potholes"
          />

          <StatCard
            icon={Droplets}
            title="Waterlogging"
            value={statistics?.waterlogging}
            type="water"
          />

          <StatCard
            icon={Car}
            title="Accidents"
            value={statistics?.accidents}
            type="accidents"
          />

        </section>


        <section className="gov-main-grid">

          {/* MAP */}

          <div className="gov-panel gov-map-panel">

            <div className="gov-panel-header">

              <div>
                <span>
                  LIVE INTELLIGENCE MAP
                </span>

                <h2>
                  Urban Incident Network
                </h2>

                <p>
                  Detected incidents across
                  monitored routes.
                </p>
              </div>

              <div className="gov-map-count">
                <span />
                {events.length} incidents
              </div>

            </div>


            <div className="gov-map">

              {events.length === 0 ? (

                <EmptyState
                  icon={Map}
                  title="No incidents detected"
                  message="The monitored network currently has no map events."
                />

              ) : (

                <IncidentMap
                  events={events}
                  fullScreen
                />

              )}

            </div>

          </div>


          {/* ALERT FEED */}

          <div className="gov-panel gov-alert-panel">

            <div className="gov-panel-header">

              <div>
                <span>
                  SAFETY FEED
                </span>

                <h2>
                  Recent Alerts
                </h2>

                <p>
                  Latest detected incidents.
                </p>
              </div>

              <div className="gov-alert-count">
                {alerts.length}
              </div>

            </div>


            <div className="gov-alert-list">

              {alerts.length === 0 ? (

                <EmptyState
                  icon={ShieldAlert}
                  title="No active alerts"
                  message="The monitored network is currently clear."
                />

              ) : (

                alerts
                  .slice(0, 8)
                  .map((alert) => (
                    <AlertRow
                      key={
                        alert.id ||
                        `${alert.alert_type}-${alert.latitude}-${alert.longitude}`
                      }
                      alert={alert}
                    />
                  ))

              )}

            </div>

          </div>

        </section>
      </>
    );
  };


  /*
   * LIVE MAP VIEW
   */
  const renderMap = () => {
    return (
      <section className="gov-single-panel">

        <div className="gov-panel-header">

          <div>
            <span>
              LIVE INTELLIGENCE
            </span>

            <h2>
              Urban Incident Network
            </h2>

            <p>
              Real-time incident locations from
              government monitoring systems.
            </p>
          </div>

          <div className="gov-map-count">
            <span />
            {events.length} incidents
          </div>

        </div>


        <div className="gov-full-map">

          {events.length === 0 ? (

            <EmptyState
              icon={Map}
              title="No incidents detected"
              message="There are currently no incidents available on the government map."
            />

          ) : (

            <IncidentMap
              events={events}
              fullScreen
            />

          )}

        </div>

      </section>
    );
  };


  /*
   * ALERT VIEW
   */
  const renderAlerts = () => {
    return (
      <section className="gov-single-panel">

        <div className="gov-panel-header">

          <div>
            <span>
              SAFETY FEED
            </span>

            <h2>
              Government Alerts
            </h2>

            <p>
              All recent incidents detected by
              the UrbanIQ monitoring network.
            </p>
          </div>

          <div className="gov-alert-count">
            {alerts.length}
          </div>

        </div>


        <div className="gov-alert-list gov-alert-list-large">

          {alerts.length === 0 ? (

            <EmptyState
              icon={ShieldAlert}
              title="No active alerts"
              message="The monitored network is currently clear."
            />

          ) : (

            alerts.map((alert) => (
              <AlertRow
                key={
                  alert.id ||
                  `${alert.alert_type}-${alert.latitude}-${alert.longitude}`
                }
                alert={alert}
              />
            ))

          )}

        </div>

      </section>
    );
  };


  /*
   * FLEET VIEW
   */
  const renderFleet = () => {

    const buses =
      Array.isArray(fleet?.buses)
        ? fleet.buses
        : [];

    const cameras =
      Array.isArray(fleet?.cameras)
        ? fleet.cameras
        : [];

    return (
      <>
        <section className="gov-stats">

          <StatCard
            icon={Car}
            title="Total Buses"
            value={
              fleet?.total_buses ??
              buses.length
            }
            type="fleet"
          />

          <StatCard
            icon={Activity}
            title="Connected Cameras"
            value={
              fleet?.total_cameras ??
              cameras.length
            }
            type="cameras"
          />

          <StatCard
            icon={Radio}
            title="Network Events"
            value={events.length}
            type="events"
          />

          <StatCard
            icon={ShieldAlert}
            title="Active Alerts"
            value={alerts.length}
            type="alerts"
          />

        </section>


        <section className="gov-single-panel">

          <div className="gov-panel-header">

            <div>
              <span>
                FLEET MONITORING
              </span>

              <h2>
                Public Transport Network
              </h2>

              <p>
                Connected buses and monitoring
                infrastructure.
              </p>
            </div>

            <button
              className="gov-small-refresh"
              onClick={loadFleetData}
              disabled={fleetLoading}
            >
              <RefreshCw
                size={15}
                className={
                  fleetLoading
                    ? "gov-spin"
                    : ""
                }
              />

              {fleetLoading
                ? "Loading..."
                : "Refresh fleet"}
            </button>

          </div>


          {fleetLoading ? (

            <div className="gov-page-empty">
              <RefreshCw
                size={28}
                className="gov-spin"
              />

              <strong>
                Loading fleet data
              </strong>

              <span>
                Connecting to the government fleet service.
              </span>
            </div>

          ) : fleet === null ? (

            <EmptyState
              icon={Truck}
              title="Fleet service unavailable"
              message="The government API does not currently expose fleet data."
            />

          ) : buses.length === 0 ? (

            <EmptyState
              icon={Truck}
              title="No fleet records"
              message="No connected public transport vehicles are currently registered."
            />

          ) : (

            <div className="gov-fleet-table-wrap">

              <table className="gov-fleet-table">

                <thead>
                  <tr>
                    <th>Bus</th>
                    <th>Route</th>
                    <th>Status</th>
                    <th>Last Update</th>
                  </tr>
                </thead>

                <tbody>

                  {buses.map((bus, index) => (

                    <tr
                      key={
                        bus.id ||
                        bus.bus_id ||
                        index
                      }
                    >

                      <td>
                        <strong>
                          {bus.bus_number ||
                            bus.registration_number ||
                            bus.bus_id ||
                            `Bus ${index + 1}`}
                        </strong>
                      </td>

                      <td>
                        {bus.route ||
                          bus.route_name ||
                          "Not assigned"}
                      </td>

                      <td>
                        <span className="gov-fleet-status">
                          <span />
                          {bus.status ||
                            "Operational"}
                        </span>
                      </td>

                      <td>
                        <span className="gov-fleet-time">
                          <Clock3 size={13} />
                          {bus.updated_at ||
                            bus.last_seen ||
                            "Live"}
                        </span>
                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          )}

        </section>
      </>
    );
  };


  /*
   * LOADING
   */
  if (loading && !statistics) {
    return (
      <div className="government-portal">

        <div className="gov-loading-screen">

          <div className="gov-loading-spinner">
            <RefreshCw
              size={25}
              className="gov-spin"
            />
          </div>

          <strong>
            Initializing UrbanIQ
          </strong>

          <span>
            Connecting to government intelligence services...
          </span>

        </div>

      </div>
    );
  }


  return (
    <div className="government-portal">


      {/* MOBILE OVERLAY */}

      {mobileOpen && (
        <div
          className="gov-mobile-overlay"
          onClick={() =>
            setMobileOpen(false)
          }
        />
      )}


      {/* SIDEBAR */}

      <aside
        className={`gov-sidebar ${
          mobileOpen ? "open" : ""
        }`}
      >

        <div className="gov-brand">

          <div className="gov-brand-icon">
            <Activity size={22} />
          </div>

          <div>
            <strong>
              UrbanIQ
            </strong>

            <span>
              Authority Console
            </span>
          </div>

          <button
            className="gov-sidebar-close"
            onClick={() =>
              setMobileOpen(false)
            }
          >
            <X size={19} />
          </button>

        </div>


        <div className="gov-sidebar-section">

          <span className="gov-sidebar-label">
            COMMAND CENTER
          </span>


          {navigationItems.map((item) => {

            const Icon = item.icon;

            return (
              <button
                key={item.id}
                type="button"
                className={`gov-nav-item ${
                  activeView === item.id
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  handleNavigation(item.id)
                }
              >

                <Icon size={18} />

                <span>
                  {item.label}
                </span>

                {item.badge > 0 && (
                  <small>
                    {item.badge}
                  </small>
                )}

              </button>
            );
          })}

        </div>


        <div className="gov-sidebar-spacer" />


        <div className="gov-sidebar-status">

          <div className="gov-status-dot" />

          <div>
            <strong>
              Network Operational
            </strong>

            <span>
              UrbanIQ monitoring active
            </span>
          </div>

        </div>


        <button
          type="button"
          className="gov-sidebar-logout"
          onClick={handleLogout}
        >
          <LogOut size={17} />
          <span>
            Logout
          </span>
        </button>

      </aside>


      {/* MAIN */}

      <main className="gov-main">


        {/* TOPBAR */}

        <header className="gov-topbar">

          <button
            type="button"
            className="gov-mobile-menu"
            onClick={() =>
              setMobileOpen(true)
            }
          >
            <Menu size={21} />
          </button>


          <div className="gov-topbar-title">

            <span>
              URBAN INTELLIGENCE
            </span>

            <strong>
              Government Authority
            </strong>

          </div>


          <div className="gov-topbar-right">

            <div className="gov-live-pill">
              <span />
              LIVE SYSTEM
            </div>

            <div className="gov-avatar">
              GA
            </div>

          </div>

        </header>


        {/* CONTENT */}

        <div className="gov-content">


          {/* PAGE HEADER */}

          <section className="gov-page-header">

            <div>

              <div className="gov-eyebrow">
                <Radio size={14} />
                OPERATIONAL OVERVIEW
              </div>

              <h1>
                {pageTitle}
              </h1>

              <p>
                {pageDescription}
              </p>

            </div>


            <div className="gov-header-actions">

              <button
                type="button"
                className="gov-refresh-button"
                onClick={
                  activeView === "fleet"
                    ? loadFleetData
                    : loadGovernmentData
                }
                disabled={
                  loading ||
                  fleetLoading
                }
              >

                <RefreshCw
                  size={16}
                  className={
                    loading ||
                    fleetLoading
                      ? "gov-spin"
                      : ""
                  }
                />

                {loading ||
                fleetLoading
                  ? "Refreshing..."
                  : "Refresh data"}

              </button>

            </div>

          </section>


          {/* ERROR */}

          {error && (
            <div className="gov-error">

              <AlertTriangle size={19} />

              <div>

                <strong>
                  Dashboard error
                </strong>

                <span>
                  {error}
                </span>

              </div>

            </div>
          )}


          {/* ACTIVE VIEW */}

          {activeView === "dashboard" &&
            renderDashboard()}

          {activeView === "map" &&
            renderMap()}

          {activeView === "alerts" &&
            renderAlerts()}

          {activeView === "fleet" &&
            renderFleet()}

          {activeView === "video" && <VideoAnalysis />}


          {/* SYSTEM FOOTER */}

          <section className="gov-system-footer">

            <div className="gov-system-left">

              <span className="gov-system-live-dot" />

              <div>

                <strong>
                  SYSTEM OPERATIONAL
                </strong>

                <span>
                  UrbanIQ government monitoring network is active
                </span>

              </div>

            </div>


            <div className="gov-system-right">

              <span>
                AUTHENTICATED
              </span>

              <strong>
                GOVERNMENT AUTHORITY
              </strong>

            </div>

          </section>

        </div>

      </main>

    </div>
  );
}