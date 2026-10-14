import { useEffect, useRef, useState } from 'react';
import { attachedVideoUrl, getAttachedClipCatalog } from './attachedRoadPins';

function durationLabel(value) {
  if (value == null || value === '' || !Number.isFinite(Number(value))) return null;
  const seconds = Math.round(Number(value));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}

export default function MapClipEvidence({ videoId, location, compact = false }) {
  const [clip, setClip] = useState(null);
  const [error, setError] = useState('');
  const video = useRef(null);

  useEffect(() => {
    let active = true;
    getAttachedClipCatalog()
      .then(clips => { if (active) setClip(clips.find(item => item.video_id === videoId) || null); })
      .catch(() => { if (active) setError('Detector details are unavailable. The video can still be played.'); });
    return () => { active = false; };
  }, [videoId]);

  const findings = clip?.findings?.findings || [];
  const moments = clip?.findings?.moments || [];
  const images = clip?.images || [];

  function seekTo(seconds) {
    if (!video.current) return;
    video.current.currentTime = seconds;
    video.current.focus();
  }

  return <article className={`map-clip-evidence${compact ? ' is-compact' : ''}`}>
    <header className="map-clip-heading">
      <div><span className="map-clip-eyebrow">Dashcam video evidence</span>
        <h3>{clip?.title || location || videoId?.replaceAll('-', ' ') || 'Road recording'}</h3>
      </div>
      <span className="map-clip-badge">Clip</span>
    </header>
    {location && <p className="map-clip-map-location">Map reference: {location}</p>}
    <video ref={video} className="map-clip-video" src={attachedVideoUrl(videoId)} controls preload="none"
      poster={images[0] ? attachedVideoUrl(videoId, `/images/${encodeURIComponent(images[0].name)}`) : undefined}
      aria-label={`${clip?.title || 'Road'} dashcam evidence video`}>
      Your browser cannot play this video.
    </video>
    {error && <p className="map-clip-note">{error}</p>}
    {clip && <>
      <div className="map-clip-facts">
        {durationLabel(clip.duration_seconds) && <span>{durationLabel(clip.duration_seconds)} video</span>}
        {clip.frames_processed != null && <span>{clip.frames_processed.toLocaleString()} frames analyzed</span>}
        {clip.camera && clip.camera !== 'unknown' && <span>{clip.camera} camera</span>}
        {clip.tasks?.length > 0 && <span>{clip.tasks.map(task => task.replaceAll('_', ' ')).join(', ')} detection</span>}
        {clip.findings?.candidate_observations > 0 && <span>{clip.findings.candidate_observations.toLocaleString()} model observations</span>}
      </div>
      {findings.length > 0 ? <section className="map-clip-findings" aria-label="Detector findings">
        <strong>Detector readings <small>observations across frames</small></strong>
        <ul>{(compact ? findings.slice(0, 4) : findings).map(item => <li key={item.label}>
          <span>{item.label}</span><b>{item.observations.toLocaleString()}</b>
          {item.peak_confidence != null && <small>peak {Math.round(item.peak_confidence * 100)}%</small>}
        </li>)}</ul>
      </section> : <p className="map-clip-note">No detector output was saved with this clip. Review the footage directly.</p>}
      {moments.length > 0 && <section className="map-clip-moments" aria-label="Notable video moments">
        <strong>Jump to a detection moment</strong>
        <div>{moments.slice(0, compact ? 3 : 6).map((moment, index) => <button key={`${moment.time_seconds}-${index}`} type="button" onClick={() => seekTo(moment.time_seconds)}>
          {durationLabel(moment.time_seconds)} · {moment.labels.join(', ')}
        </button>)}</div>
      </section>}
      {!compact && images.length > 0 && <div className="map-clip-images" aria-label="Saved analysis frames">
        {images.slice(0, 4).map(image => <a key={image.name} href={attachedVideoUrl(videoId, `/images/${encodeURIComponent(image.name)}`)} target="_blank" rel="noreferrer">
          <img src={attachedVideoUrl(videoId, `/images/${encodeURIComponent(image.name)}`)} alt={`Saved analysis frame ${image.name}`} loading="lazy" />
        </a>)}
      </div>}
      <details className="map-clip-provenance"><summary>Source and location details</summary>
        <p><b>Original recording location:</b> {clip.original_location || 'Unknown'}</p>
        <p><b>Recording time:</b> {clip.recorded_at || 'Not available'}</p>
        <p><b>Source clip:</b> {clip.source_name}</p>
        <p>{clip.location_note}</p>
        {clip.source_url && <a href={clip.source_url} target="_blank" rel="noreferrer">Open original recording source</a>}
        {clip.publisher_page && <a href={clip.publisher_page} target="_blank" rel="noreferrer">View publisher source</a>}
      </details>
      <p className="map-clip-limitations">{clip.limitations} Detector observations are candidates, not unique verified incidents.</p>
    </>}
  </article>;
}
