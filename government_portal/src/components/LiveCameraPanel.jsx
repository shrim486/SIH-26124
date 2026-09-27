import { useEffect, useRef, useState } from 'react';
import { Camera, Radio, Pause, Play } from 'lucide-react';
import { governmentApi } from '../api/governmentApi';

export default function LiveCameraPanel({cameras, onRegister}) {
  const [selection,setSelection] = useState(null), [paused,setPaused] = useState(false);
  const [frame,setFrame] = useState(null), [failure,setFailure] = useState(null), [now,setNow] = useState(Date.now);
  const [attempt,setAttempt] = useState(0);
  const objectUrl = useRef(null);
  const current = cameras.find(camera=>camera.id===selection) || cameras[0];
  const id = current?.id;
  useEffect(() => {
    if (!id || paused) return;
    let stopped = false, timer;
    const controller = new AbortController();
    async function poll() {
      try {
        const result = await governmentApi.getCameraFrame(id,controller.signal);
        if (stopped) return;
        const url = URL.createObjectURL(result.blob), previous = objectUrl.current;
        objectUrl.current = url;
        setFrame({id,url,capturedAt:result.capturedAt,processing:result.processing}); setFailure(null);
        if (previous) URL.revokeObjectURL(previous);
      } catch (error) {if (!stopped) setFailure({id,waiting:error.status===404,message:error.message});}
      finally {if (!stopped) {setNow(Date.now());timer=setTimeout(poll,2000);}}
    }
    poll();
    return () => {stopped=true;controller.abort();clearTimeout(timer);};
  },[id,paused,attempt]);
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),1000);return()=>{clearInterval(timer);if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);};},[]);
  const visible = frame?.id===id ? frame : null, error = failure?.id===id ? failure : null;
  const age = visible?.capturedAt ? (now-new Date(visible.capturedAt).getTime())/1000 : Infinity;
  const live = !!visible && age>=-60 && age<=15 && current?.status==='active' && !paused && !error;
  const state = !id ? 'No camera connected' : paused ? 'Preview paused' : current.status!=='active' ? 'Camera '+current.status : error&&!error.waiting ? 'Connection interrupted' : live ? 'Live' : visible ? 'Last received frame' : 'Connect camera';
  return <section className="civic-panel live-camera-panel" aria-label="Live camera preview">
    <div className="civic-panel-heading"><div><span className="civic-kicker">Public transport cameras</span><h2>Live camera preview</h2><p>Frames from the selected vehicle, refreshed every 2 seconds.</p></div><span role="status" className={`camera-live-state ${live?'is-live':''}`}><Radio size={15}/>{state}</span></div>
    <div className="live-camera-layout"><div>
      <div className="civic-toolbar"><label>Camera<select value={id||''} disabled={!cameras.length} onChange={event=>{setSelection(Number(event.target.value));setPaused(false);}}>{!cameras.length&&<option value="">Register a camera first</option>}{cameras.map(camera=><option key={camera.id} value={camera.id}>{camera.camera_code} · {camera.camera_type}</option>)}</select></label>
        <button disabled={!id} onClick={()=>setPaused(value=>!value)}>{paused?<Play size={15}/>:<Pause size={15}/>} {paused?'Resume preview':'Pause preview'}</button></div>
      <div className="live-camera-screen">{visible?<img src={visible.url} alt={`Latest ${visible.processing==='pothole'?'pothole detection':'camera'} frame from ${current.camera_code}`}/>:<div className="civic-empty"><Camera size={34}/><h3>{state}</h3><p>{id?'Start the camera connector on the vehicle’s edge device to receive frames here.':'Register a vehicle and its camera to connect a feed.'}</p><button onClick={onRegister}>Camera setup</button></div>}</div>
      {visible&&<p className="civic-map-caption">Captured {new Date(visible.capturedAt).toLocaleString('en-IN')} · {visible.processing==='pothole'?'Pothole model boxes':'Camera view'} · {live?'Receiving frames':'This image is not a current live view.'}</p>}
      {error&&!error.waiting&&<p role="alert" className="civic-error">{error.message} <button onClick={()=>setAttempt(value=>value+1)}>Retry connection</button></p>}
    </div><div className="camera-connect"><h3>How the camera connects</h3><ol><li><strong>Bus camera → edge device</strong><p>The on-board computer reads the vehicle’s RTSP / HTTP feed or USB camera.</p></li><li><strong>Edge device → secure API</strong><p>The camera connector sends timestamped frames over the vehicle’s internet connection. GPS comes from the vehicle’s GPS device.</p></li><li><strong>API → fleet monitoring</strong><p>This page shows the latest received image. Detected incident recordings and frames are opened from the linked issue.</p></li></ol>
      <details><summary>Connect this camera</summary>{id?<><p>On the edge device, configure the camera source, API address and government credentials in local environment variables, then run:</p><code>python -m edge_ai.live_camera --camera-id {id}</code><p>Add <code>--pothole</code> to show model boxes on the preview. Setup instructions: <code>docs/LIVE_CAMERAS.md</code>.</p><p>Camera ID: {id} · Vehicle ID: {current.bus_id}</p></>:<p>Register a vehicle and camera below to get its connector command.</p>}</details>
      <p className="civic-meta">Live preview retains only the latest image. It is not a continuous recording, and starting a preview does not publish an incident.</p>
    </div></div>
  </section>;
}
