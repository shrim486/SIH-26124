import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CircleMarker, MapContainer, Polyline, Popup, Tooltip, useMap, useMapEvents } from 'react-leaflet';
import { Link } from 'react-router-dom';
import { Ambulance, AlertTriangle, ArrowUpRight, Clock3, Copy, MapPin, Navigation, RefreshCw, Route as RouteIcon, ShieldAlert } from 'lucide-react';
import { governmentApi } from '../api/governmentApi';
import { MapBaseLayer } from '../../../shared/MapLayers';
import MapViewControls from '../../../shared/MapViewControls';
import { incidentName, incidentPlace, evidencePath } from '../../../shared/incidentPresentation';
import 'leaflet/dist/leaflet.css';
import './ambulance-assist.css';

const cityCenter = [12.9716, 77.5946];

function routeMinutes(value) {
  const minutes = Math.round(value || 0);
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} hr ${minutes % 60} min`;
}

function hasCoordinates(item) {
  return Number.isFinite(item?.latitude) && Number.isFinite(item?.longitude);
}

function MapViewport({ routePoints, markers }) {
  const map = useMap();
  useEffect(() => {
    if (routePoints.length > 1) {
      map.fitBounds(routePoints, { padding: [36, 36], maxZoom: 15 });
    } else if (markers.length > 1) {
      map.fitBounds(markers, { padding: [36, 36], maxZoom: 14 });
    } else if (markers.length === 1) {
      map.setView(markers[0], 14);
    } else {
      map.setView(cityCenter, 12);
    }
  }, [map, routePoints, markers]);
  return null;
}

function MapOriginPicker({ enabled, onPick }) {
  useMapEvents({
    click(event) {
      if (enabled) onPick(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

function ResponseMap({ records, selectedId, selectedIncident, origin, route, pickingOrigin, onSelectIncident, onPickOrigin }) {
  const routePoints = useMemo(() => (route?.geometry?.coordinates || []).map(([longitude, latitude]) => [latitude, longitude]), [route]);
  const markers = useMemo(() => {
    const points = records.filter(hasCoordinates).map(item => [item.latitude, item.longitude]);
    if (hasCoordinates(origin)) points.push([origin.latitude, origin.longitude]);
    return points;
  }, [records, origin]);
  const targetPosition = hasCoordinates(selectedIncident) ? [selectedIncident.latitude, selectedIncident.longitude] : null;

  return <div className={`aa-map-frame ${pickingOrigin ? 'is-picking' : ''}`}>
    <MapContainer center={cityCenter} zoom={12} zoomControl={false} className="civic-map aa-map">
      <MapBaseLayer />
      <MapViewControls />
      <MapOriginPicker enabled={pickingOrigin} onPick={onPickOrigin} />
      <MapViewport routePoints={routePoints} markers={markers} />
      {routePoints.length > 1 && <Polyline positions={routePoints} pathOptions={{ color: '#8fbea0', weight: 5, opacity: 0.9 }} />}
      {records.filter(hasCoordinates).map(item => {
        const itemId = String(item.event_id || item.id);
        const selected = itemId === selectedId;
        return <CircleMarker key={itemId} center={[item.latitude, item.longitude]} radius={selected ? 11 : 7}
          pathOptions={{ color: '#f5f3ec', weight: 2, fillColor: selected ? '#d97965' : item.is_demo ? '#a99466' : '#d39364', fillOpacity: 0.95 }}
          eventHandlers={{ click: () => onSelectIncident(itemId) }}>
          <Tooltip>{incidentName(item)}{item.is_demo ? ' · simulated' : ''}</Tooltip>
          <Popup><strong>{incidentName(item)}</strong><p>{incidentPlace(item)}</p>
            {item.event_id && <Link to={evidencePath(item)}>Open incident record <ArrowUpRight size={14} /></Link>}
          </Popup>
        </CircleMarker>;
      })}
      {hasCoordinates(origin) && <CircleMarker center={[origin.latitude, origin.longitude]} radius={9}
        pathOptions={{ color: '#f5f3ec', weight: 2, fillColor: '#5ea7c8', fillOpacity: 1 }}>
        <Tooltip>{origin.unit || 'Ambulance'} · start</Tooltip>
      </CircleMarker>}
      {targetPosition && <CircleMarker center={targetPosition} radius={selectedIncident?.is_demo ? 13 : 10}
        pathOptions={{ color: '#f5f3ec', weight: 2, fillColor: '#c85850', fillOpacity: 1 }}>
        <Tooltip>{incidentName(selectedIncident)} · destination</Tooltip>
      </CircleMarker>}
    </MapContainer>
    {pickingOrigin && <div className="aa-map-pick-note"><MapPin size={15} /> Select the ambulance start point on the map</div>}
  </div>;
}

export default function AmbulanceAssistPage() {
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [loading, setLoading] = useState(false);
  const [unit, setUnit] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const [preference, setPreference] = useState('fastest');
  const [includeDemo, setIncludeDemo] = useState(false);
  const [pickingOrigin, setPickingOrigin] = useState(false);
  const [routing, setRouting] = useState(false);
  const [routeError, setRouteError] = useState('');
  const [routeData, setRouteData] = useState(null);
  const [routeId, setRouteId] = useState('');
  const [copyState, setCopyState] = useState('idle');
  const loadRequest = useRef(null);
  const routeRequest = useRef(null);

  const refresh = useCallback(async () => {
    loadRequest.current?.abort();
    const controller = new AbortController();
    loadRequest.current = controller;
    setLoading(true);
    try {
      const result = await governmentApi.getRecords(false, controller.signal);
      if (!controller.signal.aborted) {
        setData(result);
        setLoadError('');
      }
    } catch (error) {
      if (!controller.signal.aborted) setLoadError(error.message);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadRequest.current = controller;
    governmentApi.getRecords(false, controller.signal)
      .then(result => {
        if (!controller.signal.aborted) {
          setData(result);
          setLoadError('');
        }
      })
      .catch(error => {
        if (!controller.signal.aborted) setLoadError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      controller.abort();
      routeRequest.current?.abort();
    };
  }, []);

  const records = useMemo(() => (data?.records || [])
    .filter(item => item.active && item.issue_status !== 'resolved' && item.issue_status !== 'closed' && hasCoordinates(item))
    .sort((left, right) => {
      const priority = { critical: 0, high: 1, medium: 2, low: 3 };
      return (priority[left.severity] ?? 4) - (priority[right.severity] ?? 4)
        || new Date(right.created_at || 0) - new Date(left.created_at || 0);
    }), [data]);
  const visibleRecords = useMemo(() => records.filter(item => includeDemo || !item.is_demo), [records, includeDemo]);
  const selectionRecords = visibleRecords.length ? visibleRecords : records;
  const activeSelectionId = selectionRecords.some(item => String(item.event_id || item.id) === selectedId)
    ? selectedId
    : String(selectionRecords[0]?.event_id || selectionRecords[0]?.id || '');
  const selectedIncident = records.find(item => String(item.event_id || item.id) === activeSelectionId) || null;
  const selectedRoute = routeData?.routes?.find(item => item.id === routeId)
    || routeData?.routes?.find(item => item.id === routeData.recommended_route_id)
    || null;
  const origin = useMemo(() => {
    if (latitude.trim() === '' || longitude.trim() === '') return null;
    const lat = Number(latitude), lon = Number(longitude);
    return Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180
      ? { latitude: lat, longitude: lon, unit: unit.trim() }
      : null;
  }, [latitude, longitude, unit]);
  const selectedIsHiddenDemo = selectedIncident?.is_demo && !includeDemo;
  const readyToPlan = Boolean(unit.trim() && origin && selectedIncident && !selectedIsHiddenDemo && !routing);

  function chooseIncident(id) {
    setSelectedId(id);
    setRouteData(null);
    setRouteError('');
  }

  function setOriginPoint(lat, lon) {
    setLatitude(lat.toFixed(6));
    setLongitude(lon.toFixed(6));
    setPickingOrigin(false);
    setRouteData(null);
    setRouteError('');
  }

  async function planRoute(event) {
    event.preventDefault();
    if (!readyToPlan) return;
    routeRequest.current?.abort();
    const controller = new AbortController();
    routeRequest.current = controller;
    setRouting(true);
    setRouteData(null);
    setRouteError('');
    try {
      const result = await governmentApi.planEmergencyRoute({
        origin: { latitude: origin.latitude, longitude: origin.longitude, label: unit.trim() },
        destination: {
          latitude: selectedIncident.latitude,
          longitude: selectedIncident.longitude,
          label: incidentName(selectedIncident),
        },
        stops: [],
        preference,
        max_extra_minutes: 15,
        include_assigned: includeDemo,
      }, controller.signal);
      if (!controller.signal.aborted) {
        setRouteData(result);
        setRouteId(result.recommended_route_id || result.routes?.[0]?.id || '');
      }
    } catch (error) {
      if (!controller.signal.aborted) setRouteError(error.message);
    } finally {
      if (!controller.signal.aborted) setRouting(false);
    }
  }

  async function copyBriefing() {
    if (!selectedIncident || !selectedRoute || !origin) return;
    const briefing = [
      `Ambulance response · ${unit.trim()}`,
      `Destination: ${incidentName(selectedIncident)} · ${incidentPlace(selectedIncident)}`,
      `Origin: ${origin.latitude.toFixed(6)}, ${origin.longitude.toFixed(6)}`,
      `Estimated drive: ${routeMinutes(selectedRoute.duration_minutes)} · ${selectedRoute.distance_km} km`,
      selectedIncident.is_demo ? 'DEMO location: not a verified local incident.' : '',
      routeData.eta_basis,
    ].filter(Boolean).join('\n');
    try {
      await navigator.clipboard.writeText(briefing);
      setCopyState('copied');
      setTimeout(() => setCopyState('idle'), 1800);
    } catch {
      setCopyState('failed');
    }
  }

  return <div className="page-shell civic-ui ambulance-assist-page">
    <header className="civic-heading aa-heading">
      <div><span className="civic-kicker">Emergency response</span><h1>Ambulance assist</h1>
        <p>Plan a road route from a supplied unit location to an active incident.</p></div>
      <div className="aa-heading-actions"><span className="aa-readiness"><span /> Route planning only</span>
        <button type="button" onClick={refresh} disabled={loading}><RefreshCw size={16} />{loading ? 'Updating…' : 'Refresh incidents'}</button>
      </div>
    </header>

    {loadError && <p className="civic-error" role="alert">{loadError}</p>}

    <div className="aa-workspace">
      <section className="aa-dispatch-panel" aria-labelledby="aa-dispatch-title">
        <div className="aa-section-title"><span>01</span><div><h2 id="aa-dispatch-title">Response details</h2><p>{records.length} active mapped report{records.length === 1 ? '' : 's'}</p></div></div>
        <form className="aa-form" onSubmit={planRoute}>
          <label>Ambulance call sign<input value={unit} onChange={event => setUnit(event.target.value)} maxLength={40} placeholder="Enter unit ID" required /></label>
          <div className="aa-label-row"><span>Current unit location</span><button type="button" className="aa-map-pick-button" aria-pressed={pickingOrigin} onClick={() => setPickingOrigin(value => !value)}><MapPin size={15} />{pickingOrigin ? 'Cancel map pick' : 'Pick on map'}</button></div>
          <div className="aa-coordinate-grid">
            <label>Latitude<input inputMode="decimal" type="number" min="-90" max="90" step="any" value={latitude} onChange={event => { setLatitude(event.target.value); setRouteData(null); }} placeholder="12.9716" required /></label>
            <label>Longitude<input inputMode="decimal" type="number" min="-180" max="180" step="any" value={longitude} onChange={event => { setLongitude(event.target.value); setRouteData(null); }} placeholder="77.5946" required /></label>
          </div>
          <label>Destination incident<select value={activeSelectionId} onChange={event => chooseIncident(event.target.value)} required>
            {!records.length && <option value="">No active mapped incidents</option>}
            {records.map(item => <option key={item.event_id || item.id} value={String(item.event_id || item.id)}>{incidentName(item)} · {incidentPlace(item)}{item.is_demo ? ' · DEMO' : ''}</option>)}
          </select></label>
          {selectedIncident && <div className="aa-selected-incident">
            <div><span className={`aa-severity aa-severity-${selectedIncident.severity || 'medium'}`} />
              <strong>{incidentName(selectedIncident)}</strong><span>{incidentPlace(selectedIncident)}</span></div>
            {selectedIncident.is_demo && <p><AlertTriangle size={14} /> Simulated location. Do not use for a real dispatch.</p>}
            {selectedIncident.event_id && <Link to={evidencePath(selectedIncident)}>Review incident <ArrowUpRight size={14} /></Link>}
          </div>}
          <label className="aa-demo-toggle"><input type="checkbox" checked={includeDemo} onChange={event => { setIncludeDemo(event.target.checked); setRouteData(null); }} />Include simulated demo reports</label>
          <fieldset className="aa-route-mode"><legend>Route preference</legend>
            <div role="group" aria-label="Route preference">
              <button type="button" aria-pressed={preference === 'fastest'} onClick={() => { setPreference('fastest'); setRouteData(null); }}><Clock3 size={15} />Fastest</button>
              <button type="button" aria-pressed={preference === 'lower_risk'} onClick={() => { setPreference('lower_risk'); setRouteData(null); }}><ShieldAlert size={15} />Lower exposure</button>
            </div>
          </fieldset>
          <button className="aa-plan-button" disabled={!readyToPlan || !records.length}>
            <RouteIcon size={17} />{routing ? 'Finding routes…' : 'Calculate response route'}
          </button>
          {selectedIsHiddenDemo && <p className="aa-form-note" role="status">Enable simulated demo reports to plan to this assigned location.</p>}
          {routeError && <p className="civic-error aa-route-error" role="alert">{routeError}<span>The incident map is still available; no route has been drawn.</span></p>}
        </form>

        <div className="aa-route-results" aria-live="polite">
          <div className="aa-section-title aa-results-title"><span>02</span><div><h2>Route options</h2><p>{routing ? 'Checking road routes…' : selectedRoute ? routeData.eta_basis : 'Calculated when the route service responds.'}</p></div></div>
          {routing && <p className="aa-muted-line">Checking available road-network alternatives…</p>}
          {!routing && !selectedRoute && !routeError && <p className="aa-muted-line">Enter a unit location and choose an incident to compare routes.</p>}
          {selectedRoute && <>
            <div className="aa-route-choice-list">{routeData.routes.map((option, index) => <button type="button" key={option.id} className={option.id === selectedRoute.id ? 'selected' : ''} aria-pressed={option.id === selectedRoute.id} onClick={() => setRouteId(option.id)}>
              <span>{option.recommended ? 'Recommended' : `Option ${index + 1}`}</span><strong>{routeMinutes(option.duration_minutes)}</strong><small>{option.distance_km} km · {option.report_count} nearby reports</small>
            </button>)}</div>
            <div className="aa-route-summary"><span><Navigation size={15} />{selectedRoute.roads || 'Road route calculated'}</span>
              <button type="button" onClick={copyBriefing}><Copy size={15} />{copyState === 'copied' ? 'Copied' : copyState === 'failed' ? 'Copy unavailable' : 'Copy briefing'}</button>
            </div>
            {!!routeData.warnings?.length && <ul className="aa-route-warnings">{routeData.warnings.map(note => <li key={note}>{note}</li>)}</ul>}
            <small className="aa-attribution">{routeData.attribution} · route estimates can change.</small>
          </>}
        </div>
      </section>

      <section className="aa-map-panel" aria-labelledby="aa-map-title">
        <div className="aa-map-heading"><div><span className="civic-kicker">Bengaluru operations</span><h2 id="aa-map-title">Response map</h2></div>
          <div className="aa-map-legend"><span><i className="aa-legend-origin" />Unit</span><span><i className="aa-legend-destination" />Incident</span><span><i className="aa-legend-route" />Route</span></div>
        </div>
        <ResponseMap records={visibleRecords} selectedId={activeSelectionId} selectedIncident={selectedIncident} origin={origin}
          route={selectedRoute} pickingOrigin={pickingOrigin} onSelectIncident={chooseIncident} onPickOrigin={setOriginPoint} />
        <p className="aa-map-caption">{pickingOrigin ? 'Click a point on the map to set the unit’s current location.' : 'Only mapped active reports are shown. Assigned locations are hidden unless explicitly included.'}</p>
        {!!routeData?.warnings?.length && <p className="aa-map-warning"><AlertTriangle size={15} />Review route warnings before sharing this plan.</p>}
      </section>
    </div>
    <footer className="aa-disclaimer"><Ambulance size={17} /><p>This tool plans routes only. It does not dispatch a vehicle, control traffic signals, request right-of-way, or guarantee emergency access. Confirm the unit’s location and conditions with the response team.</p></footer>
  </div>;
}