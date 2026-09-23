import { useEffect, useState } from 'react';
import { governmentApi } from '../api/governmentApi';

export default function AccidentsPage() {
  const [accidents, setAccidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      setLoading(true);
      setError('');

      const data = await governmentApi.getAccidents();

      setAccidents(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Accidents loading error:', err);
      setError('Unable to load accident intelligence.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return (
      <div className="loading-shell">
        Loading accident intelligence...
      </div>
    );
  }

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <p className="eyebrow">Emergency intelligence</p>
          <h1>Accidents</h1>
          <p>
            AI-detected accident and dangerous-driving events.
          </p>
        </div>

        <button className="primary-button" onClick={load}>
          Refresh
        </button>
      </div>

      <div className="stats-grid">
        <div className="stat-card rose">
          <div className="stat-content">
            <span className="stat-label">Total incidents</span>
            <strong>{accidents.length}</strong>
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

        {error && <div className="error-panel">{error}</div>}

        {accidents.length === 0 ? (
          <div className="empty-state">
            No accidents detected.
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
                {accidents.map((event, index) => (
                  <tr key={event.id ?? index}>
                    <td>
                      <strong>
                        {formatLabel(
                          event.event_type || 'Accident'
                        )}
                      </strong>
                    </td>

                    <td>
                      {event.confidence != null
                        ? `${(
                            Number(event.confidence) * 100
                          ).toFixed(1)}%`
                        : 'N/A'}
                    </td>

                    <td>
                      <span className="severity-badge rose">
                        {event.severity || 'N/A'}
                      </span>
                    </td>

                    <td>
                      {event.latitude != null &&
                      event.longitude != null
                        ? `${event.latitude}, ${event.longitude}`
                        : 'N/A'}
                    </td>

                    <td>
                      {event.registration_number ||
                        event.bus_id ||
                        'N/A'}
                    </td>

                    <td>
                      {event.timestamp
                        ? new Date(
                            event.timestamp
                          ).toLocaleString('en-IN')
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

function formatLabel(value) {
  return String(value)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}