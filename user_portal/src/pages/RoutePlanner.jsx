import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup, Tooltip, useMap, useMapEvents } from 'react-leaflet';
import { MapPin, Navigation, Plus, ArrowUpDown, Route, Clock, ShieldCheck } from 'lucide-react';
import { userApi } from '../api/userApi';
import { incidentName, incidentPlace } from '../../../shared/incidentPresentation';
import { routeAlerts, alertSignature } from '../../../shared/routeAlerts';
import { alertMarkerStyle } from '../../../shared/alertMapStyle';
import AlertMapLegend from '../../../shared/AlertMapLegend';
import 'leaflet/dist/leaflet.css';
import './route-planner.css';

const blankPoint = () => ({label:'',latitude:null,longitude:null,dwell_minutes:0});
const located = point => point && Number.isFinite(point.latitude) && Number.isFinite(point.longitude);
const title = value => (value || '').replaceAll('_',' ').replace(/\b\w/g,char => char.toUpperCase());
const minutes = value => {
  const rounded = Math.round(value);
  return value < 1 ? '<1 min' : rounded < 60 ? `${rounded} min` : `${Math.floor(rounded/60)} hr ${rounded%60} min`;
};
const coords = text => {
  const match = text.match(/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/);
  if (!match) return null;
  const latitude = Number(match[1]), longitude = Number(match[2]);
  return Math.abs(latitude)<=85 && Math.abs(longitude)<=180 ? {latitude,longitude,label:`${latitude.toFixed(5)}, ${longitude.toFixed(5)}`} : null;
};

function PlaceField({id, heading, point, onChange, onPick, picking}) {
  const [results,setResults] = useState([]), [busy,setBusy] = useState(false), [error,setError] = useState('');
  const [searchedPoint,setSearchedPoint] = useState(null);
  const request = useRef(null);
  const pointKey = JSON.stringify([point.label,point.latitude,point.longitude]);
  const currentSearch = searchedPoint === pointKey;
  useEffect(() => () => request.current?.abort(), [pointKey]);
  async function search() {
    request.current?.abort();
    setSearchedPoint(pointKey);setBusy(false);
    const position = coords(point.label);
    if (position) {onChange({...point,...position});setResults([]);setError('');return;}
    if (point.label.trim().length<3 || point.label.trim().length>160) {setError('Enter a place name of 3–160 characters, or latitude, longitude.');return;}
    const controller = new AbortController(); request.current = controller;
    setBusy(true);setError('');setResults([]);
    try {
      const data = await userApi.searchPlaces(point.label,controller.signal);
      if (!controller.signal.aborted) {setResults(data.places);if (!data.places.length) setError('No places found. Add Bengaluru to the search or place a pin on the map.');}
    } catch(err) {if (err.name!=='AbortError') setError(err.message);}
    finally {if (!controller.signal.aborted) setBusy(false);}
  }
  return <div className="rp-place"><label htmlFor={`place-${id}`}>{heading}</label>
    <div className="rp-search"><input id={`place-${id}`} value={point.label} maxLength={250} placeholder="Search place or enter latitude, longitude"
      onKeyDown={event => {if (event.key==='Enter') {event.preventDefault();search();}}}
      onChange={event => {request.current?.abort();setBusy(false);setResults([]);setError('');onChange({...point,label:event.target.value,latitude:null,longitude:null});}} />
      <button type="button" disabled={currentSearch && busy} onClick={search}>{currentSearch && busy ? 'Finding…' : coords(point.label) ? 'Set' : 'Search'}</button>
      <button type="button" aria-label={`Pick ${heading.toLowerCase()} on map`} aria-pressed={picking} onClick={onPick}><MapPin size={17} /></button></div>
    {located(point) && <small className="rp-confirmed">Selected · {point.latitude.toFixed(5)}, {point.longitude.toFixed(5)}</small>}
    {currentSearch && !!results.length && <ul className="rp-place-results" aria-label={`${heading} search results`}>{results.map((result,index) => <li key={index}><button type="button" onClick={() => {onChange({...point,...result,label:result.label.slice(0,250)});setResults([]);}}>{result.label}</button></li>)}</ul>}
    {currentSearch && error && <p role="alert" className="rp-error">{error}</p>}
  </div>;
}

