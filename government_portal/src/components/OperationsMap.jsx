import { useEffect, useRef } from 'react';
import { MapContainer, CircleMarker, Popup, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Link } from 'react-router-dom';
import { incidentName, incidentPlace, evidencePath } from '../../../shared/incidentPresentation';
import { alertColour, alertMarkerStyle } from '../../../shared/alertMapStyle';
import AlertMapLegend from '../../../shared/AlertMapLegend';
import { withAttachedRoadPins } from '../../../shared/attachedRoadPins';
import MapClipEvidence from '../../../shared/MapClipEvidence';
import { LiveTrafficLayer, TrafficMapControl, useLiveTraffic } from '../../../shared/LiveTrafficLayer';
import { MapBaseLayer } from '../../../shared/MapLayers';
import MapViewControls from '../../../shared/MapViewControls';

export const hasLocation = item => Number.isFinite(item.latitude) && Number.isFinite(item.longitude);
export const label = value => (value || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
export const issueColor = alertColour;

function View({points, selected}) {
  const map = useMap(), last = useRef('');
  const key = JSON.stringify([selected, points.map(p => [p.id, p.latitude, p.longitude])]);
  useEffect(() => {
    if (last.current === key) return;
    last.current = key;
    const point = points.find(p => p.id === selected);
    if (point) map.setView([point.latitude, point.longitude], 15);
    else if (points.length) map.fitBounds(points.map(p => [p.latitude,p.longitude]), {padding:[30,30], maxZoom:14});
    else map.setView([12.9716,77.5946],12);
  }, [map, key, points, selected]);
  return null;
}

export default function OperationsMap({items, selected, onSelect, fleet = false, includeMapClipPins = true}) {
  const points = items.filter(hasLocation);
  const mapPoints = fleet || !includeMapClipPins ? points : withAttachedRoadPins(points);
  const unverifiedLocationCount = mapPoints.filter(item => item.is_map_attachment).length;
  const traffic = useLiveTraffic();
  return <><div className="operations-map-frame"><MapContainer center={[12.9716,77.5946]} zoom={12} zoomControl={false} className="operations-map">
    <MapBaseLayer/>
    <LiveTrafficLayer enabled={traffic.enabled} reportStatus={traffic.reportStatus}/>
    <MapViewControls/>
    <View points={mapPoints} selected={selected} />
    {mapPoints.map(item => <CircleMarker key={item.id} center={[item.latitude,item.longitude]} radius={selected === item.id ? 15 : 11}
      pathOptions={fleet ? {color:'#0f172a',weight:2.5,fillColor:item.online?'#34d399':'#94a3b8',fillOpacity:1} : alertMarkerStyle(item,selected===item.id)}
      eventHandlers={{click:() => {if(!item.is_map_attachment)onSelect(item.id);}}}>
      <Tooltip className="alert-map-tooltip" direction="top" offset={[0,-12]}>{item.is_map_attachment ? `${incidentName(item)} · location unverified` : fleet ? item.bus_number : incidentName(item)}</Tooltip>
      <Popup className={fleet ? '' : 'civic-alert-popup'} minWidth={fleet ? 180 : 300} maxWidth={fleet ? 240 : 430}>{item.is_map_attachment ? <MapClipEvidence videoId={item.video_id} location={item.location_name} compact/> : <><strong>{fleet ? item.bus_number : incidentName(item)}</strong>
        {!fleet && <p>{incidentPlace(item)}</p>}
        <p>{fleet ? label(item.connection_status) : label(item.status)}</p>
        {item.is_demo && <p>Map location assigned for visualization.</p>}
        <p>{item.latitude.toFixed(6)}, {item.longitude.toFixed(6)}</p>
        {fleet ? <button onClick={() => onSelect(item.id)}>Open vehicle details</button> : <Link to={evidencePath(item)}>{item.evidence_available ? 'Open video & images' : 'Open issue details'}</Link>}</>}</Popup>
    </CircleMarker>)}
  </MapContainer><TrafficMapControl enabled={traffic.enabled} status={traffic.status} onToggle={traffic.toggle}/></div>{!fleet && <AlertMapLegend items={mapPoints} showUnverifiedLocations={unverifiedLocationCount>0}/>}</>;
}
