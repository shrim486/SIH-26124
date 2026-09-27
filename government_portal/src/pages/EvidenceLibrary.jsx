import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { governmentApi } from '../api/governmentApi';
import IssueEvidence from '../components/IssueEvidence';
import { incidentName,incidentPlace,incidentReference,incidentDate } from '../../../shared/incidentPresentation';
import '../operations.css';
export default function EvidenceLibrary(){
  const [data,setData]=useState(null),[selected,setSelected]=useState(null),[type,setType]=useState('all'),[archive,setArchive]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const request=useRef(null);
  const load=useCallback(async()=>{request.current?.abort();const controller=new AbortController();request.current=controller;setBusy(true);
    try{const result=await governmentApi.getRecords(archive,controller.signal);if(!controller.signal.aborted){setData(result);setError('');}}
    catch(err){if(!controller.signal.aborted)setError(err.message);}finally{if(!controller.signal.aborted)setBusy(false);}
  },[archive]);
  useEffect(()=>{load();const timer=setInterval(load,15000);return()=>{request.current?.abort();clearInterval(timer);};},[load]);
  const records=data?.archive===archive?data.records:[],visible=records.filter(item=>type==='all'||item.alert_type===type),current=visible.find(item=>item.id===selected)||visible[0];
  return <section className="page-shell operations civic-ui"><header className="civic-heading"><div><span className="civic-kicker">Incident recordings</span><h1>Videos & images</h1><p>Each recording belongs to the incident and location shown beside it.</p></div><button disabled={busy} onClick={load}>{busy?'Updating…':'Refresh evidence'}</button></header>
    <div className="civic-toolbar"><label>Issue type <select value={type} onChange={e=>setType(e.target.value)}><option value="all">All types</option>{[...new Set(records.map(row=>row.alert_type))].map(kind=><option key={kind} value={kind}>{incidentName({alert_type:kind})}</option>)}</select></label><label>Records <select value={archive?'archive':'active'} onChange={e=>{setArchive(e.target.value==='archive');setType('all');setSelected(null);}}><option value="active">Active alerts</option><option value="archive">Resolved / dismissed</option></select></label><span>{visible.length} records · {visible.filter(row=>row.evidence_available).length} with footage</span></div>
    {error&&<p role="alert" className="civic-error">{error}</p>}
    {!visible.length&&<div className="civic-panel civic-empty"><h2>{busy?'Loading recordings…':'No records for these filters'}</h2></div>}
    {!!visible.length&&<div className="evidence-browser"><nav className="evidence-selector" aria-label="Incident recordings">{visible.map(item=><button key={item.id} aria-pressed={current?.id===item.id} onClick={()=>setSelected(item.id)}><strong>{incidentName(item)}</strong><span>{incidentPlace(item)}</span><span>{incidentDate(item)} · {incidentReference(item)}</span><span>{item.evidence_available?'Video and detected images':'Footage not attached'}</span></button>)}</nav>
      {current&&<section className="evidence-selected civic-panel"><h2>{incidentName(current)}</h2><p>{incidentPlace(current)}</p><p className="civic-meta">{incidentReference(current)} · {incidentDate(current)}</p><div className="civic-actions"><Link to={`/detections?issue=${current.event_id}`}>Review case & map</Link>{current.evidence_available&&<Link to={`/ai-results?incident=${current.event_id}`}>Open full evidence page</Link>}</div>
        {current.is_demo&&<p className="civic-meta">Map position and time assigned for visualization; recording location unverified.</p>}
        {current.evidence_available?<IssueEvidence incidentId={current.event_id}/>:<div className="civic-empty"><h3>No footage attached</h3><p>This record is retained so the recorded-alert count matches the map and incident list.</p></div>}</section>}</div>}
  </section>;
}
