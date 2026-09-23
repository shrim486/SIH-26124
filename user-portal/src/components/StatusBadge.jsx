import React from "react";

export default function StatusBadge({ value }) {
  const text = String(value || "unknown")
    .replaceAll("_", " ")
    .replaceAll("-", " ");

  return (
    <span className={`status-badge status-${String(value).toLowerCase()}`}>
      <span className="status-dot-small" />
      {text}
    </span>
  );
}