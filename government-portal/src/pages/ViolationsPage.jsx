import { useEffect, useMemo, useState } from 'react';
import { governmentApi } from '../api/governmentApi';

const statuses = [
  'all',
  'open',
  'under_review',
  'in_progress',
  'resolved',
];

export default function RoadIssuesPage() {
  const [issues, setIssues] = useState([]);
  const [status, setStatus] = useState('all');
  const [type, setType] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updating, setUpdating] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      setError('');

      const data = await governmentApi.getRoadIssues(
        status === 'all' ? {} : { status }
      );

      setIssues(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Road issues loading error:', err);
      setError('Unable to load road issues.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [status]);

  const types = useMemo(
    () => [
      'all',
      ...new Set(
        issues.map((issue) => issue.issue_type).filter(Boolean)
      ),
    ],
    [issues]
  );

  const filtered = issues.filter(
    (issue) => type === 'all' || issue.issue_type === type
  );

  const counts = {
    total: issues.length,
    open: issues.filter((x) => x.status === 'open').length,
    progress: issues.filter((x) => x.status === 'in_progress').length,
    resolved: issues.filter((x) => x.status === 'resolved').length,
  };

  const updateStatus = async (id, nextStatus) => {
    try {
      setUpdating(id);
      setError('');

      await governmentApi.updateRoadIssueStatus(id, nextStatus);
      await load();
    } catch (err) {
      console.error('Road issue update error:', err);
      setError('Unable to update issue status.');
    } finally {
      setUpdating(null);
    }
  };

  if (loading) {
    return (
      <div className="loading-shell">
        Loading road intelligence...
      </div>
    );
  }

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <p className="eyebrow">Infrastructure operations</p>
          <h1>Road Issues</h1>
          <p>Monitor and manage AI-detected road conditions.</p>
        </div>

        <button className="primary-button" onClick={load}>
          Refresh
        </button>
      </div>

      <div className="stats-grid">
        <Stat label="Total issues" value={counts.total} tone="cyan" />
        <Stat label="Open" value={counts.open} tone="amber" />
        <Stat label="In progress" value={counts.progress} tone="violet" />
        <Stat label="Resolved" value={counts.resolved} tone="rose" />
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Detected road issues</h2>
            <p>AI fleet observations requiring government action</p>
          </div>
        </div>

        <div className="filter-bar">
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            {types.map((item) => (
              <option key={item} value={item}>
                {item === 'all'
                  ? 'All issue types'
                  : formatLabel(item)}
              </option>
            ))}
          </select>

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            {statuses.map((item) => (
              <option key={item} value={item}>
                {item === 'all'
                  ? 'All statuses'
                  : formatLabel(item)}
              </option>
            ))}
          </select>
        </div>

        {error && <div className="error-panel">{error}</div>}

        {filtered.length === 0 ? (
          <div className="empty-state">
            No road issues found.
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Issue</th>
                  <th>Severity</th>
                  <th>Location</th>
                  <th>Last detected</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {filtered.map((issue) => (
                  <tr key={issue.id}>
                    <td>
                      <strong>
                        {formatLabel(issue.issue_type || 'Road issue')}
                      </strong>
                    </td>

                    <td>
                      <span
                        className={`severity-badge ${String(
                          issue.severity || 'medium'
                        ).toLowerCase()}`}
                      >
                        {issue.severity || 'N/A'}
                      </span>
                    </td>

                    <td>
                      {issue.latitude != null &&
                      issue.longitude != null
                        ? `${issue.latitude}, ${issue.longitude}`
                        : 'N/A'}
                    </td>

                    <td>
                      {issue.last_detected
                        ? new Date(
                            issue.last_detected
                          ).toLocaleString('en-IN')
                        : 'N/A'}
                    </td>

                    <td>
                      <span className="status-badge">
                        {formatLabel(issue.status || 'N/A')}
                      </span>
                    </td>

                    <td>
                      <select
                        disabled={updating === issue.id}
                        value={issue.status || 'open'}
                        onChange={(e) =>
                          updateStatus(issue.id, e.target.value)
                        }
                      >
                        {statuses
                          .filter((item) => item !== 'all')
                          .map((item) => (
                            <option key={item} value={item}>
                              {formatLabel(item)}
                            </option>
                          ))}
                      </select>
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

function Stat({ label, value, tone = 'cyan' }) {
  return (
    <div className={`stat-card ${tone}`}>
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