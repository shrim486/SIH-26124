import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { userApi } from "../api/userApi";
import IncidentMap from "../components/IncidentMap";


function StatCard({ title, value, icon, accent }) {
  return (
    <div className="user-stat-card">
      <div
        className="user-stat-icon"
        style={{ background: accent }}
      >
        {icon}
      </div>

      <div>
        <div className="user-stat-title">{title}</div>
        <div className="user-stat-value">{value}</div>
      </div>
    </div>
  );
}


function UserDashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [mapEvents, setMapEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mapLoading, setMapLoading] = useState(true);
  const [error, setError] = useState("");
  const [mapError, setMapError] = useState("");

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await userApi.getDashboard();

      setDashboard(data);
    } catch (err) {
      console.error("Dashboard error:", err);
      setError(err.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };


  const loadMapEvents = async () => {
    try {
      setMapLoading(true);
      setMapError("");

      const events = await userApi.getMapEvents();

      setMapEvents(Array.isArray(events) ? events : []);
    } catch (err) {
      console.error("Map error:", err);
      setMapError(err.message || "Failed to load map events");
    } finally {
      setMapLoading(false);
    }
  };


  const loadAll = async () => {
    await Promise.all([
      loadDashboard(),
      loadMapEvents(),
    ]);
  };


  useEffect(() => {
    loadAll();

    const interval = setInterval(() => {
      loadAll();
    }, 30000);

    return () => clearInterval(interval);
  }, []);


  const stats =
    dashboard?.statistics ||
    dashboard?.stats ||
    {
      total_alerts: 0,
      open_issues: 0,
      resolved_issues: 0,
      potholes: 0,
      waterlogging: 0,
      accidents: 0,
    };


  const alerts =
    dashboard?.recent_alerts ||
    dashboard?.alerts ||
    [];


  if (loading && !dashboard) {
    return (
      <div className="user-page">
        <div className="user-loading">
          Loading UrbanIQ dashboard...
        </div>
      </div>
    );
  }


  return (
    <div className="user-page">

      {/* ======================================================
          HERO
      ====================================================== */}

      <section className="user-hero">

        <div>
          <div className="user-eyebrow">
            <span className="live-dot" />
            LIVE URBAN MONITORING
          </div>

          <h1>
            Stay ahead of what's
            <br />
            happening around you.
          </h1>

          <p>
            Real-time road intelligence collected through
            the UrbanIQ network.
          </p>
        </div>

        <button
          className="refresh-button"
          onClick={loadAll}
          disabled={loading}
        >
          ↻ {loading ? "Refreshing..." : "Refresh"}
        </button>

      </section>


      {/* ======================================================
          ERROR
      ====================================================== */}

      {error && (
        <div className="user-error">
          <strong>Dashboard error</strong>
          <span>{error}</span>
        </div>
      )}


      {/* ======================================================
          STATISTICS
      ====================================================== */}

      <section className="user-stats-grid">

        <StatCard
          title="Active Alerts"
          value={stats.total_alerts ?? 0}
          icon="🛡"
          accent="rgba(42, 157, 255, 0.18)"
        />

        <StatCard
          title="Road Issues"
          value={stats.potholes ?? 0}
          icon="🚧"
          accent="rgba(255, 166, 0, 0.18)"
        />

        <StatCard
          title="Accidents"
          value={stats.accidents ?? 0}
          icon="🚑"
          accent="rgba(255, 77, 109, 0.18)"
        />

        <StatCard
          title="Waterlogging"
          value={stats.waterlogging ?? 0}
          icon="💧"
          accent="rgba(0, 210, 230, 0.18)"
        />

      </section>


      {/* ======================================================
          MAIN CONTENT
      ====================================================== */}

      <section className="user-content-grid">

        {/* MAP */}

        <div
          className="user-panel"
          id="live-map"
        >

          <div className="panel-header">

            <div>
              <span className="panel-eyebrow">
                LIVE MAP
              </span>

              <h2>Urban Road Intelligence</h2>

              <p>
                Detected incidents across the monitored network.
              </p>
            </div>

            <Link
              to="/map"
              className="panel-action"
            >
              ⌖ Open full map
            </Link>

          </div>


          {mapError && (
            <div className="map-error">
              {mapError}
            </div>
          )}


          <div className="dashboard-map">
            {mapLoading ? (
              <div className="map-loading">
                Loading live incidents...
              </div>
            ) : (
              <IncidentMap events={mapEvents} />
            )}
          </div>

        </div>


        {/* SAFETY FEED */}

        <div className="user-panel">

          <div className="panel-header">

            <div>
              <span className="panel-eyebrow">
                SAFETY FEED
              </span>

              <h2>Recent Alerts</h2>

              <p>
                Latest incidents detected by UrbanIQ.
              </p>
            </div>

            <span className="feed-count">
              {alerts.length}
            </span>

          </div>


          <div className="alert-list">

            {alerts.length === 0 ? (
              <div className="empty-state">
                <div>✓</div>
                <strong>No active alerts</strong>
                <span>
                  The monitored network currently has no alerts.
                </span>
              </div>
            ) : (

              alerts.slice(0, 6).map((alert) => (

                <div
                  className="alert-row"
                  key={alert.id}
                >

                  <div className="alert-icon">
                    {alert.alert_type === "pothole"
                      ? "🚧"
                      : alert.alert_type === "accident"
                      ? "🚑"
                      : "⚠"}
                  </div>

                  <div className="alert-info">

                    <strong>
                      {alert.message ||
                        alert.alert_type ||
                        "Urban incident"}
                    </strong>

                    <span>
                      {alert.latitude?.toFixed
                        ? `${alert.latitude.toFixed(4)}, ${alert.longitude.toFixed(4)}`
                        : "Location unavailable"}
                    </span>

                  </div>

                  <span
                    className={`severity ${String(
                      alert.severity || "medium"
                    ).toLowerCase()}`}
                  >
                    {alert.severity || "medium"}
                  </span>

                </div>

              ))

            )}

          </div>

        </div>

      </section>


      {/* ======================================================
          QUICK ACTIONS
      ====================================================== */}

      <section className="quick-actions">

        <Link
          to="/map"
          className="quick-action"
        >
          <span>🗺</span>
          <div>
            <strong>Live Map</strong>
            <small>View nearby incidents</small>
          </div>
        </Link>


        <Link
          to="/report"
          className="quick-action"
        >
          <span>＋</span>
          <div>
            <strong>Report an Issue</strong>
            <small>Tell UrbanIQ about a problem</small>
          </div>
        </Link>


        <Link
          to="/reports"
          className="quick-action"
        >
          <span>▣</span>
          <div>
            <strong>My Reports</strong>
            <small>Track submitted reports</small>
          </div>
        </Link>

      </section>

    </div>
  );
}


export default UserDashboard;