import { sampleText } from './sampleText';

const names = {accident:'Accident',pothole:'Pothole',waterlogging:'Waterlogging',road_damage:'Road damage',damaged_road:'Road damage',helmet:'No helmet',helmet_violation:'No helmet',traffic_violation:'Traffic violation',triple_riding:'Possible triple riding',rash_driving:'Possible rash driving',congestion:'Congestion',bottleneck:'Bottleneck'};
export const incidentName = item => names[item.alert_type || item.event_type] || 'Road incident';
export const hasCoordinates = item => Number.isFinite(item.latitude) && Number.isFinite(item.longitude) && Math.abs(item.latitude)<=90 && Math.abs(item.longitude)<=180;
const corridorLabel = /(?:Map point \d+:\s*)?Yelahanka\s*[-–—]\s*Koramangala\s+corridor(?:,\s*Bengaluru)?/gi;
export const incidentPlace = item => {
  if (hasCoordinates(item)) return `${item.latitude.toFixed(6)}, ${item.longitude.toFixed(6)}`;
  return sampleText(item.location_name || '').replace(corridorLabel,'').replace(/^Map point \d+:\s*/i,'').trim() || 'Location pending';
};
export const incidentMessage = item => sampleText(item.message || 'Road issue reported.').replace(corridorLabel,incidentPlace(item));
export const incidentReference = item => item.reference || `INC-${String(item.event_id || item.id).padStart(5,'0')}`;
export const incidentDate = item => (item.created_at || item.timestamp) ? new Date(item.created_at || item.timestamp).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}) : 'Time unavailable';
export const evidencePath = item => {
  const id = 'alert_type' in item ? item.event_id : item.id;
  return id ? item.evidence_available ? `/ai-results?incident=${id}` : `/detections?issue=${id}` : `/alerts?alert=${item.id}`;
};
export const alertToIssue = item => ({...item,id:item.event_id || `alert-${item.id}`,alert_id:item.id,event_type:item.alert_type,status:item.issue_status,timestamp:item.created_at,event_metadata:JSON.stringify({is_demo:item.is_demo,location_name:item.location_name,evidence_available:item.evidence_available})});
