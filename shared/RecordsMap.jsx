import { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip, useMap } from 'react-leaflet';
import { incidentName, incidentPlace, incidentDate, evidencePath, hasCoordinates } from './incidentPresentation';
import { alertMarkerStyle } from './alertMapStyle';
import AlertMapLegend from './AlertMapLegend';
import 'leaflet/dist/leaflet.css';

export { issueColour } from './alertMapStyle';
function View({items,selected,fitKey}) {
  const map = useMap(), previous = useRef('');
  const key = JSON.stringify([selected,fitKey,items.map(item => [item.id,item.latitude,item.longitude])]);
  useEffect(() => {
    if (previous.current===key) return;
    previous.current=key;
    const item=items.find(row=>row.id===selected);
    if (item) map.setView([item.latitude,item.longitude],15);
    else if(items.length) map.fitBounds(items.map(row=>[row.latitude,row.longitude]),{padding:[35,35],maxZoom:14});
    else map.setView([12.9716,77.5946],12);
  },[map,items,selected,key]);
  return null;
}
export default function RecordsMap({items,selected,onSelect=()=>{},government=false,fitKey=0}) {
  const points=items.filter(hasCoordinates);
  const prefix=government ? '' : (import.meta.env.VITE_GOVERNMENT_PORTAL_URL || 'http://127.0.0.1:5174');
  return <><MapContainer center={[12.9716,77.5946]} zoom={12} className="civic-map">
    <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <View items={points} selected={selected} fitKey={fitKey} />
    {points.map(item=><CircleMarker key={item.id} center={[item.latitude,item.longitude]} radius={selected===item.id ? 15 : 11}
      pathOptions={alertMarkerStyle(item,selected===item.id)} eventHandlers={{click:()=>onSelect(item.id)}}>
      <Tooltip className="alert-map-tooltip" direction="top" offset={[0,-12]}>{incidentName(item)} · {item.severity || 'medium'} priority</Tooltip>
      <Popup><strong>{incidentName(item)}</strong><p>{incidentPlace(item)}</p><p>{incidentDate(item)}</p>
        {item.is_demo && <p>Assigned map location; recording location unverified.</p>}
        <a className="civic-popup-link" href={`${prefix}${evidencePath(item)}`}>{item.evidence_available ? 'Open video & images' : 'Open issue details'}{!government && ' · government sign-in'}</a>
      </Popup>
    </CircleMarker>)}
  </MapContainer><AlertMapLegend items={points}/></>;
}