function MapView({route, points, focus, fitKey, alerts, view}) {
  const map = useMap();
  const alertPositions = JSON.stringify(alerts.map(p => [p.latitude,p.longitude]));
  useEffect(() => {
    if (focus) {map.setView([focus.latitude,focus.longitude],16);return;}
    const positions = view === 'alerts' ? JSON.parse(alertPositions) : route ? route.geometry.coordinates.map(([lon,lat]) => [lat,lon]) : points.filter(located).map(p => [p.latitude,p.longitude]);
    if (positions.length) map.fitBounds(positions,{padding:[35,35],maxZoom:14});
  }, [route, points, focus, fitKey, map, view, alertPositions]);
  return null;
}
function PinPicker({target,onPick}) {
  useMapEvents({click:event => {if (target) onPick(target,{latitude:event.latlng.lat,longitude:event.latlng.lng,label:`Map pin · ${event.latlng.lat.toFixed(5)}, ${event.latlng.lng.toFixed(5)}`});}});
  return null;
}

export default function RoutePlanner() {
  const [origin,setOrigin] = useState(blankPoint), [destination,setDestination] = useState(blankPoint), [stops,setStops] = useState([]);
  const [preference,setPreference] = useState('balanced'), [extra,setExtra] = useState(15), [assigned,setAssigned] = useState(false);
  const [result,setResult] = useState(null), [selected,setSelected] = useState(null), [busy,setBusy] = useState(false), [error,setError] = useState('');
  const [pick,setPick] = useState(null), [focus,setFocus] = useState(null), [fitKey,setFitKey] = useState(0), [showOther,setShowOther] = useState(true), [locating,setLocating] = useState(false);
  const [catalog,setCatalog] = useState(null), [alertsError,setAlertsError] = useState(''), [alertsBusy,setAlertsBusy] = useState(false), [view,setView] = useState('journey');
  const alertsRequest = useRef(null);
  const refreshAlerts = useCallback(async () => {
    alertsRequest.current?.abort(); const controller = new AbortController(); alertsRequest.current = controller; setAlertsBusy(true);
    try { const data = await userApi.getRecords(false, controller.signal); if (!controller.signal.aborted) { setCatalog(data); setAlertsError(''); } }
    catch (err) { if (!controller.signal.aborted) setAlertsError(err.message); }
    finally { if (!controller.signal.aborted) setAlertsBusy(false); }
  }, []);
  useEffect(() => { refreshAlerts(); const timer = setInterval(refreshAlerts,15000); return () => {clearInterval(timer);alertsRequest.current?.abort();}; }, [refreshAlerts]);
  const request = useRef(null), nextStop = useRef(1), geoRequest = useRef(0);
  useEffect(() => () => {request.current?.abort();geoRequest.current++;},[]);
  function invalidate() {request.current?.abort();setBusy(false);setResult(null);setSelected(null);setFocus(null);setError('');geoRequest.current++;setLocating(false);}
  function updatePoint(id, point) {
    invalidate();
    if (id==='origin') setOrigin(point);
    else if (id==='destination') setDestination(point);
    else setStops(previous => previous.map(stop => stop.id===id ? {...stop,...point} : stop));
    setPick(null);
  }
  function useLocation() {
    if (!navigator.geolocation) {setError('Location access is unavailable. Search for a place or use a map pin.');return;}
    const id = ++geoRequest.current;setLocating(true);setError('');
    navigator.geolocation.getCurrentPosition(position => {
      if (id!==geoRequest.current) return;
      updatePoint('origin',{...blankPoint(),latitude:position.coords.latitude,longitude:position.coords.longitude,label:'Current location'});
    }, () => {if (id===geoRequest.current) {setLocating(false);setError('Location access failed. Allow location permission or choose your start on the map.');}},
    {enableHighAccuracy:true,timeout:15000,maximumAge:60000});
  }
  function moveStop(index, offset) {
    invalidate();setStops(previous => {const copy=[...previous];[copy[index],copy[index+offset]]=[copy[index+offset],copy[index]];return copy;});
  }
  const points = useMemo(() => [origin,...stops,destination],[origin,stops,destination]);
  const current = result?.routes.find(route => route.id===selected) || result?.routes[0];
  const issueList = current?.issues || [];
  const displayedIssues = routeAlerts(catalog?.records || result?.issues || [], result?.issues, issueList, !current || showOther);
  const alertsChanged = result && catalog && result.alertSignature !== alertSignature(catalog.records);
  const markedPoints = result?.points || points;
  const toPayload = point => ({label:point.label,latitude:point.latitude,longitude:point.longitude,dwell_minutes:Number(point.dwell_minutes || 0)});
  async function plan(event) {
    event.preventDefault();setError('');setPick(null);
    if (!points.every(located)) {setError('Choose a search result or map pin for your start, every stop and drop-off.');return;}
    request.current?.abort();const controller = new AbortController();request.current = controller;
    setBusy(true);setResult(null);setFocus(null);
    try {
      const signature = alertSignature(catalog?.records || []);
      const data = await userApi.planRoute({origin:toPayload(origin),destination:toPayload(destination),stops:stops.map(toPayload),
        preference,max_extra_minutes:Number(extra),include_assigned:assigned},controller.signal);
      if (!controller.signal.aborted) {setResult({...data,alertSignature:signature});setSelected(data.recommended_route_id);setView('journey');setFitKey(value => value+1);}
    } catch(err) {if (err.name!=='AbortError') setError(err.message || 'Could not plan this route.');}
    finally {if (!controller.signal.aborted) setBusy(false);}
  }
  function chooseRoute(id) {setSelected(id);setFocus(null);setView('journey');}
  return <div className="route-planner">
    <header className="rp-heading"><div><p className="rp-eyebrow">Travel with road awareness</p><h1>Plan your route</h1><p>Balance travel time with accidents, waterlogging and road damage reported along the way.</p></div><Route size={36} /></header>
    <div className="rp-layout"><form className="rp-panel rp-form" onSubmit={plan}>
      <div className="rp-actions"><button type="button" onClick={useLocation} disabled={locating}><Navigation size={16} />{locating ? 'Locating…' : 'Use my location'}</button>
        <button type="button" onClick={() => {invalidate();setOrigin(destination);setDestination(origin);setStops(previous => [...previous].reverse());}}><ArrowUpDown size={16} /> Reverse trip</button></div>
      <PlaceField id="origin" heading="Start / pickup" point={origin} onChange={point => updatePoint('origin',point)} onPick={() => setPick(pick==='origin' ? null : 'origin')} picking={pick==='origin'} />
      {stops.map((stop,index) => <div className="rp-stop" key={stop.id}><PlaceField id={stop.id} heading={`Stop ${index+1}`} point={stop} onChange={point => updatePoint(stop.id,point)} onPick={() => setPick(pick===stop.id ? null : stop.id)} picking={pick===stop.id} />
        <div className="rp-stop-tools"><label>Time at stop <input type="number" min="0" max="120" value={stop.dwell_minutes} onChange={event => updatePoint(stop.id,{...stop,dwell_minutes:event.target.value})} /> min</label>
          <button type="button" aria-label={`Move stop ${index+1} earlier`} disabled={index===0} onClick={() => moveStop(index,-1)}>↑</button>
          <button type="button" aria-label={`Move stop ${index+1} later`} disabled={index===stops.length-1} onClick={() => moveStop(index,1)}>↓</button>
          <button type="button" onClick={() => {invalidate();setPick(null);setStops(previous => previous.filter(item => item.id!==stop.id));}}>Remove</button></div></div>)}
      <button type="button" className="rp-add-stop" disabled={stops.length>=3} onClick={() => {invalidate();setStops(previous => [...previous,{...blankPoint(),id:`stop-${nextStop.current++}`}]);}}><Plus size={16} /> Add a stop {stops.length>0 && `(${stops.length}/3)`}</button>
      <PlaceField id="destination" heading="Destination / drop-off" point={destination} onChange={point => updatePoint('destination',point)} onPick={() => setPick(pick==='destination' ? null : 'destination')} picking={pick==='destination'} />
      <div className="rp-preferences"><label>Route preference<select value={preference} onChange={event => {invalidate();setPreference(event.target.value);}}>
        <option value="balanced">Balanced · time + road conditions</option><option value="fastest">Fastest driving estimate</option><option value="lower_risk">Lower exposure to reported hazards</option></select></label>
        <label>Maximum extra driving time<select value={extra} onChange={event => {invalidate();setExtra(Number(event.target.value));}}>{[0,5,10,15,20,30,45,60].map(value => <option value={value} key={value}>{value} minutes</option>)}</select></label>
        <label className="rp-checkbox"><input type="checkbox" checked={assigned} onChange={event => {invalidate();setAssigned(event.target.checked);}} /> Include assigned map points in comparison</label>
        {assigned && <p className="rp-note">These positions were assigned for visualization; their recording locations are unverified.</p>}</div>
      <button className="rp-plan" disabled={busy} type="submit"><ShieldCheck size={18} />{busy ? 'Comparing roads and hazards…' : 'Find balanced routes'}</button>
      {busy && <button type="button" onClick={() => {request.current?.abort();setBusy(false);}}>Cancel</button>}
      {error && <p role="alert" className="rp-error">{error}</p>}
      <p className="rp-note">Driving routes · stops stay in your chosen order. Place searches and chosen coordinates are sent to the map providers.</p>
    </form>
    <section className="rp-map-panel"><div className="rp-map-toolbar"><span>{pick ? 'Click the map to set the selected point' : 'Select a route or an incident to inspect it'}</span>
      {pick ? <button onClick={() => setPick(null)}>Cancel pin</button> : <button onClick={() => {setFocus(null);setView('journey');setFitKey(value => value+1);}}>Fit journey</button>}</div>
      <div className="rp-alert-toolbar"><div><strong>{catalog ? `${catalog.total} active incident alerts` : 'Loading incident alerts…'}</strong><small>{alertsError ? 'Alert updates interrupted' : catalog ? `Live updates · every 15s · ${new Date(catalog.updated_at).toLocaleTimeString('en-IN')}` : 'Connecting to alerts'}</small></div>
        <button onClick={refreshAlerts} disabled={alertsBusy}>{alertsBusy?'Updating…':'Refresh alerts'}</button><button disabled={!displayedIssues.length} onClick={() => {setFocus(null);setView('alerts');setFitKey(value=>value+1);}}>Fit alerts</button>
        {current && <label className="rp-checkbox"><input type="checkbox" checked={showOther} onChange={event => setShowOther(event.target.checked)}/>Show all active alerts</label>}
      </div>
      {alertsError && <p role="alert" className="rp-error">{alertsError}. {catalog ? 'Showing the last received alerts.' : 'Incident alerts could not be loaded.'}</p>}
      {!!catalog?.missing_location && <p className="rp-note rp-alert-note">{catalog.missing_location} alerts have no usable location and cannot be placed on the map.</p>}
      {alertsChanged && <p role="status" className="rp-notice">Incident alerts have changed. Select “Find balanced routes” again to update the route comparison.</p>}
      <MapContainer center={[12.9716,77.5946]} zoom={12} className={`rp-map ${pick ? 'rp-picking' : ''}`}>
        <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <MapView route={current} points={markedPoints} focus={focus} fitKey={fitKey} alerts={displayedIssues} view={view} /><PinPicker target={pick} onPick={(id,point) => updatePoint(id,{...points.find(p => p.id===id),...point})} />
        {[...(result?.routes || [])].sort((a,b) => Number(a.id===current?.id)-Number(b.id===current?.id)).map(route => <Polyline key={route.id} positions={route.geometry.coordinates.map(([lon,lat]) => [lat,lon])}
          pathOptions={{color:route.id===current?.id ? '#38bdf8' : '#8795ad',weight:route.id===current?.id ? 7 : 4,opacity:route.id===current?.id ? 1 : .65,dashArray:route.id===current?.id ? undefined : '9 7'}}
          eventHandlers={{click:() => chooseRoute(route.id)}}><Tooltip>{route.roles.join(' / ') || 'Alternative'} · {minutes(route.duration_minutes)}</Tooltip></Polyline>)}
        {displayedIssues.map(issue => <CircleMarker key={issue.id} center={[issue.latitude,issue.longitude]} radius={focus?.id===issue.id ? 15 : issue.on_route ? 12 : 11}
          pathOptions={alertMarkerStyle(issue,focus?.id===issue.id)}>
          <Tooltip className="alert-map-tooltip" direction="top" offset={[0,-12]}>{incidentName(issue)} · {issue.severity || 'medium'} priority · {incidentPlace(issue)}</Tooltip>
          <Popup><strong>{incidentName(issue)}</strong><p>{issue.severity} priority{Number.isFinite(issue.distance_from_route_m) ? ` · ${issue.distance_from_route_m} m from ${issue.on_route?'this':'a compared'} route` : ''}</p><p>{incidentPlace(issue)}</p>
            <p>{issue.is_demo ? 'Assigned map position' : 'Reported location'} · {new Date(issue.created_at).toLocaleString('en-IN')}</p>
            {issue.is_demo && !assigned && <p>Visible on the map; excluded from route scoring until assigned positions are included.</p>}
            {issue.event_id && <Link to={`/map?incident=${issue.event_id}`}>Open incident details</Link>}</Popup></CircleMarker>)}
        {markedPoints.map((point,index) => located(point) && <CircleMarker key={`${index}-${point.latitude}-${point.longitude}`} center={[point.latitude,point.longitude]} radius={11} pathOptions={{color:'#fff',fillColor:index===0 ? '#059669' : index===markedPoints.length-1 ? '#e11d48' : '#2563eb',fillOpacity:1,weight:2}}>
          <Tooltip permanent direction="top">{index===0 ? 'Start' : index===markedPoints.length-1 ? 'Drop-off' : `Stop ${index}`}</Tooltip><Popup>{point.label}</Popup></CircleMarker>)}
      </MapContainer><AlertMapLegend items={displayedIssues} route={!!current}/>
      <div className="rp-alert-pins" aria-label="Incident alerts on the map">{displayedIssues.map(issue => <button key={issue.id} onClick={() => setFocus(issue)}><strong>{incidentName(issue)}</strong><span>{incidentPlace(issue)}</span>{issue.on_route && <small>Along selected route</small>}</button>)}{catalog && !displayedIssues.length && <p>No located alerts in this view.</p>}</div>
      <div className="rp-attribution">Routes: <a href="https://project-osrm.org/" target="_blank" rel="noreferrer">OSRM</a> / <a href="https://routing.openstreetmap.de/about.html" target="_blank" rel="noreferrer">FOSSGIS</a> · Places: <a href="https://photon.komoot.io" target="_blank" rel="noreferrer">Photon</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a> · <a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noreferrer">Fix the map</a></div>
    </section></div>
    {result && <section className="rp-results" aria-label="Route comparison">
      <div className="rp-section-heading"><h2>Choose your route</h2><span>{result.compared_routes} road alternatives compared · updated {new Date(result.generated_at).toLocaleTimeString('en-IN')}</span></div>
      <p className="rp-note">{result.eta_basis}</p>
      <div className="rp-route-cards">{result.routes.map(route => <button key={route.id} className={`rp-route ${route.id===current?.id ? 'rp-selected' : ''}`} aria-pressed={route.id===current?.id} onClick={() => chooseRoute(route.id)}>
        <span className="rp-route-name">{route.recommended && <b>Recommended</b>}{route.roles.join(' · ') || 'Alternative route'}</span>
        <strong><Clock size={20} />{minutes(route.duration_minutes)} <small>approx.</small></strong><span>{route.distance_km} km · {route.stop_minutes} min at stops</span>
        <span>{route.hazard_count} nearby road hazards · {route.high_priority_count} high priority</span><span>{route.extra_minutes ? `+${minutes(route.extra_minutes)} versus fastest` : 'Fastest time estimate'}{route.avoided_hazards>0 ? ` · avoids ${route.avoided_hazards} reported hazards` : ''}</span>
        <span className="rp-road-names">{route.roads || 'Via connected local roads'}</span></button>)}</div>
      {result.warnings.map(note => <p className="rp-notice" key={note}>{note}</p>)}
      {!!result.excluded_assigned_count && <p className="rp-note">{result.excluded_assigned_count} records with assigned map locations excluded. You can include them above for a route comparison.</p>}
      {!!result.excluded_stale_count && <p className="rp-note">{result.excluded_stale_count} old short-lived reports excluded from scoring.</p>}
      {current && <div className="rp-detail-grid"><section className="rp-panel"><h2>Issues along this route ({issueList.length})</h2><p className="rp-note">{result.hazard_basis} No nearby reports does not guarantee a clear road.</p>
        <p className="rp-note">The map shows all active alerts by default. Use its filter to focus on reports included along this route.</p>
        {current.high_priority_count>0 && <p className="rp-notice">This route passes near high-priority reports. Review the marked locations.</p>}
        {!issueList.length && <p>No eligible reports were found close to this route.</p>}
        {issueList.map(issue => <article className="rp-issue" key={issue.id}><div><strong>{title(issue.alert_type)}</strong><span>{issue.severity} priority · around {(issue.along_route_m/1000).toFixed(1)} km into your journey · {issue.distance_from_route_m} m from route</span>
          <span>{incidentPlace(issue)}{issue.is_demo ? ' · assigned position' : ''}</span>
          <small>{new Date(issue.created_at).toLocaleString('en-IN')}{!issue.affects_ranking ? ' · informational; does not change route ranking' : ''}</small></div>
          <button onClick={() => {setFocus(issue);document.getElementById('root')?.querySelector('.rp-map-panel')?.scrollIntoView({behavior:'smooth',block:'center'});}}>Show on route</button>
        </article>)}</section>
        <section className="rp-panel"><h2>Your journey</h2><ol className="rp-legs">{current.legs.map((leg,index) => <li key={index}><strong>{leg.from_label} → {leg.to_label}</strong><span>{leg.distance_km} km · {minutes(leg.duration_minutes)} driving{leg.stop_minutes ? ` + ${leg.stop_minutes} min stop` : ''}</span><small>{leg.roads}</small></li>)}</ol>
          <p className="rp-note">Balanced ranking weighs driving time and hazard severity within your extra-time limit. High-priority exposure is reduced first. It compares available road routes rather than guaranteeing an issue-free journey.</p>
          <button onClick={() => {setFocus(null);setFitKey(value => value+1);document.querySelector('.rp-map-panel')?.scrollIntoView({behavior:'smooth',block:'center'});}}>Show whole journey</button>
        </section></div>}
    </section>}
  </div>;
}
