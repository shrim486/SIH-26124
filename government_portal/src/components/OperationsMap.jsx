import { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Link } from 'react-router-dom';
import { incidentName, incidentPlace, evidencePath } from '../../../shared/incidentPresentation';
import { alertColour, alertMarkerStyle } from '../../../shared/alertMapStyle';
import AlertMapLegend from '../../../shared/AlertMapLegend';

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

export default function OperationsMap({items, selected, onSelect, fleet = false}) {
  const points = items.filter(hasLocation);
  return <><MapContainer center={[12.9716,77.5946]} zoom={12} className="operations-map">
    <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <View points={points} selected={selected} />
    {points.map(item => <CircleMarker key={item.id} center={[item.latitude,item.longitude]} radius={selected === item.id ? 15 : 11}
      pathOptions={fleet ? {color:'#0f172a',weight:2.5,fillColor:item.online?'#34d399':'#94a3b8',fillOpacity:1} : alertMarkerStyle(item,selected===item.id)}
      eventHandlers={{click:() => onSelect(item.id)}}>
      <Tooltip className="alert-map-tooltip" direction="top" offset={[0,-12]}>{fleet ? item.bus_number : incidentName(item)}</Tooltip>
      <Popup><strong>{fleet ? item.bus_number : incidentName(item)}</strong>
        {!fleet && <p>{incidentPlace(item)}</p>}
        <p>{fleet ? label(item.connection_status) : label(item.status)}</p>
        {item.is_demo && <p>Map location assigned for visualization.</p>}
        <p>{item.latitude.toFixed(6)}, {item.longitude.toFixed(6)}</p>
        {fleet ? <button onClick={() => onSelect(item.id)}>Open vehicle details</button> : <Link to={evidencePath(item)}>{item.evidence_available ? 'Open video & images' : 'Open issue details'}</Link>}</Popup>
    </CircleMarker>)}
  </MapContainer>{!fleet && <AlertMapLegend items={points}/>}</>;
}
