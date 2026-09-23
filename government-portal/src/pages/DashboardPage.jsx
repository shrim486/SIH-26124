import { useEffect, useState } from "react";
import { governmentApi } from "../api/governmentApi";

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [statistics, setStatistics] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError("");

      const [dashboardData, statisticsData] = await Promise.all([
        governmentApi.getDashboard(),
        governmentApi.getStatistics(),
      ]);

      setDashboard(dashboardData);
      setStatistics(statisticsData);
    } catch (err) {
      console.error("Dashboard loading error:", err);
      setError(err.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  if (loading) {
    return (
      <div style={styles.loadingScreen}>
        <div style={styles.loadingSpinner}></div>
        <div>
          <div style={styles.loadingTitle}>Loading UrbanIQ</div>
          <div style={styles.loadingText}>
            Connecting to the urban intelligence network...
          </div>
        </div>
      </div>
    );
  }

  const stats =
    statistics ||
    dashboard?.statistics ||
    dashboard?.stats ||
    {};

  const events =
    dashboard?.recent_events ||
    dashboard?.events ||
    [];

  const roadIssues =
    dashboard?.recent_road_issues ||
    dashboard?.road_issues ||
    [];

  const alerts =
    dashboard?.recent_alerts ||
    dashboard?.alerts ||
    [];

  const violations =
    dashboard?.recent_violations ||
    dashboard?.violations ||
    [];

  const fleet = dashboard?.fleet || {
    total_buses: 0,
    total_cameras: 0,
    buses: [],
    cameras: [],
  };

  return (
    <div style={styles.page}>

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div style={styles.header}>
        <div>
          <div style={styles.eyebrow}>URBANIQ / GOVERNMENT COMMAND</div>

          <h1 style={styles.title}>
            Urban Intelligence Dashboard
          </h1>

          <p style={styles.subtitle}>
            Real-time monitoring of road conditions, incidents,
            violations and public transport intelligence.
          </p>
        </div>

        <button
          style={styles.refreshButton}
          onClick={loadDashboard}
        >
          ↻ Refresh
        </button>
      </div>


      {/* =====================================================
          ERROR
      ===================================================== */}

      {error && (
        <div style={styles.errorBox}>
          <div style={styles.errorTitle}>
            Dashboard API Error
          </div>

          <div style={styles.errorText}>
            {error}
          </div>
        </div>
      )}


      {/* =====================================================
          SYSTEM STATUS
      ===================================================== */}

      <div style={styles.statusBar}>
        <div style={styles.statusLeft}>
          <span style={styles.statusDot}></span>

          <div>
            <div style={styles.statusTitle}>
              AI Fleet Network
            </div>

            <div style={styles.statusText}>
              All connected intelligence systems operational
            </div>
          </div>
        </div>

        <div style={styles.statusRight}>
          <span>API</span>
          <strong>ONLINE</strong>
        </div>
      </div>


      {/* =====================================================
          MAIN KPI CARDS
      ===================================================== */}

      <div style={styles.kpiGrid}>

        <KpiCard
          icon="⚡"
          label="Total Alerts"
          value={stats.total_alerts ?? 0}
          description="All detected incidents"
        />

        <KpiCard
          icon="🚨"
          label="Open Issues"
          value={stats.open_issues ?? 0}
          description="Requiring attention"
        />

        <KpiCard
          icon="✓"
          label="Resolved"
          value={stats.resolved_issues ?? 0}
          description="Completed issues"
        />

      </div>


      {/* =====================================================
          DETECTION BREAKDOWN
      ===================================================== */}

      <div style={styles.sectionHeader}>
        <div>
          <div style={styles.sectionEyebrow}>
            AI DETECTION
          </div>

          <h2 style={styles.sectionTitle}>
            Urban Event Breakdown
          </h2>
        </div>

        <div style={styles.liveBadge}>
          <span style={styles.liveDot}></span>
          LIVE DATA
        </div>
      </div>


      <div style={styles.detectionGrid}>

        <DetectionCard
          icon="🛣️"
          label="Potholes"
          value={stats.potholes ?? 0}
          severity="Road infrastructure"
        />

        <DetectionCard
          icon="🌊"
          label="Waterlogging"
          value={stats.waterlogging ?? 0}
          severity="Road hazard"
        />

        <DetectionCard
          icon="🚑"
          label="Accidents"
          value={stats.accidents ?? 0}
          severity="Critical incident"
        />

        <DetectionCard
          icon="🪖"
          label="Helmet Violations"
          value={stats.helmet_violations ?? 0}
          severity="Traffic violation"
        />

        <DetectionCard
          icon="🏍️"
          label="Triple Riding"
          value={stats.triple_riding ?? 0}
          severity="Traffic violation"
        />

        <DetectionCard
          icon="🚦"
          label="Traffic Bottlenecks"
          value={stats.traffic_bottlenecks ?? 0}
          severity="Traffic intelligence"
        />

      </div>


      {/* =====================================================
          TWO COLUMN AREA
      ===================================================== */}

      <div style={styles.twoColumn}>


        {/* =================================================
            RECENT ALERTS
        ================================================= */}

        <section style={styles.panel}>

          <div style={styles.panelHeader}>
            <div>
              <div style={styles.panelEyebrow}>
                PRIORITY FEED
              </div>

              <h2 style={styles.panelTitle}>
                Recent Alerts
              </h2>
            </div>

            <div style={styles.countBadge}>
              {alerts.length}
            </div>
          </div>


          {alerts.length === 0 ? (
            <EmptyState message="No active alerts detected." />
          ) : (
            <div style={styles.alertList}>
              {alerts.slice(0, 6).map((alert) => (
                <div
                  key={alert.id}
                  style={styles.alertItem}
                >

                  <div style={styles.alertIcon}>
                    {getEventIcon(alert.alert_type)}
                  </div>

                  <div style={styles.alertContent}>

                    <div style={styles.alertTopRow}>

                      <strong style={styles.alertType}>
                        {formatLabel(alert.alert_type)}
                      </strong>

                      <SeverityBadge
                        severity={alert.severity}
                      />

                    </div>

                    <div style={styles.alertMessage}>
                      {alert.message || "Urban event detected"}
                    </div>

                    <div style={styles.alertMeta}>

                      <span>
                        📍{" "}
                        {formatCoordinate(alert.latitude)}
                        {" , "}
                        {formatCoordinate(alert.longitude)}
                      </span>

                      <span>
                        {formatDate(alert.created_at)}
                      </span>

                    </div>

                  </div>

                </div>
              ))}
            </div>
          )}

        </section>


        {/* =================================================
            ROAD ISSUES
        ================================================= */}

        <section style={styles.panel}>

          <div style={styles.panelHeader}>

            <div>
              <div style={styles.panelEyebrow}>
                INFRASTRUCTURE
              </div>

              <h2 style={styles.panelTitle}>
                Road Issues
              </h2>
            </div>

            <div style={styles.countBadge}>
              {roadIssues.length}
            </div>

          </div>


          {roadIssues.length === 0 ? (
            <EmptyState message="No road issues detected." />
          ) : (
            <div style={styles.issueList}>

              {roadIssues.slice(0, 5).map((issue) => (

                <div
                  key={issue.id}
                  style={styles.issueItem}
                >

                  <div style={styles.issueMain}>

                    <div style={styles.issueTitleRow}>

                      <strong>
                        {formatLabel(issue.issue_type)}
                      </strong>

                      <SeverityBadge
                        severity={issue.severity}
                      />

                    </div>

                    <div style={styles.issueLocation}>
                      📍 {formatCoordinate(issue.latitude)},{" "}
                      {formatCoordinate(issue.longitude)}
                    </div>

                  </div>

                  <div style={styles.issueStatus}>
                    {formatLabel(issue.status)}
                  </div>

                </div>

              ))}

            </div>
          )}

        </section>

      </div>


      {/* =====================================================
          RECENT DETECTIONS
      ===================================================== */}

      <section style={styles.panel}>

        <div style={styles.panelHeader}>

          <div>
            <div style={styles.panelEyebrow}>
              EDGE AI STREAM
            </div>

            <h2 style={styles.panelTitle}>
              Recent AI Detections
            </h2>
          </div>

          <div style={styles.liveBadge}>
            <span style={styles.liveDot}></span>
            LIVE
          </div>

        </div>


        {events.length === 0 ? (
          <EmptyState message="No AI detections available." />
        ) : (

          <div style={styles.eventTable}>

            <div style={styles.tableHeader}>
              <span>EVENT</span>
              <span>CONFIDENCE</span>
              <span>LOCATION</span>
              <span>BUS</span>
              <span>SEVERITY</span>
              <span>TIME</span>
            </div>


            {events.slice(0, 8).map((event) => (

              <div
                key={event.id}
                style={styles.tableRow}
              >

                <div style={styles.eventName}>
                  <span style={styles.eventIcon}>
                    {getEventIcon(event.event_type)}
                  </span>

                  <strong>
                    {formatLabel(event.event_type)}
                  </strong>
                </div>


                <div style={styles.confidence}>
                  <div style={styles.confidenceBar}>

                    <div
                      style={{
                        ...styles.confidenceFill,
                        width: `${Math.min(
                          100,
                          (event.confidence || 0) * 100
                        )}%`,
                      }}
                    />

                  </div>

                  <span>
                    {Math.round(
                      (event.confidence || 0) * 100
                    )}
                    %
                  </span>
                </div>


                <div style={styles.locationCell}>
                  <span>
                    {formatCoordinate(event.latitude)}
                  </span>

                  <span>
                    {formatCoordinate(event.longitude)}
                  </span>
                </div>


                <div style={styles.busCell}>
                  {event.bus_id
                    ? `BUS-${event.bus_id}`
                    : "N/A"}
                </div>


                <SeverityBadge
                  severity={event.severity}
                />


                <div style={styles.timeCell}>
                  {formatDate(event.timestamp)}
                </div>

              </div>

            ))}

          </div>

        )}

      </section>


      {/* =====================================================
          BOTTOM INTELLIGENCE AREA
      ===================================================== */}

      <div style={styles.bottomGrid}>


        {/* TRAFFIC */}
        <section style={styles.smallPanel}>

          <div style={styles.smallPanelIcon}>
            🚦
          </div>

          <div>
            <div style={styles.smallPanelLabel}>
              TRAFFIC INTELLIGENCE
            </div>

            <div style={styles.smallPanelValue}>
              {stats.traffic_bottlenecks ?? 0}
            </div>

            <div style={styles.smallPanelText}>
              Active bottlenecks
            </div>
          </div>

        </section>


        {/* VIOLATIONS */}
        <section style={styles.smallPanel}>

          <div style={styles.smallPanelIcon}>
            ⚠️
          </div>

          <div>
            <div style={styles.smallPanelLabel}>
              VIOLATIONS
            </div>

            <div style={styles.smallPanelValue}>
              {(stats.helmet_violations ?? 0) +
                (stats.triple_riding ?? 0)}
            </div>

            <div style={styles.smallPanelText}>
              Detected violations
            </div>
          </div>

        </section>


        {/* FLEET */}
        <section style={styles.smallPanel}>

          <div style={styles.smallPanelIcon}>
            🚌
          </div>

          <div>
            <div style={styles.smallPanelLabel}>
              AI FLEET
            </div>

            <div style={styles.smallPanelValue}>
              {fleet.total_buses ?? 0}
            </div>

            <div style={styles.smallPanelText}>
              Connected buses
            </div>
          </div>

        </section>


        {/* CAMERAS */}
        <section style={styles.smallPanel}>

          <div style={styles.smallPanelIcon}>
            📹
          </div>

          <div>
            <div style={styles.smallPanelLabel}>
              CAMERAS
            </div>

            <div style={styles.smallPanelValue}>
              {fleet.total_cameras ?? 0}
            </div>

            <div style={styles.smallPanelText}>
              Edge cameras
            </div>
          </div>

        </section>

      </div>


      {/* =====================================================
          FOOTER
      ===================================================== */}

      <div style={styles.footer}>

        <div>
          URBANIQ GOVERNMENT INTELLIGENCE PLATFORM
        </div>

        <div>
          GPS coordinates are attached to every detected event
        </div>

      </div>

    </div>
  );
}


/* ============================================================
   KPI CARD
============================================================ */

function KpiCard({
  icon,
  label,
  value,
  description,
}) {
  return (
    <div style={styles.kpiCard}>

      <div style={styles.kpiIcon}>
        {icon}
      </div>

      <div>
        <div style={styles.kpiLabel}>
          {label}
        </div>

        <div style={styles.kpiValue}>
          {value}
        </div>

        <div style={styles.kpiDescription}>
          {description}
        </div>
      </div>

    </div>
  );
}


/* ============================================================
   DETECTION CARD
============================================================ */

function DetectionCard({
  icon,
  label,
  value,
  severity,
}) {
  return (
    <div style={styles.detectionCard}>

      <div style={styles.detectionIcon}>
        {icon}
      </div>

      <div style={styles.detectionContent}>

        <div style={styles.detectionLabel}>
          {label}
        </div>

        <div style={styles.detectionValue}>
          {value}
        </div>

        <div style={styles.detectionSeverity}>
          {severity}
        </div>

      </div>

    </div>
  );
}


/* ============================================================
   SEVERITY BADGE
============================================================ */

function SeverityBadge({ severity }) {
  const value = String(
    severity || "normal"
  ).toLowerCase();

  const severityStyles = {
    critical: {
      background: "rgba(255, 59, 92, 0.14)",
      border: "1px solid rgba(255, 59, 92, 0.35)",
      color: "#ff6b86",
    },

    high: {
      background: "rgba(255, 130, 60, 0.14)",
      border: "1px solid rgba(255, 130, 60, 0.35)",
      color: "#ff9a62",
    },

    medium: {
      background: "rgba(255, 196, 79, 0.14)",
      border: "1px solid rgba(255, 196, 79, 0.35)",
      color: "#ffc94f",
    },

    low: {
      background: "rgba(51, 213, 145, 0.12)",
      border: "1px solid rgba(51, 213, 145, 0.3)",
      color: "#55dda5",
    },

    normal: {
      background: "rgba(115, 170, 220, 0.12)",
      border: "1px solid rgba(115, 170, 220, 0.25)",
      color: "#8bbce8",
    },
  };

  return (
    <span
      style={{
        ...styles.severityBadge,
        ...(severityStyles[value] ||
          severityStyles.normal),
      }}
    >
      {value.toUpperCase()}
    </span>
  );
}


/* ============================================================
   EMPTY STATE
============================================================ */

function EmptyState({ message }) {
  return (
    <div style={styles.emptyState}>
      <div style={styles.emptyIcon}>
        ✓
      </div>

      <div>
        <div style={styles.emptyTitle}>
          Nothing to report
        </div>

        <div style={styles.emptyText}>
          {message}
        </div>
      </div>
    </div>
  );
}


/* ============================================================
   HELPERS
============================================================ */

function formatLabel(value) {
  if (!value) return "Unknown";

  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );
}


