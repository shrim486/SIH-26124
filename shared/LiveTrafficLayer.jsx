import { useEffect, useState } from 'react';
import { TileLayer } from 'react-leaflet';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');
const TOMTOM_ATTRIBUTION = 'Traffic data &copy; <a href="https://www.tomtom.com/traffic-index/" target="_blank" rel="noreferrer">TomTom</a>';

export function useLiveTraffic(initiallyEnabled = true) {
  const [enabled, setEnabled] = useState(initiallyEnabled);
  const [status, setStatus] = useState(initiallyEnabled ? 'loading' : 'off');
  const toggle = () => {
    const next = !enabled;
    setEnabled(next);
    setStatus(next ? 'loading' : 'off');
  };
  return {
    enabled,
    status,
    toggle,
    reportStatus: setStatus,
  };
}

export function LiveTrafficLayer({ enabled, reportStatus }) {
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (!enabled) return undefined;
    reportStatus('loading');
    const timer = window.setInterval(() => {
      reportStatus('loading');
      setRevision(value => value + 1);
    }, 60_000);
    return () => window.clearInterval(timer);
  }, [enabled, reportStatus]);

  if (!enabled) return null;

  const reportLoaded = () => reportStatus('live');
  const reportFailed = () => reportStatus('error');
  const eventHandlers = { tileload: reportLoaded, tileerror: reportFailed };
  return <>
    <TileLayer key={`flow-${revision}`} url={`${API_BASE}/traffic/tiles/flow/{z}/{x}/{y}.png`}
      opacity={0.78} zIndex={220} attribution={TOMTOM_ATTRIBUTION} eventHandlers={eventHandlers}/>
    <TileLayer key={`incidents-${revision}`} url={`${API_BASE}/traffic/tiles/incidents/{z}/{x}/{y}.png`}
      opacity={0.88} zIndex={221} attribution={TOMTOM_ATTRIBUTION} eventHandlers={eventHandlers}/>
  </>;
}

export function TrafficMapControl({ enabled, status, onToggle, inline = false }) {
  const [legendOpen, setLegendOpen] = useState(false);
  const statusText = status === 'error'
    ? 'Traffic feed unavailable. Check TomTom Traffic API access.'
    : status === 'loading'
      ? 'Loading traffic tiles...'
      : 'Traffic data refreshes about every minute.';
  const statusLabel = !enabled ? 'Off' : status === 'error' ? 'Unavailable' : status === 'loading' ? 'Updating' : 'Live';

  return <div className={`traffic-map-control${inline ? ' traffic-map-control-inline' : ''}`} data-status={enabled ? status : 'off'}>
    <div className="traffic-map-actions">
      <button type="button" className={`traffic-map-toggle${enabled ? ' is-active' : ''}`} aria-pressed={enabled} onClick={() => {
        setLegendOpen(false);
        onToggle();
      }}>
        <span className="traffic-map-toggle-dot" aria-hidden="true"/>
        <span className="traffic-map-toggle-label">Traffic</span>
        <span className="traffic-map-toggle-status">{statusLabel}</span>
      </button>
      {enabled && <button type="button" className="traffic-map-legend-toggle" aria-label={legendOpen ? 'Hide traffic legend' : 'Show traffic legend'} aria-expanded={legendOpen} title="Traffic legend" onClick={() => setLegendOpen(open => !open)}>
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 2.8a7.2 7.2 0 1 0 0 14.4 7.2 7.2 0 0 0 0-14.4Z"/><path d="M8.2 7.2a1.9 1.9 0 1 1 3.1 1.5c-.8.6-1.3 1-1.3 2.1m0 2.4h.01"/></svg>
      </button>}
    </div>
    {enabled && legendOpen && <div className="traffic-map-key" aria-label="Live traffic legend">
      <strong>Traffic conditions</strong>
      <span><i className="traffic-key-free"/>Moving freely</span>
      <span><i className="traffic-key-slow"/>Slowing</span>
      <span><i className="traffic-key-heavy"/>Heavy traffic</span>
      <span><i className="traffic-key-jam"/>Jam or closure</span>
      <small>{statusText}</small>
    </div>}
  </div>;
}
