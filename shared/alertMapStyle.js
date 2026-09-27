// Use the same saturated incident colours on portal maps and route planning.
const colours = {
  accident: '#e11d48', pothole: '#f97316', waterlogging: '#0284c7',
  road_damage: '#eab308', damaged_road: '#eab308',
  helmet_violation: '#7c3aed', helmet: '#7c3aed', without_helmet: '#7c3aed',
  traffic_violation: '#db2777', triple_riding: '#db2777', rash_driving: '#db2777',
  congestion: '#0d9488', bottleneck: '#0d9488',
};
export const issueColour = kind => colours[kind] || '#0d9488';
export const archivedAlert = item => item.active === false || ['resolved','closed'].includes(item.status || item.issue_status);
export const alertColour = item => archivedAlert(item) ? '#64748b' : issueColour(item.alert_type || item.event_type);
export const alertMarkerStyle = (item, selected = false) => ({
  color: '#0f172a', weight: selected ? 4 : item.on_route ? 3.5 : 2.5,
  opacity: 1, fillColor: alertColour(item), fillOpacity: 1,
  className: 'alert-map-marker',
});
