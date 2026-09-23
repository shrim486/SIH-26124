import { useEffect, useState } from 'react';
import { governmentApi } from '../api/governmentApi';

export default function FleetPage() {
  const [fleet, setFleet] = useState({
    total_buses: 0,
    total_cameras: 0,
    buses: [],
    cameras: [],
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadFleet = async () => {
    try {
      setLoading(true);
      setError('');

      const data = await governmentApi.getFleet();

      setFleet({
        total_buses: data?.total_buses ?? 0,
        total_cameras: data?.total_cameras ?? 0,
        buses: Array.isArray(data?.buses) ? data.buses : [],
        cameras: Array.isArray(data?.cameras) ? data.cameras : [],
      });
    } catch (err) {
      console.error('Fleet loading error:', err);
      setError('Unable to load fleet data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFleet();
  }, []);

  if (loading) {
    return (
      <div className="loading-shell">
        <div className="loading-spinner" />
        <div className="loading-copy">
          <strong>Loading Fleet Monitoring</strong>
          <span>Fetching live fleet data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-shell">
        <div className="error-panel">
          <h2>Unable to load fleet</h2>
          <p>{error}</p>
          <button className="primary-button" onClick={loadFleet}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <p className="eyebrow">Fleet operations</p>
          <h1>Fleet Monitoring</h1>
          <p className="page-description">
            Monitor buses and camera infrastructure connected to the UrbanIQ network.
          </p>
        </div>

        <button className="primary-button" onClick={loadFleet}>
          Refresh fleet
        </button>
      </div>

      <div className="stats-grid">
        <StatCard
          icon="🚌"
          label="Total buses"
          value={fleet.total_buses}
          tone="cyan"
        />

        <StatCard
          icon="📷"
          label="Total cameras"
          value={fleet.total_cameras}
          tone="violet"
        />

        <StatCard
          icon="📡"
          label="Connected assets"
          value={fleet.total_buses + fleet.total_cameras}
          tone="indigo"
        />
      </div>

      <div className="content-grid">
        <FleetTable
          title="Bus fleet"
          description="Registered public transport vehicles"
          icon="🚌"
          rows={fleet.buses}
          emptyTitle="No buses registered"
          emptyText="No bus records are currently available in the fleet database."
        />

        <FleetTable
          title="Camera infrastructure"
          description="Camera devices installed across the fleet"
          icon="📷"
          rows={fleet.cameras}
          emptyTitle="No cameras registered"
          emptyText="No camera records are currently available in the database."
        />
      </div>
    </div>
  );
}

function FleetTable({
  title,
  description,
  icon,
  rows,
  emptyTitle,
  emptyText,
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>

        {title === 'Bus fleet' && (
          <span className="live-badge">● Live</span>
        )}
      </div>

      {rows.length === 0 ? (
        <div className="empty-state fleet-empty-state">
          <div className="empty-icon">{icon}</div>
          <strong>{emptyTitle}</strong>
          <span>{emptyText}</span>
        </div>
      ) : (
        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                {Object.keys(rows[0]).map((key) => (
                  <th key={key}>{formatLabel(key)}</th>
                ))}
              </tr>
            </thead>

            <tbody>
              {rows.map((row, index) => (
                <tr key={row.id ?? index}>
                  {Object.keys(rows[0]).map((key) => (
                    <td key={key}>{formatValue(row[key])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function StatCard({ icon, label, value, tone }) {
  return (
    <div className={`stat-card ${tone}`}>
      <div className="stat-icon">{icon}</div>

      <div className="stat-content">
        <span className="stat-label">{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function formatLabel(value) {
  return String(value)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }

  return String(value);
}