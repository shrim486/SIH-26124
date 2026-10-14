import { useEffect, useState } from 'react';
import { attachedRoadPins, getAttachedClipCatalog } from './attachedRoadPins';
import MapClipEvidence from './MapClipEvidence';

export default function MapClipLibrary() {
  const [clips, setClips] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    getAttachedClipCatalog()
      .then(items => { if (active) setClips(items); })
      .catch(err => { if (active) setError(err.message || 'Could not load video evidence.'); });
    return () => { active = false; };
  }, []);

  const locations = new Map(attachedRoadPins.map(pin => [pin.video_id, pin.location_name]));
  return <section className="map-clip-library" aria-labelledby="map-clip-library-heading">
    <header className="map-clip-library-heading"><div><span className="civic-kicker">Recorded video evidence</span>
      <h2 id="map-clip-library-heading">Dashcam clips</h2>
      <p>Play the saved road footage and review detector readings. The map labels are browsing references, not verified recording locations.</p>
    </div><strong>{clips ? `${clips.length} clips` : 'Loading clips…'}</strong></header>
    {error && <p role="status" className="map-clip-note">{error}</p>}
    {clips?.length === 0 && <p className="map-clip-note">No saved clips are available from the video service right now.</p>}
    {!!clips?.length && <div className="map-clip-library-grid">{clips.map(clip => <MapClipEvidence key={clip.video_id}
      videoId={clip.video_id} location={locations.get(clip.video_id)} />)}</div>}
  </section>;
}
