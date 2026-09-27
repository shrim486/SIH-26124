import { alertColour, archivedAlert } from './alertMapStyle';
import { incidentName } from './incidentPresentation';

export default function AlertMapLegend({items, route = false}) {
  const entries = new Map(items.map(item => {
    const name = archivedAlert(item) ? 'Archived issue' : incidentName(item);
    return [name, {name, colour:alertColour(item)}];
  }));
  if (!entries.size && !route) return null;
  return <div className="civic-map-legend" aria-label="Map colour key">
    {route && <span><i className="civic-legend-route" aria-hidden="true"/>Selected route</span>}
    {[...entries.values()].map(entry => <span key={entry.name}><i style={{background:entry.colour}} aria-hidden="true"/>{entry.name}</span>)}
  </div>;
}
