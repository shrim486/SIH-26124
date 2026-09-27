import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Bell, MapPin, Video, Bus, RefreshCw, Route, AlertTriangle } from 'lucide-react';
import RecordsMap, { issueColour } from './RecordsMap';
import { incidentName, incidentPlace, incidentDate, evidencePath, incidentReference } from './incidentPresentation';

export default function Overview({loadRecords,loadFleet,government=false}) {
  const [data,setData]=useState(null),[fleet,setFleet]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[selected,setSelected]=useState(null);
  const request=useRef(null);
  const refresh=useCallback(async()=>{
    request.current?.abort(); const controller=new AbortController();request.current=controller;setBusy(true);
    try {const [records,vehicles]=await Promise.all([loadRecords(false,controller.signal),loadFleet ? loadFleet(controller.signal) : null]);
      if(!controller.signal.aborted){setData(records);setFleet(vehicles);setError('');}
    }catch(err){if(!controller.signal.aborted)setError(err.message);}
    finally{if(!controller.signal.aborted)setBusy(false);}
  },[loadRecords,loadFleet]);
  useEffect(()=>{refresh();const timer=setInterval(refresh,15000);return()=>{request.current?.abort();clearInterval(timer);};},[refresh]);
  const rows=data?.records || [],prefix=government ? '' : (import.meta.env.VITE_GOVERNMENT_PORTAL_URL || 'http://127.0.0.1:5174');
  return <div className="civic-ui civic-overview">
    <header className="civic-heading"><div><span className="civic-kicker">Bengaluru · {government ? 'City operations' : 'Road conditions'}</span>
      <h1>{government ? 'City overview' : 'A clearer view of your journey.'}</h1><p>{government ? 'Review current incidents, inspect evidence and coordinate a response.' : 'Check reported hazards and choose a route that balances time and road conditions.'}</p></div>
      <button onClick={refresh} disabled={busy}><RefreshCw size={16}/>{busy?'Updating…':'Refresh'}</button></header>
    {error&&<p className="civic-error" role="alert">{error}</p>}
    <div className="civic-metrics">{[[Bell,'Active alerts',data?.total,'/alerts'],[MapPin,'Mapped incidents',data?.mapped,government?'/detections':'/map'],[Video,'With video evidence',data?.with_evidence,`${prefix}/ai-results`],
      [government?Bus:Route,government?'Buses reporting GPS':'Plan a journey',government?fleet?.online_buses:'Start here',government?'/fleet':'/plan-route']].map(([Icon,title,value,url])=><a className="civic-metric" href={url} key={title}><span><Icon size={18}/>{title}<ArrowUpRight size={15}/></span><strong>{value??'—'}</strong></a>)}</div>
    <div className="civic-overview-grid"><section className="civic-panel"><div className="civic-panel-heading"><div><h2>On the map</h2><p>{data ? `${data.mapped} active incident${data.mapped===1?'':'s'} with coordinates` : 'Loading incidents…'}</p></div><a href={government?'/detections':'/map'}>Open map <ArrowUpRight size={15}/></a></div>
      <RecordsMap items={rows} selected={selected} onSelect={setSelected} government={government}/>
      <div className="civic-map-caption">{data?.missing_location ? `${data.missing_location} records are awaiting coordinates and are listed below.` : 'The map and recorded alerts use the same incident list.'}</div></section>
      <section className="civic-panel"><div className="civic-panel-heading"><div><h2>Recorded alerts</h2><p>{data ? `${data.total} active records` : 'Loading records…'}</p></div><a href="/alerts">View all <ArrowUpRight size={15}/></a></div>
        <div className="civic-record-list">{rows.slice(0,6).map(item=><a key={item.id} href={`${prefix}${evidencePath(item)}`} className="civic-record">
          <span className="civic-issue-dot" style={{background:issueColour(item.alert_type)}}/><div><strong>{incidentName(item)}</strong><span>{incidentPlace(item)}</span><small>{incidentDate(item)} · {incidentReference(item)}</small><span className="civic-record-action">{item.evidence_available?'View video & images':'View issue details'} <ArrowUpRight size={13}/></span></div><span className={`civic-priority ${item.severity}`}>{item.severity || 'medium'}</span></a>)}
          {!rows.length&&<div className="civic-empty"><Bell size={26}/><h3>{busy?'Loading alerts…':'No active alerts'}</h3><p>New reports will appear here once received.</p></div>}
          {rows.length>6&&<a className="civic-list-more" href="/alerts">View all {rows.length} recorded alerts</a>}</div></section></div>
    <section className="civic-panel"><div className="civic-panel-heading"><div><h2>Issues at a glance</h2><p>Counts reflect the active reports shown on the map and in the alert list.</p></div></div>
      <div className="civic-category-grid">{[['helmet_violation','No helmet'],['traffic_violation','Traffic violations'],['waterlogging','Waterlogging'],['accident','Accidents'],['pothole','Potholes'],['road_damage','Road damage']].map(([kind,title])=>{
        const count=rows.filter(row=>kind==='traffic_violation'?['traffic_violation','triple_riding','rash_driving'].includes(row.alert_type):row.alert_type===kind).length;
        return <a href={`/alerts?type=${kind==='traffic_violation'?'violations':kind}`} key={kind}><span className="civic-issue-dot" style={{background:issueColour(kind)}}/><span>{title}</span><strong>{count}</strong><ArrowUpRight size={14}/></a>;
      })}</div></section>
    <div className="civic-footer-notes"><span>Updated {data ? new Date(data.updated_at).toLocaleTimeString('en-IN') : '—'} · refreshes every 15 seconds</span>
      {rows.some(row=>row.is_demo)&&<span><AlertTriangle size={14}/> Some records have assigned map locations. Their recording locations are unverified.</span>}</div>
  </div>;
}
