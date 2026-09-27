import React from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";

import L from "leaflet";

import "leaflet/dist/leaflet.css";
import { sampleText } from '../../../shared/sampleText';
import { incidentPlace } from '../../../shared/incidentPresentation';


/* ============================================================
   FIX LEAFLET DEFAULT ICONS
   ============================================================ */

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",

  iconUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",

  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});


/* ============================================================
   MAP CENTER
   ============================================================ */

const DEFAULT_CENTER = [
  12.9716,
  77.5946,
];


/* ============================================================
   MAP VIEW HELPER
   ============================================================ */

function MapViewController({ events, focusId }) {
  const map = useMap();
  const lastView = React.useRef('');

  React.useEffect(() => {
    if (!events || events.length === 0) {
      map.setView(DEFAULT_CENTER, 12);
      return;
    }

    const validEvents = events.filter(
      (event) =>
        event.latitude != null && event.longitude != null && Number.isFinite(Number(event.latitude)) &&
        Number.isFinite(Number(event.longitude))
    );

    if (validEvents.length === 0) {
      map.setView(DEFAULT_CENTER, 12);
      return;
    }
    const focused = validEvents.find(event => String(event.id) === String(focusId));
    const viewKey = JSON.stringify([focusId, validEvents.map(event => [event.id, event.latitude, event.longitude])]);
    if (lastView.current === viewKey) return;
    lastView.current = viewKey;
    if (focused) { map.setView([Number(focused.latitude),Number(focused.longitude)],15); return; }

    const bounds = L.latLngBounds(
      validEvents.map((event) => [
        Number(event.latitude),
        Number(event.longitude),
      ])
    );

    map.fitBounds(bounds, {
      padding: [40, 40],
      maxZoom: 15,
    });

  }, [events, map, focusId]);

  return null;
}


/* ============================================================
   EVENT COLOR
   ============================================================ */

function getEventColor(type) {

  const value = String(type || "").toLowerCase();
  const colors = {pothole:'#f97316',damaged_road:'#fb923c',road_damage:'#fb923c',waterlogging:'#06b6d4',road_divider:'#64748b',zebra_crossing:'#22c55e',traffic_sign:'#eab308',accident:'#ef4444',number_plate:'#3b82f6',helmet:'#14b8a6',triple_riding:'#ec4899',congestion:'#a855f7',bottleneck:'#8b5cf6'};
  if (colors[value]) return colors[value];

  if (value.includes("accident")) {
    return "#ff4d6d";
  }

  if (value.includes("water")) {
    return "#00d2e6";
  }

  if (value.includes("traffic")) {
    return "#a855f7";
  }

  if (value.includes("helmet")) {
    return "#f59e0b";
  }

  return "#ffad33";
}


/* ============================================================
   INCIDENT MAP
   ============================================================ */

export default function IncidentMap({
  events = [],
  fullScreen = false,
  focusId = null,
}) {

  const validEvents = events.filter(
    (event) =>
      event.latitude != null && event.longitude != null && Number.isFinite(Number(event.latitude)) &&
      Number.isFinite(Number(event.longitude))
  );


  return (
    <div
      className={
        fullScreen
          ? "incident-map full-map"
          : "incident-map"
      }
    >

      <MapContainer
        center={DEFAULT_CENTER}
        zoom={12}
        scrollWheelZoom={true}
        style={{
          width: "100%",
          height: "100%",
          minHeight: fullScreen ? "calc(100vh - 160px)" : "420px",
        }}
      >

        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />


        <MapViewController events={validEvents} focusId={focusId} />


        {validEvents.map((event) => {
          let metadata = event.event_metadata || {};
          if (typeof metadata === 'string') { try { metadata = JSON.parse(metadata); } catch { metadata = {}; } }
          if (!metadata || typeof metadata !== 'object') metadata = {};
          const demo = event.status === 'demo' || metadata.is_demo;
          const eventLabel = String(event.event_type || 'Urban incident').replaceAll('_', ' ');

          const latitude = Number(event.latitude);
          const longitude = Number(event.longitude);

          const color = ['resolved','closed'].includes(event.status) ? '#94a3b8' : getEventColor(
            event.event_type
          );


          const icon = L.divIcon({
            className: "custom-map-marker-wrapper",
            html: `
              <div
                style="
                  width:18px;
                  height:18px;
                  border-radius:50%;
                  background:${color};
                  border:3px solid white;
                  box-shadow:0 0 0 5px ${color}33, 0 3px 12px rgba(0,0,0,.45);
                "
              ></div>
            `,
            iconSize: [18, 18],
            iconAnchor: [9, 9],
          });


          return (
            <Marker
              key={`${event.id}-${latitude}-${longitude}`}
              position={[latitude, longitude]}
              icon={icon}
              eventHandlers={{ add: e => { if (String(event.id) === String(focusId)) e.target.openPopup(); } }}
            >

              <Popup>

                <div style={{ minWidth: "190px" }}>

                  <strong>
                    {eventLabel}
                  </strong>
                  <p>Incident #{event.id}</p>
                  <p>Status: {['open','in_progress','resolved','closed'].includes(event.status) ? event.status.replaceAll('_',' ') : 'open'}</p>
                  <p>{incidentPlace({latitude,longitude,location_name:metadata.location_name})}</p>
                  {event.timestamp && <p>{demo ? 'Assigned time' : 'Reported time'}: {new Date(event.timestamp).toLocaleString('en-IN')}</p>}
                  {metadata.description && <details><summary>Recording details</summary><p>{sampleText(metadata.description)}</p></details>}
                  {demo && <p>Map location assigned for visualization; recording location unverified.</p>}
                  {metadata.evidence_available && <p>Video and detected frames are linked to incident #{event.id} in the government portal.</p>}
                  {metadata.evidence_available && <a href={`${import.meta.env.VITE_GOVERNMENT_PORTAL_URL || 'http://127.0.0.1:5174'}/ai-results?incident=${event.id}`} target="_blank" rel="noreferrer">Government video evidence (sign-in)</a>}

                  <br />

                  <span>
                    Severity:{" "}
                    {event.severity || "unknown"}
                  </span>

                  <br />

                  <span>
                    Confidence:{" "}
                    {event.confidence != null
                      ? `${(
                          Number(event.confidence) * 100
                        ).toFixed(1)}%`
                      : "N/A"}
                  </span>

                  <br />

                  <span>
                    Location:{" "}
                    {latitude.toFixed(5)},{" "}
                    {longitude.toFixed(5)}
                  </span>

                  {event.bus_id != null && (
                    <>
                      <br />
                      <span>
                        Bus: {event.bus_id}
                      </span>
                    </>
                  )}

                </div>

              </Popup>

            </Marker>
          );
        })}

      </MapContainer>


      <div className="map-overlay">

        <span className="map-live-dot" />

        LIVE

        <span>
          {validEvents.length} incidents
        </span>

      </div>


      {validEvents.length === 0 && (
        <div className="map-empty-overlay">
          <strong>No incidents on map</strong>
          <span>
            New detections will appear here automatically.
          </span>
        </div>
      )}

    </div>
  );
}