function formatCoordinate(value) {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return Number(value).toFixed(5);
}


function formatDate(value) {
  if (!value) return "Unknown";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}


function getEventIcon(type) {
  const value = String(type || "").toLowerCase();

  if (value.includes("pothole")) return "🛣️";
  if (value.includes("water")) return "🌊";
  if (value.includes("accident")) return "🚑";
  if (value.includes("helmet")) return "🪖";
  if (value.includes("triple")) return "🏍️";
  if (value.includes("traffic")) return "🚦";

  return "⚡";
}


/* ============================================================
   STYLES
============================================================ */

const styles = {

  page: {
    minHeight: "100%",
    padding: "34px",
    background:
      "radial-gradient(circle at 80% 0%, rgba(28,117,185,0.12), transparent 32%), #07101b",
    color: "#f5f9ff",
    fontFamily:
      "Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },


  loadingScreen: {
    minHeight: "70vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "18px",
    color: "#dcecff",
  },


  loadingSpinner: {
    width: "28px",
    height: "28px",
    borderRadius: "50%",
    border: "3px solid rgba(60,180,255,0.2)",
    borderTopColor: "#38bdf8",
  },


  loadingTitle: {
    fontSize: "18px",
    fontWeight: 700,
  },


  loadingText: {
    marginTop: "4px",
    color: "#7294b8",
    fontSize: "13px",
  },


  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: "24px",
    marginBottom: "28px",
  },


  eyebrow: {
    color: "#28b9ff",
    fontSize: "12px",
    fontWeight: 800,
    letterSpacing: "2px",
    marginBottom: "8px",
  },


  title: {
    margin: 0,
    fontSize: "42px",
    lineHeight: 1.08,
    letterSpacing: "-1.5px",
  },


  subtitle: {
    margin: "10px 0 0",
    color: "#83a8cf",
    fontSize: "15px",
  },


  refreshButton: {
    border: "1px solid #254d70",
    background: "#0d2033",
    color: "#eaf6ff",
    borderRadius: "10px",
    padding: "13px 20px",
    fontSize: "14px",
    fontWeight: 700,
    cursor: "pointer",
    whiteSpace: "nowrap",
  },


  errorBox: {
    marginBottom: "20px",
    padding: "18px 20px",
    borderRadius: "12px",
    background: "rgba(255, 52, 91, 0.1)",
    border: "1px solid rgba(255, 70, 105, 0.5)",
  },


  errorTitle: {
    color: "#ff7893",
    fontSize: "14px",
    fontWeight: 800,
    marginBottom: "5px",
  },


  errorText: {
    color: "#dba9b4",
    fontSize: "13px",
  },


  statusBar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "16px 20px",
    marginBottom: "22px",
    borderRadius: "12px",
    border: "1px solid #183a59",
    background:
      "linear-gradient(90deg, rgba(14,39,61,0.9), rgba(8,24,39,0.8))",
  },


  statusLeft: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },


  statusDot: {
    width: "9px",
    height: "9px",
    borderRadius: "50%",
    background: "#35e69a",
    boxShadow: "0 0 14px rgba(53,230,154,0.7)",
  },


  statusTitle: {
    fontSize: "13px",
    fontWeight: 800,
    color: "#c4dcf4",
  },


  statusText: {
    marginTop: "3px",
    fontSize: "12px",
    color: "#7294b8",
  },


  statusRight: {
    display: "flex",
    gap: "8px",
    fontSize: "11px",
    color: "#6689ad",
  },


  kpiGrid: {
    display: "grid",
    gridTemplateColumns:
      "repeat(3, minmax(0, 1fr))",
    gap: "18px",
    marginBottom: "34px",
  },


  kpiCard: {
    display: "flex",
    alignItems: "center",
    gap: "18px",
    minHeight: "135px",
    padding: "24px",
    borderRadius: "16px",
    border: "1px solid #1d4567",
    background:
      "linear-gradient(145deg, #0d2236, #091725)",
    boxShadow:
      "0 12px 30px rgba(0,0,0,0.18)",
  },


  kpiIcon: {
    width: "52px",
    height: "52px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: "14px",
    background: "#12344e",
    fontSize: "24px",
  },


  kpiLabel: {
    color: "#8eb4d8",
    fontSize: "14px",
    fontWeight: 600,
  },


  kpiValue: {
    marginTop: "3px",
    fontSize: "38px",
    fontWeight: 800,
    letterSpacing: "-1px",
  },


  kpiDescription: {
    marginTop: "3px",
    color: "#587d9f",
    fontSize: "12px",
  },


  sectionHeader: {
    display: "flex",
    alignItems: "flex-end",
    justifyContent: "space-between",
    marginBottom: "15px",
  },


  sectionEyebrow: {
    fontSize: "10px",
    letterSpacing: "1.7px",
    color: "#2ebdff",
    fontWeight: 800,
  },


  sectionTitle: {
    margin: "4px 0 0",
    fontSize: "22px",
  },


  liveBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "7px",
    padding: "6px 9px",
    borderRadius: "20px",
    border: "1px solid rgba(52,226,157,0.25)",
    background: "rgba(52,226,157,0.07)",
    color: "#54dda5",
    fontSize: "10px",
    fontWeight: 800,
    letterSpacing: "1px",
  },


  liveDot: {
    width: "6px",
    height: "6px",
    borderRadius: "50%",
    background: "#4ce3a5",
  },


  detectionGrid: {
    display: "grid",
    gridTemplateColumns:
      "repeat(3, minmax(0, 1fr))",
    gap: "14px",
    marginBottom: "34px",
  },


  detectionCard: {
    display: "flex",
    gap: "14px",
    alignItems: "center",
    padding: "18px",
    borderRadius: "14px",
    border: "1px solid #183b5a",
    background: "#0b1b2b",
  },


  detectionIcon: {
    width: "45px",
    height: "45px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: "12px",
    background: "#12324b",
    fontSize: "20px",
  },


  detectionLabel: {
    color: "#88add0",
    fontSize: "13px",
  },


  detectionValue: {
    marginTop: "1px",
    fontSize: "27px",
    fontWeight: 800,
  },


  detectionSeverity: {
    color: "#557d9f",
    fontSize: "10px",
    marginTop: "1px",
  },


  twoColumn: {
    display: "grid",
    gridTemplateColumns:
      "repeat(2, minmax(0, 1fr))",
    gap: "18px",
    marginBottom: "20px",
  },


  panel: {
    borderRadius: "16px",
    border: "1px solid #1a3d5c",
    background: "#091827",
    overflow: "hidden",
    marginBottom: "20px",
  },


  panelHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "20px 22px",
    borderBottom: "1px solid #15324b",
  },


  panelEyebrow: {
    fontSize: "9px",
    letterSpacing: "1.5px",
    color: "#4aa8dc",
    fontWeight: 800,
  },


  panelTitle: {
    margin: "4px 0 0",
    fontSize: "18px",
  },


  countBadge: {
    minWidth: "28px",
    height: "28px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: "8px",
    background: "#11334e",
    color: "#72c8f5",
    fontSize: "12px",
    fontWeight: 800,
  },


  alertList: {
    display: "flex",
    flexDirection: "column",
  },


  alertItem: {
    display: "flex",
    gap: "13px",
    padding: "16px 20px",
    borderBottom: "1px solid #102a41",
  },


  alertIcon: {
    width: "38px",
    height: "38px",
    flexShrink: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: "10px",
    background: "#102e47",
  },


  alertContent: {
    minWidth: 0,
    flex: 1,
  },


  alertTopRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "10px",
  },


  alertType: {
    fontSize: "13px",
  },


  alertMessage: {
    marginTop: "5px",
    color: "#91abc4",
    fontSize: "12px",
  },


  alertMeta: {
    display: "flex",
    flexWrap: "wrap",
    gap: "10px",
    marginTop: "8px",
    color: "#557997",
    fontSize: "10px",
  },


  severityBadge: {
    display: "inline-flex",
    padding: "4px 7px",
    borderRadius: "5px",
    fontSize: "8px",
    fontWeight: 800,
    letterSpacing: ".5px",
    whiteSpace: "nowrap",
  },


  issueList: {
    display: "flex",
    flexDirection: "column",
  },


  issueItem: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "15px",
    padding: "17px 20px",
    borderBottom: "1px solid #102a41",
  },


  issueMain: {
    minWidth: 0,
  },


  issueTitleRow: {
    display: "flex",
    alignItems: "center",
    gap: "9px",
    fontSize: "13px",
  },


  issueLocation: {
    marginTop: "7px",
    color: "#597d9c",
    fontSize: "10px",
  },


  issueStatus: {
    padding: "5px 8px",
    borderRadius: "6px",
    background: "rgba(255,190,70,0.08)",
    color: "#e8b858",
    fontSize: "9px",
    fontWeight: 800,
    textTransform: "uppercase",
  },


  eventTable: {
    width: "100%",
  },


  tableHeader: {
    display: "grid",
    gridTemplateColumns:
      "1.3fr 1.2fr 1.3fr .8fr .8fr 1fr",
    gap: "15px",
    padding: "12px 20px",
    color: "#527795",
    fontSize: "9px",
    fontWeight: 800,
    letterSpacing: "1px",
    background: "#07131f",
  },


  tableRow: {
    display: "grid",
    gridTemplateColumns:
      "1.3fr 1.2fr 1.3fr .8fr .8fr 1fr",
    gap: "15px",
    alignItems: "center",
    padding: "15px 20px",
    borderTop: "1px solid #10283d",
    fontSize: "11px",
  },


  eventName: {
    display: "flex",
    alignItems: "center",
    gap: "9px",
  },


  eventIcon: {
    width: "28px",
    height: "28px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: "7px",
    background: "#102e46",
  },


  confidence: {
    display: "flex",
    alignItems: "center",
    gap: "7px",
    color: "#91b5d3",
  },


  confidenceBar: {
    width: "45px",
    height: "4px",
    borderRadius: "10px",
    background: "#17344c",
    overflow: "hidden",
  },


  confidenceFill: {
    height: "100%",
    background: "#35baf3",
    borderRadius: "10px",
  },


  locationCell: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
    color: "#769bb9",
    fontSize: "10px",
  },


  busCell: {
    color: "#a8c9e2",
    fontWeight: 700,
  },


  timeCell: {
    color: "#6587a4",
    fontSize: "10px",
  },


  emptyState: {
    display: "flex",
    alignItems: "center",
    gap: "13px",
    padding: "28px 20px",
  },


  emptyIcon: {
    width: "36px",
    height: "36px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: "10px",
    background: "rgba(52,226,157,0.08)",
    color: "#43d69b",
  },


  emptyTitle: {
    fontSize: "12px",
    fontWeight: 800,
  },


  emptyText: {
    marginTop: "3px",
    color: "#5d809e",
    fontSize: "10px",
  },


  bottomGrid: {
    display: "grid",
    gridTemplateColumns:
      "repeat(4, minmax(0, 1fr))",
    gap: "14px",
    marginTop: "4px",
  },


  smallPanel: {
    display: "flex",
    alignItems: "center",
    gap: "13px",
    padding: "18px",
    borderRadius: "13px",
    border: "1px solid #173954",
    background: "#091927",
  },


  smallPanelIcon: {
    width: "42px",
    height: "42px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: "10px",
    background: "#102e47",
    fontSize: "18px",
  },


  smallPanelLabel: {
    color: "#527d9e",
    fontSize: "8px",
    fontWeight: 800,
    letterSpacing: "1px",
  },


  smallPanelValue: {
    marginTop: "2px",
    fontSize: "23px",
    fontWeight: 800,
  },


  smallPanelText: {
    color: "#5e829f",
    fontSize: "9px",
  },


  footer: {
    display: "flex",
    justifyContent: "space-between",
    gap: "15px",
    marginTop: "30px",
    paddingTop: "18px",
    borderTop: "1px solid #122b41",
    color: "#46657e",
    fontSize: "9px",
    letterSpacing: ".5px",
  },
};