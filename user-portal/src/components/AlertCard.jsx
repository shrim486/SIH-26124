import React from "react";
import {
  AlertTriangle,
  Car,
  Droplets,
  MapPin,
  ShieldAlert,
  Construction,
} from "lucide-react";

function getIcon(type) {
  const value = String(type || "").toLowerCase();

  if (value.includes("water")) return Droplets;
  if (value.includes("accident")) return Car;
  if (value.includes("traffic")) return Construction;
  if (value.includes("pothole")) return AlertTriangle;

  return ShieldAlert;
}

export default function AlertCard({ alert }) {
  const Icon = getIcon(alert?.alert_type || alert?.event_type);

  return (
    <div className="alert-card">
      <div className="alert-icon">
        <Icon size={20} />
      </div>

      <div className="alert-info">
        <div className="alert-title-row">
          <strong>
            {String(
              alert?.alert_type ||
                alert?.event_type ||
                "Urban Alert"
            ).replaceAll("_", " ")}
          </strong>

          <span
            className={`severity severity-${String(
              alert?.severity || "medium"
            ).toLowerCase()}`}
          >
            {alert?.severity || "medium"}
          </span>
        </div>

        <p>
          {alert?.message ||
            "Urban infrastructure issue detected in this area."}
        </p>

        <div className="alert-meta">
          <span>
            <MapPin size={13} />
            {Number(alert?.latitude || 0).toFixed(4)},{" "}
            {Number(alert?.longitude || 0).toFixed(4)}
          </span>

          {alert?.confidence && (
            <span>
              Confidence {Math.round(alert.confidence * 100)}%
            </span>
          )}
        </div>
      </div>
    </div>
  );
}