import { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, Tooltip, useMap } from 'react-leaflet';
import { hasCoordinates } from '../../../shared/incidentPresentation';
import 'leaflet/dist/leaflet.css';

function trailParts(points){
  const parts=[];let part=[],last=null;
  for(const point of points){
    if(point.source!=='device'||!hasCoordinates(point)){if(part.length>1)parts.push(part);part=[];last=null;continue;}
    if(last&&new Date(point.recorded_at)-new Date(last.recorded_at)>300000){if(part.length>1)parts.push(part);part=[];}
    part.push([point.latitude,point.longitude]);last=point;
  }
  if(part.length>1)parts.push(part);
  return parts;
}
function View({buses,selected,history,follow,fitKey}){
  const map=useMap(),previous=useRef('');
  const key=JSON.stringify([selected,fitKey,follow,history.length>0,buses.map(row=>follow?[row.id,row.latitude,row.longitude]:row.id)]);
  useEffect(()=>{
    if(key===previous.current)return;previous.current=key;
    const bus=buses.find(row=>row.id===selected);
    if(bus&&follow)map.setView([bus.latitude,bus.longitude],15);
    else if(bus){const points=history.filter(hasCoordinates).map(row=>[row.latitude,row.longitude]);map.fitBounds([[bus.latitude,bus.longitude],...points],{padding:[30,30],maxZoom:15});}
    else if(buses.length)map.fitBounds(buses.map(row=>[row.latitude,row.longitude]),{padding:[30,30],maxZoom:14});
  },[map,key,buses,selected,history,follow]);
  return null;
}
export default function FleetMap({buses,selected,onSelect,history=[],follow=false,fitKey=0}){
  const mapped=buses.filter(hasCoordinates),parts=trailParts(history);
  return <MapContainer center={[12.9716,77.5946]} zoom={12} className="civic-map fleet-map">
    <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>
    <View buses={mapped} selected={selected} history={history} follow={follow} fitKey={fitKey}/>
    {parts.map((points,index)=><Polyline key={index} positions={points} pathOptions={{color:'#66b6cf',weight:4,opacity:.7}}/>)}
    {mapped.map(bus=><CircleMarker key={bus.id} center={[bus.latitude,bus.longitude]} radius={bus.id===selected?12:8} pathOptions={{color:'#fff',weight:2,fillOpacity:1,fillColor:bus.online?'#52b89a':'#8e9fb4'}} eventHandlers={{click:()=>onSelect(bus.id,false)}}>
      <Tooltip>{bus.bus_number} · {bus.route_number||'Route unassigned'}</Tooltip><Popup><strong>{bus.bus_number}</strong><p>{bus.connection_status.replaceAll('_',' ')}</p><p>{new Date(bus.last_seen).toLocaleString('en-IN')}</p><button onClick={()=>onSelect(bus.id)}>Open vehicle details</button></Popup>
    </CircleMarker>)}
  </MapContainer>;
}
