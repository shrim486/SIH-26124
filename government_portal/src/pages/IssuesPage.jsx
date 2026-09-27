import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { governmentApi } from '../api/governmentApi';
import OperationsMap, { label } from '../components/OperationsMap';
import '../operations.css';
import { sampleText } from '../../../shared/sampleText';
import IssueEvidence from '../components/IssueEvidence';
import { incidentName,incidentPlace,incidentReference } from '../../../shared/incidentPresentation';

const titles = {road:'Road Issues', accidents:'Accidents', violations:'Traffic Violations', all:'Detected Issues Map'};
const statuses = ['open', 'in_progress', 'resolved', 'closed'];

function History({id, revision}) {
  const [rows,setRows] = useState(null), [error,setError] = useState('');
  useEffect(() => {
    let current = true; setRows(null); setError('');
    governmentApi.getIssueHistory(id).then(data => {if (current) setRows(data);}).catch(err => {if (current) setError(err.message);});
    return () => {current = false;};
  }, [id, revision]);
  return <details><summary>Status history</summary>{error && <p role="alert">{error}</p>}
    {rows === null ? <p>Loading history…</p> : !rows.length ? <p>No status changes yet.</p> : rows.map(row => <p key={row.id}>
      <strong>{label(row.previous_status)} → {label(row.status)}</strong><br />{new Date(row.created_at).toLocaleString('en-IN')} · {row.actor}{row.note && <><br />{sampleText(row.note)}</>}
    </p>)}</details>;
}

