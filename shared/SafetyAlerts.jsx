import { useCallback, useEffect, useRef, useState } from 'react';
import { Search, RefreshCw, ArrowUpRight, MapPin, Bell } from 'lucide-react';
import RecordsMap, { issueColour } from './RecordsMap';
import { incidentName,incidentPlace,incidentReference,incidentDate,evidencePath,hasCoordinates } from './incidentPresentation';

const types=[['all','All issues'],['helmet_violation','No helmet'],['violations','Traffic violations'],['waterlogging','Waterlogging'],['accident','Accidents'],['pothole','Potholes'],['road_damage','Road damage'],['traffic','Traffic conditions']];
const matches=(item,type)=>type==='all'||(type==='violations'?['traffic_violation','triple_riding','rash_driving'].includes(item.alert_type):type==='traffic'?['congestion','bottleneck'].includes(item.alert_type):item.alert_type===type);
export default function SafetyAlerts({loadRecords,updateAlert,updateIssue,renderEvidence,government=false,title='Alerts & incidents'}) {
  const query=new URLSearchParams(window.location.search);
  const [data,setData]=useState(null),[type,setType]=useState(query.get('type')||'all'),[archive,setArchive]=useState(query.get('archive')==='true');
  const [search,setSearch]=useState(''),[selected,setSelected]=useState(Number(query.get('alert'))||null),[expanded,setExpanded]=useState(null),[fitKey,setFitKey]=useState(0);
  const [focusIncident,setFocusIncident]=useState(query.get('incident'));
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[action,setAction]=useState(null);
  const request=useRef(null),mutating=useRef(false),mounted=useRef(false);
  const refresh=useCallback(async()=>{
    request.current?.abort();const controller=new AbortController();request.current=controller;setBusy(true);
    try{const records=await loadRecords(archive,controller.signal);if(!controller.signal.aborted){setData(records);setError('');}}
    catch(err){if(!controller.signal.aborted)setError(err.message);}
    finally{if(!controller.signal.aborted)setBusy(false);}
  },[loadRecords,archive]);
  useEffect(()=>{mounted.current=true;refresh();const timer=setInterval(()=>{if(!mutating.current)refresh();},15000);return()=>{mounted.current=false;request.current?.abort();clearInterval(timer);};},[refresh]);
  const rows=data?.archive===archive?data.records:[];
  const visible=rows.filter(item=>matches(item,type)&&`${incidentName(item)} ${incidentPlace(item)} ${incidentReference(item)}`.toLowerCase().includes(search.toLowerCase()));
  const mapped=visible.filter(hasCoordinates),prefix=government?'':(import.meta.env.VITE_GOVERNMENT_PORTAL_URL||'http://127.0.0.1:5174');
  const focused=visible.find(item=>item.id===selected)||visible.find(item=>String(item.event_id)===focusIncident);
  function locate(id){setSelected(id);setFocusIncident(null);}
  async function change(item,kind){
    mutating.current=true;setAction(item.id);setError('');request.current?.abort();
    try{if(kind==='issue')await updateIssue(item.event_id,['resolved','closed'].includes(item.issue_status)?'open':'resolved');
      else await updateAlert(item.id,item.active?'dismissed':'active');
      if(mounted.current)await refresh();
    }catch(err){if(mounted.current)setError(err.message);}
    finally{mutating.current=false;if(mounted.current){setAction(null);setBusy(false);}}
  }
  return <section className="civic-ui civic-records">
    <header className="civic-heading"><div><span className="civic-kicker">Bengaluru · Road reports</span><h1>{title}</h1><p>One incident list, with matching locations, status and evidence.</p></div>
      <button onClick={refresh} disabled={busy||action!==null}><RefreshCw size={16}/>{busy?'Updating…':'Refresh'}</button></header>
    <div className="civic-toolbar"><label className="civic-search"><Search size={17}/><input aria-label="Search incidents" placeholder="Search issue, location or reference" value={search} onChange={e=>setSearch(e.target.value)}/></label>
      <label>Records <select value={archive?'archive':'active'} disabled={action!==null} onChange={e=>{setArchive(e.target.value==='archive');setSelected(null);setExpanded(null);}}><option value="active">Active alerts</option><option value="archive">Resolved / dismissed</option></select></label></div>
    <div className="civic-filters">{types.map(([key,label])=><button key={key} aria-pressed={type===key} onClick={()=>{setType(key);setSelected(null);}}>{label}<span>{rows.filter(item=>matches(item,key)).length}</span></button>)}</div>
    {error&&<p role="alert" className="civic-error">{error}</p>}
    <div className="civic-section-line"><span><strong>{visible.length}</strong> recorded alerts · <strong>{mapped.length}</strong> mapped{visible.length!==mapped.length&&` · ${visible.length-mapped.length} awaiting coordinates`}</span><small>{data?`Updated ${new Date(data.updated_at).toLocaleTimeString('en-IN')}`:'Loading…'}</small></div>
    <div className="civic-records-grid"><section className="civic-panel civic-map-sticky"><div className="civic-panel-heading"><h2>Incident locations</h2><button onClick={()=>{setSelected(null);setFocusIncident(null);setFitKey(value=>value+1);}}>Show all</button></div>
      <RecordsMap items={visible} selected={focused?.id} onSelect={locate} government={government} fitKey={fitKey}/>
      <p className="civic-map-caption">Open a map pin to view its own video and images. Records awaiting coordinates stay in the list.</p></section>
      <div className="civic-alert-list">{!visible.length&&<div className="civic-panel civic-empty"><Bell size={26}/><h2>{busy?'Loading records…':'No matching alerts'}</h2><p>Choose another filter or check back after a new report.</p></div>}
        {visible.map(item=><article key={item.id} id={`record-${item.id}`} className={`civic-panel civic-alert ${focused?.id===item.id?'is-selected':''}`}>
          <div className="civic-alert-heading"><span className="civic-issue-dot" style={{background:issueColour(item.alert_type)}}/><h2>{incidentName(item)}</h2><span className={`civic-priority ${item.severity}`}>{item.severity||'medium'}</span></div>
          <p className="civic-location">{incidentPlace(item)}</p><p className="civic-meta">{incidentDate(item)} · {incidentReference(item)}</p>
          <div className="civic-status-line"><span>{(item.issue_status||'open').replaceAll('_',' ')}</span>{!item.active&&<span>Alert archived</span>}{!hasCoordinates(item)&&<span>Coordinates pending</span>}</div>
          <details className="civic-record-details"><summary>Location & recording details</summary><p>{hasCoordinates(item)?`${item.latitude.toFixed(6)}, ${item.longitude.toFixed(6)}`:'Coordinates have not been supplied.'}</p><p>{item.is_demo?'Map location and time assigned for visualization; recording location unverified.':`Location source: ${(item.location_source||'supplied coordinates').replaceAll('_',' ')}`}</p></details>
          <div className="civic-actions"><a className="civic-primary-link" href={`${prefix}${evidencePath(item)}`}>{item.evidence_available?'Open video & images':'Open issue details'}<ArrowUpRight size={14}/></a>
            <button disabled={!hasCoordinates(item)} onClick={()=>{setSelected(item.id);document.querySelector('.civic-map-sticky')?.scrollIntoView({behavior:'smooth',block:'center'});}}><MapPin size={14}/>Locate</button>
            {government&&renderEvidence&&item.evidence_available&&<button onClick={()=>setExpanded(expanded===item.id?null:item.id)}>{expanded===item.id?'Hide preview':'Preview evidence'}</button>}</div>
          {!item.evidence_available&&<p className="civic-meta">No detection video is attached to this record.</p>}
          {!government&&item.evidence_available&&<p className="civic-meta">Evidence requires government sign-in.</p>}
          {expanded===item.id&&renderEvidence&&renderEvidence(item)}
          {government&&['helmet_violation','traffic_violation','triple_riding','rash_driving'].includes(item.alert_type)&&<details className="civic-record-details"><summary>Number plate review</summary>
            {item.reported_registration&&<p>Reported registration: <strong>{item.reported_registration}</strong></p>}
            {!item.plate_matches?.length&&!item.reported_registration&&<p>No readable plate is reliably linked to this report.</p>}
            {(item.plate_matches||[]).map((match,index)=><div key={index}><p><strong>{match.plate_text||'Unreadable plate'}</strong> · unverified OCR candidate</p><p>{match.reading_status==='repeated_ocr_candidate'?'Repeated in matching frames.':'Reading remains uncertain.'} Review the frame before taking action.</p>
              {item.evidence_available&&Number.isFinite(match.time_seconds)&&<a href={`${evidencePath(item)}&time=${match.time_seconds}`}>Review rider and plate at {match.time_seconds.toFixed(2)}s</a>}</div>)}
            <p>No automatic fine is issued from this reading.</p></details>}
          {government&&item.event_id&&<div className="civic-actions civic-case-actions"><a href={`/detections?issue=${item.event_id}`}>Review case</a>
            {updateIssue&&<button disabled={action!==null} onClick={()=>change(item,'issue')}>{action===item.id?'Saving…':['resolved','closed'].includes(item.issue_status)?'Reopen issue':'Resolve issue'}</button>}
            {updateAlert&&!['resolved','closed'].includes(item.issue_status)&&<button disabled={action!==null} onClick={()=>change(item,'alert')}>{item.active?'Dismiss alert':'Reactivate alert'}</button>}</div>}
        </article>)}
      </div></div>
    {rows.some(item=>item.is_demo)&&<p className="civic-footer-notes">Some positions and times are assigned for visualization; their recording locations are unverified.</p>}
  </section>;
}
