import React, { useEffect, useState } from "react";
import { CheckCircle2, Film, LoaderCircle, UploadCloud } from "lucide-react";
import { userApi } from "../api/userApi";

export default function VideoAnalysis() {
  const [job, setJob] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!job || ["complete", "failed"].includes(job.status)) return undefined;
    const timer = setTimeout(async () => {
      try {
        setJob(await userApi.getVideoAnalysis(job.id));
      } catch (err) {
        setError(err.message || "Unable to read video analysis status");
      }
    }, 2000);
    return () => clearTimeout(timer);
  }, [job]);

  async function selectVideo(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    setJob(null);
    setPreviewUrl(URL.createObjectURL(file));
    try {
      setJob(await userApi.startVideoAnalysis(file));
    } catch (err) {
      setError(err.message || "Could not start video analysis");
    }
  }

  return (
    <section className="video-analysis-panel">
      <div className="video-analysis-picker">
        <Film size={28} />
        <div>
          <strong>Select a raw traffic video</strong>
          <span>Processing starts as soon as the file is selected.</span>
        </div>
        <label className="video-analysis-button">
          <UploadCloud size={17} />
          Choose video
          <input type="file" accept="video/*" onChange={selectVideo} />
        </label>
      </div>

      {error && <div className="gov-error"><span>{error}</span></div>}
      {previewUrl && <video className="video-analysis-preview" src={previewUrl} controls />}

      {job && job.status !== "complete" && job.status !== "failed" && (
        <div className="video-analysis-status">
          <LoaderCircle size={18} className="gov-spin" />
          <span>Analyzing motorcycle and helmet detections...</span>
        </div>
      )}

      {job?.status === "failed" && <div className="gov-error"><span>{job.error}</span></div>}

      {job?.status === "complete" && (
        <div className="video-analysis-result">
          <div className="video-analysis-status complete">
            <CheckCircle2 size={18} />
            <span>Detection complete</span>
          </div>
          <video className="video-analysis-preview" src={`${userApi.videoAnalysisUrl(job.id)}?t=${Date.now()}`} controls />
        </div>
      )}
    </section>
  );
}