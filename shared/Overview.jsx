import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Bell, Bus, MapPin, Navigation, RefreshCw, Route, ShieldCheck, Video } from 'lucide-react';
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
  if(!government) return <CitizenOverview data={data} rows={rows} error={error} busy={busy} refresh={refresh} prefix={prefix} selected={selected} setSelected={setSelected}/>;
  return <div className="civic-ui civic-overview">
    <header className="civic-heading"><div><span className="civic-kicker">Bengaluru · {government ? 'City operations' : 'Road conditions'}</span>
      <h1>{government ? 'City overview' : 'A clearer view of your journey.'}</h1><p>{government ? 'Review current incidents, inspect evidence and coordinate a response.' : 'Check reported hazards and choose a route that balances time and road conditions.'}</p></div>
      <button onClick={refresh} disabled={busy}><RefreshCw size={16}/>{busy?'Updating…':'Refresh'}</button></header>
    {error&&<p className="civic-error" role="alert">{error}</p>}
    <div className="civic-metrics">{[[Bell,'Active alerts',data?.total,'/alerts'],[MapPin,'Mapped incidents',data?.mapped,government?'/detections':'/map'],[Video,'With video evidence',data?.with_evidence,`${prefix}/ai-results`],
      [government?Bus:Route,government?'Buses reporting GPS':'Plan a journey',government?fleet?.online_buses:'Start here',government?'/fleet':'/plan-route']].map(([Icon,title,value,url])=><a className="civic-metric" href={url} key={title}><span><Icon size={18}/>{title}<ArrowUpRight size={15}/></span><strong>{value??'—'}</strong></a>)}</div>
    <div className="civic-overview-grid"><section className="civic-panel"><div className="civic-panel-heading"><div><h2>On the map</h2><p>{data ? `${data.mapped} active incident${data.mapped===1?'':'s'} with coordinates` : 'Loading incidents…'}</p></div><a href={government?'/detections':'/map'}>Open map <ArrowUpRight size={15}/></a></div>
      <RecordsMap items={rows} selected={selected} onSelect={setSelected} government={government}/>
      <div className="civic-map-caption">The map includes saved video evidence with assigned reference points; open a pin to review its footage and source location.{data?.missing_location ? ` ${data.missing_location} reports are awaiting coordinates.` : ''}</div></section>
      <section className="civic-panel"><div className="civic-panel-heading"><div><h2>Recorded alerts</h2></div><a href="/alerts">View all <ArrowUpRight size={15}/></a></div>
        <div className="civic-record-list">{rows.slice(0,6).map(item=><a key={item.id} href={`${prefix}${evidencePath(item)}`} className="civic-record">
          <span className="civic-issue-dot" style={{background:issueColour(item.alert_type)}}/><div><strong>{incidentName(item)}</strong><span>{incidentPlace(item)}</span><small>{incidentDate(item)} · {incidentReference(item)}</small><span className="civic-record-action">{item.evidence_available?'View video & images':'View issue details'} <ArrowUpRight size={13}/></span></div><span className={`civic-priority ${item.severity}`}>{item.severity || 'medium'}</span></a>)}
          {!rows.length&&<div className="civic-empty"><Bell size={26}/><h3>{busy?'Loading alerts…':'No active alerts'}</h3><p>New reports will appear here once received.</p></div>}
          {rows.length>6&&<a className="civic-list-more" href="/alerts">View all {rows.length} recorded alerts</a>}</div></section></div>
    <div className="civic-footer-notes"><span>Updated {data ? new Date(data.updated_at).toLocaleTimeString('en-IN') : '—'} · refreshes every 15 seconds</span>
    </div>
  </div>;
}

