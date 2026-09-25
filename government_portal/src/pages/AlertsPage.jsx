import { useEffect, useState } from 'react';
import { governmentApi } from '../api/governmentApi';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      setLoading(true);
      setAlerts(await governmentApi.getAlerts());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return <div className="loading-shell">Loading alert intelligence...</div>;
  }

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <p className="eyebrow">Emergency intelligence</p>
          <h1>Alerts</h1>
          <p>Road hazard and traffic alerts.</p>
        </div>

        <button className="primary-button" onClick={load}>
          Refresh
        </button>
      </div>

      <div className="stats-grid">
        <div className="stat-card rose">
          <div className="stat-content">
            <span className="stat-label">Total incidents</span>
            <strong>{alerts.length}</strong>
          </div>
        </div>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Incident intelligence</h2>
            <p>Latest emergency events detected by the fleet</p>
          </div>
        </div>

        {alerts.length === 0 ? (
          <div className="empty-state">
            No alerts detected.
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Confidence</th>
                  <th>Severity</th>
                  <th>Location</th>
                  <th>Vehicle</th>
                  <th>Timestamp</th>
                </tr>
              </thead>

              <tbody>
                {alerts.map((event, index) => (
                  <tr key={event.id ?? index}>
                    <td>
                      <strong>
                        {event.alert_type || 'Alert'}
                      </strong>
                    </td>

                    <td>
                      {event.confidence != null
                        ? `${(event.confidence * 100).toFixed(1)}%`
                        : 'N/A'}
                    </td>

                    <td>
                      <span className="severity-badge rose">
                        {event.severity || 'N/A'}
                      </span>
                    </td>

                    <td>
                      {event.latitude != null && event.longitude != null
                        ? `${event.latitude}, ${event.longitude}`
                        : 'N/A'}
                    </td>

                    <td>
                      {event.registration_number ||
                        event.bus_id ||
                        'N/A'}
                    </td>

                    <td>
                      {event.created_at
                        ? new Date(event.created_at).toLocaleString('en-IN')
                        : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}