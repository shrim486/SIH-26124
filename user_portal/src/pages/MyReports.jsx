import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileWarning, MapPin, RefreshCw } from "lucide-react";

import { userApi } from "../api/userApi";
import StatusBadge from "../components/StatusBadge";
import { incidentName } from "../../../shared/incidentPresentation";

export default function MyReports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true); setError('');
        const data = await userApi.getReports();

        setReports(
          Array.isArray(data)
            ? data
            : data?.events || []
        );
      } catch (error) {
        setError(error.message || 'Could not load reports.');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [refresh]);

  return <section className="page-shell civic-ui citizen-reports-page">
    <header className="civic-heading"><div><span className="civic-kicker">Your activity</span><h1>My reports</h1>
      <p>Follow the status of issues you have reported.</p></div>
      <button className="civic-refresh-button" onClick={() => setRefresh(value => value + 1)} disabled={loading}><RefreshCw size={16}/>{loading ? 'Refreshing' : 'Refresh'}</button>
    </header>
    {error && <p className="civic-error" role="alert">{error}</p>}
    <section className="civic-panel citizen-reports-card">
      <div className="civic-panel-heading"><div><h2>Submitted reports</h2>{reports.length > 0 && <p>{reports.length} report{reports.length === 1 ? '' : 's'}</p>}</div></div>
      {loading ? <div className="civic-empty"><span className="civic-loading-mark" aria-hidden="true"/><p>Loading your reports…</p></div> : reports.length === 0 ?
        <div className="civic-empty"><FileWarning size={28}/><h3>No reports yet</h3><p>Reports you submit will appear here.</p><Link className="civic-primary-link" to="/report">Report an issue</Link></div> :
        <div className="citizen-report-list">{reports.map(report => {
          const hasLocation = report.latitude != null && report.longitude != null && Number.isFinite(Number(report.latitude)) && Number.isFinite(Number(report.longitude));
          return <article className="citizen-report-row" key={report.id}>
            <span className="civic-issue-dot" aria-hidden="true"/>
            <div className="citizen-report-copy"><strong>{incidentName({event_type:report.event_type})}</strong>
              <span><MapPin size={13}/>{hasLocation ? `${Number(report.latitude).toFixed(5)}, ${Number(report.longitude).toFixed(5)}` : 'Location unavailable'}</span>
            </div>
            <StatusBadge value={report.status || 'new'}/>
            <time>{report.timestamp ? new Date(report.timestamp).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'}) : 'Recently reported'}</time>
          </article>;
        })}</div>}
    </section>
  </section>;
}