function CitizenOverview({data,rows,error,busy,refresh,prefix,selected,setSelected}) {
  const recent=rows.slice(0,4);
  return <div className="civic-ui civic-overview citizen-overview">
    <header className="citizen-welcome">
      <div><span className="civic-kicker">Bengaluru · before you drive</span><h1>Check the road. Then go.</h1>
        <p>See reported hazards, check traffic on the map, and choose a route that works for you.</p></div>
      <button className="citizen-refresh" onClick={refresh} disabled={busy} aria-label="Refresh road reports"><RefreshCw size={16}/>{busy?'Updating':'Refresh'}</button>
    </header>

    {error&&<p className="civic-error" role="alert">{error}</p>}

    <section className="citizen-route-card" aria-labelledby="citizen-route-heading">
      <div className="citizen-route-copy"><span className="citizen-card-kicker"><Navigation size={14}/> PLAN A DRIVE</span>
        <h2 id="citizen-route-heading">Where are you headed?</h2>
        <p>Compare driving routes using current traffic when available and active mapped road reports.</p>
        <div className="citizen-route-actions"><Link className="citizen-route-primary" to="/plan-route">Plan a route <ArrowRight size={17}/></Link>
          <Link className="citizen-route-secondary" to="/map">Open live map <ArrowUpRight size={15}/></Link></div>
      </div>
      <div className="citizen-route-illustration" aria-hidden="true"><span className="citizen-route-stop citizen-route-origin"><span/></span><i/><span className="citizen-route-stop citizen-route-destination"><MapPin size={22}/></span></div>
    </section>

    <div className="citizen-road-summary" aria-label="Active road report summary">
      <div><Bell size={17}/><span>Active reports</span><strong>{data?.total??'—'}</strong></div>
      <div><MapPin size={17}/><span>Mapped locations</span><strong>{data?.mapped??'—'}</strong></div>
      <div><Video size={17}/><span>With video</span><strong>{data?.with_evidence??'—'}</strong></div>
    </div>

    <div className="citizen-dashboard-grid">
      <section className="civic-panel citizen-map-panel"><div className="civic-panel-heading"><div><h2>Road conditions</h2>
        <p>{data?`${data.mapped} active report${data.mapped===1?'':'s'} mapped around Bengaluru`:'Loading road reports…'}</p></div><Link to="/map">Full map <ArrowUpRight size={15}/></Link></div>
        <RecordsMap items={rows} selected={selected} onSelect={setSelected}/>
        <p className="civic-map-caption">Traffic appears when available. Video evidence pins open the saved recording and detector readings.</p>
      </section>

      <section className="civic-panel citizen-reports-panel"><div className="civic-panel-heading"><div><h2>Recent road reports</h2>
        <p>{data?`${data.total} active report${data.total===1?'':'s'}`:'Reports refresh every 15 seconds'}</p></div><Link to="/map">View map <ArrowUpRight size={15}/></Link></div>
        <div className="citizen-recent-list">{recent.map(item=><a key={item.id} href={`${prefix}${evidencePath(item)}`} className="citizen-recent-report">
          <span className="civic-issue-dot" style={{background:issueColour(item.alert_type)}}/><span className="citizen-recent-copy"><strong>{incidentName(item)}</strong><span>{incidentPlace(item)}</span><small>{incidentDate(item)} · {incidentReference(item)}</small></span><ArrowUpRight size={15}/>
        </a>)}
          {!recent.length&&<div className="citizen-reports-empty"><ShieldCheck size={24}/><strong>{busy?'Checking for reports…':error?'Reports are unavailable':'No active reports right now'}</strong><span>{busy?'':error?'Try refreshing, or check the map again in a moment.':'You can still check traffic or plan a route.'}</span>{!busy&&<Link to="/plan-route">Plan a route <ArrowRight size={14}/></Link>}</div>}
          {rows.length>recent.length&&<Link className="citizen-reports-more" to="/map">Open incident map <ArrowRight size={15}/></Link>}
        </div>
      </section>
    </div>

    <div className="citizen-safety-note"><ShieldCheck size={18}/><p>Reports help you make a more informed choice, but conditions can change and a map cannot guarantee a clear road.</p>
      <Link to="/report">Report a road issue <ArrowUpRight size={14}/></Link></div>
    <div className="civic-footer-notes"><span>{data?`Updated ${new Date(data.updated_at).toLocaleTimeString('en-IN')} · refreshes every 15 seconds`:'Connecting to road reports'}</span></div>
  </div>;
}