export default function IssuesPage({category = 'all'}) {
  const [params] = useSearchParams();
  const [items,setItems] = useState([]), [status,setStatus] = useState(params.has('issue') ? 'all' : 'active'), [type,setType] = useState('all');
  const [activeIds,setActiveIds] = useState([]);
  const [showDemo,setShowDemo] = useState(true), [selected,setSelected] = useState(Number(params.get('issue')) || null);
  const [busy,setBusy] = useState(false), [saving,setSaving] = useState(false), [error,setError] = useState('');
  const [note,setNote] = useState(''), [message,setMessage] = useState(''), [revision,setRevision] = useState(0);
  const requestId = useRef(0), mutating = useRef(false);
  const bus = params.get('bus');
  const load = useCallback(async () => {
    const id = ++requestId.current; setBusy(true);
    try {
      const [data,records] = await Promise.all([governmentApi.getIssues({...category !== 'all' ? {category} : {}, ...bus ? {bus_id:bus} : {}}),governmentApi.getRecords()]);
      if (id === requestId.current) {setItems(data); setActiveIds(records.records.map(row=>row.event_id));setError('');}
    } catch(err) {if (id === requestId.current) setError(err.message);}
    finally {if (id === requestId.current) setBusy(false);}
  }, [category,bus]);
  useEffect(() => {
    setType('all'); load();
    const timer = setInterval(() => {if (!mutating.current) load();}, 15000);
    return () => {++requestId.current; clearInterval(timer);};
  }, [load]);
  const visible = items.filter(item => (showDemo || !item.is_demo) && (status === 'all' || (status === 'active' ? activeIds.includes(item.id) : item.status === status)) && (type === 'all' || item.event_type === type));
  const current = selected!==null ? visible.find(item => item.id === selected) : visible[0];
  useEffect(() => {setNote('');}, [current?.id]);
  useEffect(() => {setMessage('');}, [selected]);
  async function update(next) {
    mutating.current = true; setSaving(true); setError(''); setMessage(''); ++requestId.current;
    try {
      await governmentApi.updateIssueStatus(current.id, next, note);
      setMessage(`${incidentName(current)} · ${label(next)}. ${['resolved','closed'].includes(next) ? 'Its public alert has been cleared.' : ['resolved','closed'].includes(current.status) ? 'Its public alert has been restored.' : 'Status saved.'}`);
      setNote(''); setRevision(value => value + 1); await load();
    } catch(err) {setError(err.message);}
    finally {mutating.current = false; setSaving(false);}
  }
  return <div className="page-shell operations civic-ui">
    <div className="page-header"><div><p className="eyebrow">Government response</p><h1>{titles[category]}</h1>
      <p>Review map locations and evidence, assign a status and track resolution.</p></div><button disabled={busy || saving} onClick={load}>{busy ? 'Refreshing…' : 'Refresh'}</button></div>
    <div className="stats-grid">{statuses.map(value => <div key={value} className="stat-card"><span>{label(value)}</span><strong>{items.filter(item => item.status === value).length}</strong></div>)}</div>
    <div className="filter-bar"><label>Status <select value={status} onChange={e => {setStatus(e.target.value);setSelected(null);}}><option value="active">Active alerts</option><option value="all">All recorded issues</option>{statuses.map(value => <option key={value} value={value}>{label(value)}</option>)}</select></label>
      <label>Issue <select value={type} onChange={e => {setType(e.target.value);setSelected(null);}}><option value="all">All issue types</option>{[...new Set(items.map(i => i.event_type))].map(value => <option key={value} value={value}>{incidentName({event_type:value})}</option>)}</select></label>
      <label><input type="checkbox" checked={showDemo} onChange={e => setShowDemo(e.target.checked)} /> Include assigned map locations</label>
      {bus && <Link to="/detections">Show issues from all vehicles</Link>}</div>
    {showDemo && items.some(item => item.is_demo) && <p className="operations-note">Assigned coordinates and times are for map visualization; recording locations are unverified.</p>}
    {error && <p className="error-panel" role="alert">{error}</p>}{message && <p role="status" className="operations-note">{message}</p>}
    <div className="operations-grid"><section className="panel"><h2>{visible.length} issues on map</h2><OperationsMap items={visible} selected={current?.id} onSelect={setSelected} />
      <p className="operations-note">Grey pins are resolved or closed. Select a pin or open a row below.</p></section>
      <section className="panel issue-detail" id="selected-case" aria-label="Selected issue">{!current ? <><h2>Select an issue</h2><p>The requested issue is not in the current results. Choose a row or change the filters.</p></> : <>
        <h2>{incidentName(current)}</h2><p className="civic-meta">{incidentReference(current)}</p><p>{label(current.status)} · {current.severity || 'medium'} priority</p>
        <p>{incidentPlace(current)}<br />{current.is_demo ? 'Map location assigned for visualization' : label(current.location_source)}</p>
        <p>{new Date(current.timestamp).toLocaleString('en-IN')}{current.is_demo ? ' · assigned time' : ''}</p>
        {current.description && <details><summary>Recording details</summary><p>{sampleText(current.description)}</p></details>}
        <div className="operations-actions"><a href={`${import.meta.env.VITE_USER_PORTAL_URL || 'http://127.0.0.1:5173'}/map?incident=${current.id}`} target="_blank" rel="noreferrer">Citizen map</a>
          {current.evidence_available ? <><a href="#issue-evidence">View video & detected images below</a><Link to={`/ai-results?incident=${current.id}`}>Open evidence page</Link></> : <span>No video linked to this report</span>}</div>
        {current.category === 'violations' && <div className="operations-note"><strong>Number plate review</strong><p>Candidate for review; no automatic fine.</p>
          {current.reported_registration && <p>Reported registration: {current.reported_registration}</p>}
          {!current.plate_matches.length && !current.reported_registration && <p>No readable plate reliably linked.</p>}
          {current.plate_matches.map((match,index) => <p key={index}>{match.plate_text || 'Unreadable plate'} · {label(match.reading_status)}; unverified.
            {current.evidence_available && <><br /><Link to={`/ai-results?incident=${current.id}&time=${match.time_seconds}`}>Review rider and plate frame</Link></>}</p>)}</div>}
        <label>Action note (optional)<textarea maxLength={1000} value={note} onChange={e => setNote(e.target.value)} placeholder="Inspection or resolution details" /></label>
        <div className="operations-actions">{statuses.filter(value => value !== current.status).map(value => <button key={value} disabled={saving} onClick={() => update(value)}>
          {saving ? 'Saving…' : value === 'open' ? 'Reopen issue' : value === 'in_progress' ? 'Start review' : value === 'resolved' ? 'Resolve issue' : 'Close issue'}</button>)}</div>
        <History id={current.id} revision={`${revision}-${current.status}`} />
      </>}</section></div>
    {current && <section id="issue-evidence" className="panel issue-evidence-panel">
      <h2>Video & detected images · {incidentName(current)}</h2>
      {current.evidence_available ? <IssueEvidence incidentId={current.id} /> : <p>No annotated video or detected images have been attached to this report.</p>}
    </section>}
    <section className="panel"><div className="table-wrapper"><table className="data-table"><thead><tr><th>Issue</th><th>Location</th><th>Status</th><th>Time</th><th>Action</th></tr></thead>
      <tbody>{visible.map(item => <tr key={item.id}><td>{incidentName(item)}<small>{incidentReference(item)}</small></td><td>{incidentPlace(item)}{item.is_demo && <small>Assigned map location</small>}</td>
        <td>{label(item.status)}</td><td>{new Date(item.timestamp).toLocaleString('en-IN')}</td><td><div className="operations-actions"><button onClick={() => {setSelected(item.id);document.getElementById('selected-case')?.scrollIntoView({behavior:'smooth',block:'start'});}}>Review issue</button>
          {item.evidence_available && <Link to={`/ai-results?incident=${item.id}`}>Video & images</Link>}</div></td></tr>)}</tbody></table></div>
      {!visible.length && <p>{busy ? 'Loading issues…' : 'No issues match these filters.'}</p>}</section>
  </div>;
}
