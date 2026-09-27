import React, { useCallback, useEffect, useRef, useState } from 'react';
import './analysis-results.css';
import { sampleText } from './sampleText';
import { incidentName, incidentPlace, incidentReference } from './incidentPresentation';

function PublishDetection({ item, apiBase, getToken, onPublished }) {
  const [busy,setBusy] = useState(false);
  const [message,setMessage] = useState('');
  const candidates = item.detection_segments || [];
  const published = item.published_incidents || [];
  const available = candidates.filter(segment => !published.some(link => link.segment_id === segment.id));
  async function submit(event) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    setBusy(true); setMessage('');
    try {
      const payload = {segment_id:form.get('segment_id'),latitude:Number(form.get('latitude')),
        longitude:Number(form.get('longitude')),occurred_at:new Date(form.get('occurred_at')).toISOString(),
        location_name:form.get('location_name'),description:form.get('description'),demo:form.get('demo')==='on'};
      const response = await fetch(`${apiBase}/government/analysis-results/${item.id}/incidents`, {
        method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${getToken()}`},body:JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check the location, time and selected detection.');
      setMessage(`${incidentName(data.incident)} is now on both portal maps. Reference: ${incidentReference(data.incident)}.`);
      onPublished();
    } catch (err) { setMessage(err.message); }
    finally { setBusy(false); }
  }
  return <section className="ai-publish-accident">
    <h3>Detection map reports</h3>
    {published.map(link => <p key={link.id}>{incidentReference(link)}{' '}
      <a href={`?incident=${link.id}`}>View linked video and detected frames</a>{' · '}
      <a href={`${import.meta.env.VITE_USER_PORTAL_URL || 'http://127.0.0.1:5173'}/map?incident=${link.id}`} target="_blank" rel="noreferrer">User map</a>
    </p>)}
    {!candidates.length && <p>No detection candidates meeting the detector threshold were found in this run.</p>}
    {!!available.length && <form onSubmit={submit} className="ai-incident-form">
      <p>Review the video first. Use the incident location and time, not your current location. Each detected segment creates one linked report.</p>
      <label>Detected segment<select name="segment_id" required>{available.map(segment =>
        <option key={segment.id} value={segment.id}>{segment.event_type.replaceAll("_", " ")}: {segment.start_seconds.toFixed(2)}–{segment.end_seconds.toFixed(2)}s · {segment.detected_frames} detected frames</option>)}</select></label>
      <label>Location name<input name="location_name" maxLength={160} required placeholder="Road or junction" /></label>
      <label>Latitude<input name="latitude" type="number" step="any" min="-90" max="90" required /></label>
      <label>Longitude<input name="longitude" type="number" step="any" min="-180" max="180" required /></label>
      <label>Detection date and time (local)<input name="occurred_at" type="datetime-local" required /></label>
      <label>Description<textarea name="description" maxLength={1000} rows={2} /></label>
      <label><input name="demo" type="checkbox" /> Location and time assigned for visualization</label>
      <button disabled={busy}>{busy ? 'Adding report…' : 'Add detection to map'}</button>
    </form>}
    {message && <p role="status">{message}</p>}
  </section>;
}

export function IncidentEvidence({ apiBase, getToken, incidentId, compact = false }) {
  const [item,setItem] = useState(null);
  const [error,setError] = useState('');
  const [attempt,setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setItem(null); setError('');
    fetch(`${apiBase}/government/analysis-results/incidents/${encodeURIComponent(incidentId)}`, {
      headers:{Authorization:`Bearer ${getToken()}`},signal:controller.signal,
    }).then(async response => {
      if (!response.ok) throw new Error('Could not load this incident’s evidence. Check your sign-in and incident ID.');
      const data = await response.json();
      const requested = compact ? null : new URLSearchParams(window.location.search).get('time');
      if (requested !== null && Number.isFinite(Number(requested)) && Number(requested) >= 0 && Number(requested) < data.duration_seconds) data.start_seconds = Number(requested);
      if (!controller.signal.aborted) setItem(data);
    }).catch(err => { if (err.name !== 'AbortError') setError(err.message); });
    return () => controller.abort();
  }, [apiBase,getToken,incidentId,compact,attempt]);
  return <section className={`ai-results ${compact ? 'ai-results-inline' : ''}`} aria-label={`Video and detected images for issue ${incidentId}`}>
    {error && <div><p role="alert">{error}</p><button onClick={() => setAttempt(value => value + 1)}>Retry evidence</button></div>}
    {!item && !error && <p>Loading incident evidence…</p>}
    {item && <ResultVideo key={`${incidentId}-${attempt}`} item={item} apiBase={apiBase} getToken={getToken} compact={compact} />}
  </section>;
}

export default function AnalysisResults(props) {
  return props.incidentId ? <IncidentEvidence key={props.incidentId} {...props} /> : <SavedAnalysisResults {...props} />;
}

function useMedia(apiBase, path, getToken) {
  const [state, setState] = useState({ path: null, url: '', error: '' });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!path) return undefined;
    const controller = new AbortController();
    let objectUrl;
    fetch(`${apiBase}${path}`, {
      headers: { Authorization: `Bearer ${getToken() || ''}` }, signal: controller.signal,
    }).then(async response => {
      if (response.status===401 || response.status===403) window.dispatchEvent(new Event('government-unauthorized'));
      if (!response.ok) throw new Error(`Unable to load media (${response.status}). Sign in again if your session expired.`);
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(blob);
      setState({ path, url: objectUrl, error: '' });
    }).catch(error => {
      if (error.name !== 'AbortError') setState({ path, url: '', error: error.message });
    });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [apiBase, path, getToken, attempt]);
  return { ...(state.path === path ? state : {url:'', error:''}), retry: () => {
    setState({path, url:'', error:''}); setAttempt(value => value + 1);
  } };
}

export function AuthenticatedVideo({apiBase,path,getToken,className}) {
  const {url,error,retry}=useMedia(apiBase,path,getToken);
  if(error) return <div role="alert">{error}<button onClick={retry}>Retry video</button></div>;
  return url ? <video className={className} src={url} controls preload="metadata"/> : <p role="status">Loading protected video…</p>;
}

function EvidenceImage({ apiBase, path, getToken, label, onClick }) {
  const { url, error, retry } = useMedia(apiBase, path, getToken);
  return <figure className="ai-result-image">
    {error ? <div><p role="alert">{error}</p><button onClick={retry}>Retry image</button></div> : url ?
      <a href={url} target="_blank" rel="noreferrer" onClick={onClick}><img src={url} alt={label} loading="lazy" /></a> :
      <p>Loading image…</p>}
    <figcaption>{label}{url && <a className="ai-frame-open" href={url} target="_blank" rel="noreferrer">Open full image</a>}</figcaption>
  </figure>;
}

export function ResultVideo({ item, apiBase, getToken, compact = false }) {
  const { url, error, retry } = useMedia(apiBase, item.video_url, getToken);
  const video = useRef(null);
  const requestedTime = useRef(null);
  const frames = item.frames.length ? item.frames : !item.incident && item.preview_url ? [{image_url:item.preview_url,time_seconds:0}] : [];
  const helmetCounts = (item.evidence_segment ? [item.evidence_segment] : item.detection_segments || [])
    .filter(segment => segment.event_type === 'helmet').reduce((counts, segment) => {
      for (const [label, count] of Object.entries(segment.label_frame_counts || {})) counts[label] = (counts[label] || 0) + count;
      return counts;
    }, {});
  return <article>
    <h3>{compact ? 'Annotated video' : item.incident ? incidentName(item.incident) : sampleText(item.name)}</h3>
    {!compact && item.incident && <div className="ai-incident-banner">
      <strong>{incidentPlace(item.incident)}</strong><span className="civic-meta">{incidentReference(item.incident)}</span>
      <p>{item.incident.demo ? 'Map location and time assigned for visualization; recording location unverified.' : 'Reported detection with linked video evidence.'}</p>
      {item.incident.description && <details><summary>Recording details</summary><p>{sampleText(item.incident.description)}</p></details>}<p>{item.incident.event_type?.replaceAll('_', ' ')} · {new Date(item.incident.timestamp).toLocaleString('en-IN')}</p>
      <a href={`${import.meta.env.VITE_USER_PORTAL_URL || 'http://127.0.0.1:5173'}/map?incident=${item.incident.id}`} target="_blank" rel="noreferrer">View this incident on the user map</a>
    </div>}
    {!compact && <><p>{item.frames_processed} frames{item.duration_seconds != null ? ` · ${item.duration_seconds.toFixed(2)} seconds` : ''}
      {item.boxes_across_frames != null ? ` · ${item.boxes_across_frames} box observations across frames` : ''}</p>
    <p>Camera: {item.camera || "unknown"}. {item.source_info && <a href={item.source_info.url} target="_blank" rel="noreferrer">Original video source</a>}</p>
    <p className="ai-result-tags">Models: {item.tasks.map(task => task.replaceAll('_', ' ')).join(', ')}</p></>}
    {item.evidence_segment && <p className="ai-segment-time">Detected segment · {item.evidence_segment.start_seconds.toFixed(2)}–{item.evidence_segment.end_seconds.toFixed(2)} seconds</p>}
    {item.tasks.includes('helmet') && <p>Box colours: green = with helmet; red = without helmet; blue = number plate.</p>}
    {!!Object.keys(helmetCounts).length && <p>{Object.entries(helmetCounts).map(([label, count]) => `${label.replaceAll('_', ' ')}: ${count} frames`).join(' · ')}. Frame counts are repeated observations, not unique riders.</p>}
    {error && <div><p role="alert">{error}</p><button onClick={retry}>Retry video</button></div>}
    {url ? <><video ref={video} src={url} controls preload="metadata" onLoadedMetadata={e => { e.currentTarget.currentTime = requestedTime.current ?? item.start_seconds ?? 0; }} aria-label={`Annotated video: ${sampleText(item.name)}`} />
      <label>Playback speed <select defaultValue="1" onChange={e => { if (video.current) video.current.playbackRate = Number(e.target.value); }}><option value="0.5">0.5×</option><option value="0.75">0.75×</option><option value="1">1× (original speed)</option></select></label>
      <a className="ai-result-download" href={url} download={`${sampleText(item.name).replaceAll(' ', '_')}.mp4`}>Download annotated MP4</a></> : !error && <p role="status">Loading video…</p>}
    <h4>Detected images ({frames.length})</h4>
    {!!frames.length && <p className="ai-frame-help">Select an image to jump to that moment in the video, or open the full image to inspect its detection boxes.</p>}
    {!frames.length && <p>No detected images are linked to this issue.</p>}
    <div className="ai-result-grid">
      {frames.map(frame =>
        <EvidenceImage key={frame.image_url} apiBase={apiBase} path={frame.image_url} getToken={getToken}
          label={`${item.incident ? 'Detected frame' : 'Video frame'} · ${frame.time_seconds.toFixed(2)}s${frame.labels?.length ? ' · ' + frame.labels.map(label => label.replaceAll('_', ' ')).join(', ') : ''}`} onClick={event => {
            if (video.current && url) {
              event.preventDefault(); requestedTime.current = frame.time_seconds;
              if (video.current.readyState >= 1) video.current.currentTime = frame.time_seconds;
              video.current.scrollIntoView({block:'center',behavior:'smooth'});
            }
          }} />)}
    </div>
  </article>;
}

function SavedAnalysisResults({ apiBase, getToken, refreshKey = '' }) {
  const [data, setData] = useState({videos:[],models:[]});
  const [typeFilter, setTypeFilter] = useState('all');
  const [selected, setSelected] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async (signal) => {
    setLoading(true); setError('');
    try {
      const response = await fetch(`${apiBase}/government/analysis-results`, {
        headers:{ Authorization:`Bearer ${getToken() || ''}` }, signal,
      });
      if (!response.ok) throw new Error(`Saved results unavailable (${response.status}). Check your government sign-in and API connection.`);
      setData(await response.json());
    } catch (err) { if (err.name !== 'AbortError') setError(err.message); }
    finally { if (!signal?.aborted) setLoading(false); }
  }, [apiBase,getToken]);
  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal);
    return () => controller.abort();
  }, [refresh,refreshKey]);
  const videos = data.videos.filter(video => typeFilter === 'all' || video.tasks.includes(typeFilter));
  const item = videos.find(video => video.id === selected) || videos[0];
  return <section className="ai-results" aria-label="Saved AI detection results">
    <div className="ai-result-heading"><h2>Saved detection outputs</h2><button onClick={() => refresh()} disabled={loading}>Refresh results</button></div>
    <p>Review annotated videos and detected frames. Predictions are candidates for review. Select a detected segment below and provide its location and time to add the same incident to the user map and government detection list.</p>
    {error && <p role="alert">{error}</p>}
    {loading && <p>Loading saved outputs…</p>}
    {!loading && !error && !data.videos.length && <p>No completed analysis videos yet. Upload a video below to create one.</p>}
    <div className="ai-model-grid" aria-label="Model coverage">{(data.models || []).map(model => <button key={model.id} className={typeFilter === model.id ? 'selected' : ''} aria-pressed={typeFilter === model.id} onClick={() => { setTypeFilter(model.id); setSelected(''); }}>
      <strong>{model.name}</strong><span>{model.videos_analyzed} videos analyzed · {model.positive_segments} candidate segments</span><small>{model.method}</small>
      {!model.positive_segments && <span>No candidate detections in saved videos</span>}
    </button>)}</div>
    <label>Model filter <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setSelected(''); }}><option value="all">All models</option>{(data.models || []).map(model => <option key={model.id} value={model.id}>{model.name}</option>)}</select></label>
    {!loading && !videos.length && <p>No completed video for this model yet. Select it in the upload form below.</p>}
    {!!videos.length && <label>Saved run <select value={item.id} onChange={e => setSelected(e.target.value)}>
      {videos.map(video => <option value={video.id} key={video.id}>{sampleText(video.name)}{video.recommended ? ' — featured' : ''}</option>)}
    </select></label>}
    {item && <><ResultVideo key={item.id} item={item} apiBase={apiBase} getToken={getToken} />
      <PublishDetection key={`publish-${item.id}`} item={item} apiBase={apiBase} getToken={getToken} onPublished={() => refresh()} /></>}

  </section>;
}
