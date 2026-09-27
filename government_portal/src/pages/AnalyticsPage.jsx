import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { governmentApi } from '../api/governmentApi';
import { incidentName } from '../../../shared/incidentPresentation';
export default function AnalyticsPage(){
  const [data,setData]=useState(null),[archive,setArchive]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const request=useRef(null);
  const load=useCallback(async()=>{request.current?.abort();const controller=new AbortController();request.current=controller;setBusy(true);
    try{const result=await governmentApi.getRecords(archive,controller.signal);if(!controller.signal.aborted){setData(result);setError('');}}
    catch(err){if(!controller.signal.aborted)setError(err.message);}finally{if(!controller.signal.aborted)setBusy(false);}
  },[archive]);
  useEffect(()=>{load();return()=>request.current?.abort();},[load]);
  const records=data?.archive===archive?data.records:[],types=[...new Set(records.map(row=>row.alert_type))];
  return <div className="page-shell civic-ui"><header className="civic-heading"><div><span className="civic-kicker">Reporting overview</span><h1>Incident analytics</h1><p>Counts from the same recorded alerts used on both portal maps.</p></div><button disabled={busy} onClick={load}>{busy?'Updating…':'Refresh analytics'}</button></header>
    <div className="civic-toolbar"><label>Records <select value={archive?'archive':'active'} onChange={e=>setArchive(e.target.value==='archive')}><option value="active">Active alerts</option><option value="archive">Resolved / dismissed</option></select></label></div>
    {error&&<p role="alert" className="civic-error">{error}</p>}
    <div className="civic-metrics">{[['Recorded alerts',records.length],['Mapped incidents',records.filter(row=>row.has_location).length],['With evidence',records.filter(row=>row.evidence_available).length],['Coordinates pending',records.filter(row=>!row.has_location).length]].map(([title,value])=><div className="civic-metric" key={title}><span>{title}</span><strong>{data?value:'—'}</strong></div>)}</div>
    <div className="fleet-forms"><section className="civic-panel"><div className="civic-panel-heading"><h2>Issues by type</h2></div><div className="table-wrapper"><table className="data-table"><thead><tr><th>Issue</th><th>Recorded alerts</th></tr></thead><tbody>{types.map(type=><tr key={type}><td><Link to={`/alerts?type=${type}&archive=${archive}`}>{incidentName({alert_type:type})}</Link></td><td>{records.filter(row=>row.alert_type===type).length}</td></tr>)}</tbody></table>{!records.length&&<p className="civic-empty">{busy?'Loading…':'No records in this view.'}</p>}</div></section>
      <section className="civic-panel"><div className="civic-panel-heading"><h2>Priority breakdown</h2></div><table className="data-table"><thead><tr><th>Priority</th><th>Recorded alerts</th></tr></thead><tbody>{['critical','high','medium','low'].map(severity=><tr key={severity}><td><span className={`civic-priority ${severity}`}>{severity}</span></td><td>{records.filter(row=>row.severity===severity).length}</td></tr>)}</tbody></table></section></div>
    <p className="civic-meta">Assigned map positions are included and retain their provenance on the individual record. Counts describe reported issues, not detector accuracy.</p>
  </div>;
}
