import React, { useEffect, useState } from "react";
import IncidentMap from "../components/IncidentMap";
import { userApi } from "../api/userApi";


export default function LiveMap() {

  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");


  const loadEvents = async () => {

    try {

      setLoading(true);
      setError("");

      const data = await userApi.getMapEvents();

      setEvents(
        Array.isArray(data)
          ? data
          : []
      );

    } catch (err) {

      console.error("Live map error:", err);

      setError(
        err.message ||
        "Unable to load live map"
      );

    } finally {

      setLoading(false);

    }

  };


  useEffect(() => {

    loadEvents();

    const interval = setInterval(
      loadEvents,
      30000
    );

    return () =>
      clearInterval(interval);

  }, []);


  return (
    <div className="user-page live-map-page">

      <div className="page-heading">

        <div>

          <div className="user-eyebrow">
            <span className="live-dot" />
            LIVE URBAN MONITORING
          </div>

          <h1>Live Incident Map</h1>

          <p>
            Real-time locations of incidents detected
            across the UrbanIQ network.
          </p>

        </div>


        <button
          className="refresh-button"
          onClick={loadEvents}
          disabled={loading}
        >
          ↻ {loading ? "Refreshing..." : "Refresh"}
        </button>

      </div>


      {error && (
        <div className="user-error">
          <strong>Map error</strong>
          <span>{error}</span>
        </div>
      )}


      <div className="full-map-container">

        {loading && events.length === 0 ? (
          <div className="map-loading">
            Loading live map...
          </div>
        ) : (
          <IncidentMap
            events={events}
            fullScreen
          />
        )}

      </div>

    </div>
  );
}