import React, { useState } from "react";
import {
  CheckCircle,
  Crosshair,
  MapPin,
  Send,
} from "lucide-react";

import { userApi } from "../api/userApi";

export default function ReportIssue() {
  const [form, setForm] = useState({
    event_type: "pothole",
    description: "",
    latitude: "",
    longitude: "",
    severity: "medium",
  });

  const [locating, setLocating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function getLocation() {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by this browser.");
      return;
    }

    setLocating(true);
    setError("");

    navigator.geolocation.getCurrentPosition(
      (position) => {
        update("latitude", position.coords.latitude.toFixed(6));
        update("longitude", position.coords.longitude.toFixed(6));
        setLocating(false);
      },
      () => {
        setError(
          "Unable to access your location. Please allow location permission."
        );
        setLocating(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
      }
    );
  }

  async function submit(event) {
    event.preventDefault();

    setSubmitting(true);
    setSuccess("");
    setError("");

    try {
      const payload = {
        event_type: form.event_type,
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        severity: form.severity,
        description: form.description,
      };

      await userApi.reportIssue(payload);

      setSuccess(
        "Your report has been submitted successfully."
      );

      setForm({
        event_type: "pothole",
        description: "",
        latitude: "",
        longitude: "",
        severity: "medium",
      });
    } catch (err) {
      console.error(err);
      setError(
        err.message ||
          "Could not submit the report. Check the backend endpoint."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="form-page">
      <div className="form-intro">
        <span className="section-kicker">CITIZEN REPORTING</span>
        <h2>Report a road or safety issue</h2>
        <p>
          Help UrbanIQ build a clearer picture of what is happening
          on the streets.
        </p>
      </div>

      {success && (
        <div className="success-banner">
          <CheckCircle size={20} />
          {success}
        </div>
      )}

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <form className="issue-form" onSubmit={submit}>
        <div className="form-grid">
          <label>
            Issue type
            <select
              value={form.event_type}
              onChange={(e) =>
                update("event_type", e.target.value)
              }
            >
              <option value="pothole">Pothole</option>
              <option value="waterlogging">Waterlogging</option>
              <option value="accident">Accident</option>
              <option value="damaged_road">Damaged Road</option>
              <option value="traffic">Traffic Bottleneck</option>
              <option value="missing_sign">Missing Signboard</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label>
            Severity
            <select
              value={form.severity}
              onChange={(e) =>
                update("severity", e.target.value)
              }
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </label>
        </div>

        <label>
          Description
          <textarea
            value={form.description}
            onChange={(e) =>
              update("description", e.target.value)
            }
            placeholder="Describe what you observed..."
            rows={5}
            required
          />
        </label>

        <div className="location-box">
          <div className="location-heading">
            <div className="location-icon">
              <MapPin size={20} />
            </div>

            <div>
              <strong>Incident location</strong>
              <p>
                Use your current GPS location or enter coordinates.
              </p>
            </div>
          </div>

          <button
            type="button"
            className="location-button"
            onClick={getLocation}
            disabled={locating}
          >
            <Crosshair size={17} />
            {locating
              ? "Finding location..."
              : "Use my current location"}
          </button>

          <div className="form-grid">
            <label>
              Latitude
              <input
                value={form.latitude}
                onChange={(e) =>
                  update("latitude", e.target.value)
                }
                placeholder="12.971600"
                required
              />
            </label>

            <label>
              Longitude
              <input
                value={form.longitude}
                onChange={(e) =>
                  update("longitude", e.target.value)
                }
                placeholder="77.594600"
                required
              />
            </label>
          </div>
        </div>

        <button
          type="submit"
          className="submit-button"
          disabled={submitting}
        >
          <Send size={17} />
          {submitting ? "Submitting..." : "Submit report"}
        </button>
      </form>
    </div>
  );
}