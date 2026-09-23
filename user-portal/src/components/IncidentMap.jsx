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

function MapViewController({ events }) {
  const map = useMap();

  React.useEffect(() => {
    if (!events || events.length === 0) {
      map.setView(DEFAULT_CENTER, 12);
      return;
    }

    const validEvents = events.filter(
      (event) =>
        Number.isFinite(Number(event.latitude)) &&
        Number.isFinite(Number(event.longitude))
    );

    if (validEvents.length === 0) {
      map.setView(DEFAULT_CENTER, 12);
      return;
    }

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

  }, [events, map]);

  return null;
}


/* ============================================================
   EVENT COLOR
   ============================================================ */

function getEventColor(type) {

  const value = String(type || "").toLowerCase();

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
}) {

  const validEvents = events.filter(
    (event) =>
      Number.isFinite(Number(event.latitude)) &&
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


        <MapViewController events={validEvents} />


        {validEvents.map((event) => {

          const latitude = Number(event.latitude);
          const longitude = Number(event.longitude);

          const color = getEventColor(
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
            >

              <Popup>

                <div style={{ minWidth: "190px" }}>

                  <strong>
                    {event.event_type || "Urban Incident"}
                  </strong>

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