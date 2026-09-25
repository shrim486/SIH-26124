import React, { useEffect, useState } from "react";
import { FileWarning, MapPin } from "lucide-react";

import { userApi } from "../api/userApi";
import StatusBadge from "../components/StatusBadge";

export default function MyReports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await userApi.getEvents();

        setReports(
          Array.isArray(data)
            ? data
            : data?.events || []
        );
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  return (
    <div className="reports-page">
      <div className="form-intro">
        <span className="section-kicker">ACTIVITY</span>
        <h2>Reported incidents</h2>
        <p>
          Track issues reported through the UrbanIQ network.
        </p>
      </div>

      <div className="reports-card">
        {loading ? (
          <div className="empty-state">
            Loading reports...
          </div>
        ) : reports.length === 0 ? (
          <div className="empty-state">
            <FileWarning size={35} />
            <strong>No reports yet</strong>
            <p>
              Reports submitted through the portal will appear here.
            </p>
          </div>
        ) : (
          <div className="reports-list">
            {reports.map((report) => (
              <div className="report-row" key={report.id}>
                <div className="report-type-icon">
                  <FileWarning size={19} />
                </div>

                <div className="report-main">
                  <strong>
                    {String(
                      report.event_type || "Incident"
                    ).replaceAll("_", " ")}
                  </strong>

                  <span>
                    <MapPin size={13} />
                    {Number(report.latitude).toFixed(5)},{" "}
                    {Number(report.longitude).toFixed(5)}
                  </span>
                </div>

                <div className="report-right">
                  <StatusBadge
                    value={report.status || "new"}
                  />

                  <small>
                    {report.timestamp
                      ? new Date(
                          report.timestamp
                        ).toLocaleString()
                      : "Recently reported"}
                  </small>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}