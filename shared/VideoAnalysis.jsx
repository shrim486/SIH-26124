import React, { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Film, LoaderCircle, UploadCloud } from "lucide-react";
import AnalysisResults, { AuthenticatedVideo } from './AnalysisResults';

function createApi(base, getToken) {
  async function request(path, options = {}) {
    const response = await fetch(`${base}${path}`, {...options, cache:'no-store', headers:{...options.headers,Authorization:`Bearer ${getToken() || ''}`}});
    if (response.status===401 || response.status===403) window.dispatchEvent(new Event('government-unauthorized'));
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Video request failed');
    return data;
  }
  return {
    startVideoAnalysis(file, profile, camera, roadBottom, zones) {
      const body = new FormData();
      body.append('file',file); body.append('profile',profile);
      body.append('camera',camera); body.append('road_bottom',roadBottom);
      if (zones) body.append('zones', zones);
      return request('/video-analysis', {method:'POST',body});
    },
    getVideoAnalysis(id) { return request(`/video-analysis/${id}`); },
  };
}

export default function VideoAnalysis({ apiBase, getToken, incidentId }) {
  const userApi = useMemo(() => createApi(apiBase,getToken), [apiBase,getToken]);
  const [job, setJob] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [error, setError] = useState("");
  const [profile, setProfile] = useState('all');
  const [camera, setCamera] = useState('dashcam');
  const [roadBottom, setRoadBottom] = useState(100);
  const [uploading, setUploading] = useState(false);
  const [zones, setZones] = useState('');
  const trafficProfile = ['traffic','congestion','bottleneck'].includes(profile);
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  useEffect(() => {
    if (!job || ["complete", "failed"].includes(job.status)) return undefined;
    let cancelled = false;
    let timer;
    async function poll() {
      try {
        const next = await userApi.getVideoAnalysis(job.id);
        if (!cancelled) { setJob(next); setError(''); }
      } catch (err) {
        if (!cancelled) {
          setError((err.message || "Unable to read video analysis status") + ' — retrying…');
          timer = setTimeout(poll, 5000);
        }
      }
    }
    timer = setTimeout(poll, 2000);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [job, userApi]);

  async function selectVideo(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    setJob(null);
    setPreviewUrl(URL.createObjectURL(file));
    try {
      setUploading(true);
      setJob(await userApi.startVideoAnalysis(file, profile, camera, roadBottom / 100, zones));
    } catch (err) {
      setError(err.message || "Could not start video analysis");
    } finally { setUploading(false); event.target.value = ''; }
  }

  return (
    <section className="video-analysis-panel">
      <AnalysisResults apiBase={apiBase} getToken={getToken} incidentId={incidentId} refreshKey={job?.status === "complete" ? job.id : ""} />
      <h2>Analyze another video</h2>
      <label>Detect{' '}
        <select value={profile} onChange={e => setProfile(e.target.value)}>
          <option value="all">All visual detectors</option>
          <option value="road">Road damage, water, dividers, crossings and signs</option>
          <option value="motorcycle">Helmets, plate/OCR and possible triple riding</option>
          <option value="plates">Number plates and text</option>
          <option value="accident">Possible accident scenes</option>
          <option value="traffic">Traffic queue indicators</option>
          <option value="bottleneck">Congestion and bottleneck zones</option>
          {['pothole','damaged_road','waterlogging','road_divider','zebra_crossing','traffic_sign','number_plate','helmet','triple_riding'].map(task => <option key={task} value={task}>{task === 'helmet' ? 'Helmet + number plate/OCR' : task.replaceAll('_',' ')}</option>)}
        </select>
      </label>
      <label>Camera{' '}
        <select value={camera} onChange={e => setCamera(e.target.value)}>
          <option value="dashcam">Moving car dashcam</option>
          <option value="fixed">Fixed roadside camera</option>
          <option value="handheld">Handheld road footage</option>
        </select>
      </label>
      {trafficProfile && camera !== 'fixed' && <p role="alert">Select a fixed roadside camera to analyze traffic motion.</p>}
      {trafficProfile && <label>Traffic zones (normalized coordinates)<textarea value={zones} onChange={e => setZones(e.target.value)} rows={3} placeholder={'{"upstream":[0,0,0.5,1],"downstream":[0.5,0,1,1]}'} /><span>For bottlenecks, mark upstream and downstream rectangles along the same traffic flow. Values are left, top, right, bottom between 0 and 1. Leave blank for whole-frame congestion.</span></label>}
      <p>Review detections before publishing. Traffic queues require a fixed camera. Longer videos can take several minutes on CPU.</p>
      <details><summary>Model notes</summary><p>Waterlogging, road-divider and traffic-sign models are experimental; verify their predictions against the video.</p></details>
      <label>Bottom of road view (% from top){' '}
        <input type="number" min="1" max="100" value={roadBottom} onChange={e => setRoadBottom(Number(e.target.value))} />
      </label>
      <p>Leave at 100 for the full image. If your dashboard fills the lower part, enter where it starts; detections centered below that line are excluded.</p>
      <div className="video-analysis-picker">
        <Film size={28} />
        <div>
          <strong>Select a raw traffic video</strong>
          <span>Processing starts as soon as the file is selected.</span>
        </div>
        <label className="video-analysis-button">
          <UploadCloud size={17} />
          Choose video
          <input type="file" accept=".mp4,.mov,.avi,.mkv" onChange={selectVideo} disabled={uploading || !(roadBottom > 0 && roadBottom <= 100) || (job && !['complete','failed'].includes(job.status)) || (trafficProfile && camera!=='fixed') || (profile === 'bottleneck' && !zones.trim())} />
        </label>
      </div>

      {error && <div className="gov-error"><span>{error}</span></div>}
      {previewUrl && <video className="video-analysis-preview" src={previewUrl} controls />}

      {job && job.status !== "complete" && job.status !== "failed" && (
        <div className="video-analysis-status">
          <LoaderCircle size={18} className="gov-spin" />
          <span>Analyzing {job.profile || 'selected'} detections...</span>
        </div>
      )}

      {job?.status === "failed" && <div className="gov-error"><span>{job.error}</span></div>}

      {job?.status === "complete" && (
        <div className="video-analysis-result">
          <div className="video-analysis-status complete">
            <CheckCircle2 size={18} />
            <span>Detection complete</span>
          </div>
          <AuthenticatedVideo className="video-analysis-preview" apiBase={apiBase} path={`/video-analysis/${job.id}/video`} getToken={getToken}/>
        </div>
      )}
    </section>
  );
}
