// Evidence-video map references on Bengaluru corridors. Their map coordinates are assigned,
// so these remain evidence records rather than confirmed, current road incidents.
const attachedRoadPins = [
  ['bellary-yelahanka-pothole', 'pothole', 'NH 44 · Bellary Road, Yelahanka', 13.1000, 77.5962, 'full_project_run_potholes/potholes_detected.mp4'],
  ['bellary-hebbal-accident', 'accident', 'NH 44 · Hebbal Flyover', 13.0361, 77.5971, 'bengaluru_accident_demo/annotated.mp4'],
  ['mekhri-circle-road-damage', 'road_damage', 'Bellary Road, Mekhri Circle Flyover', 13.0162, 77.5918, 'full_project_run_damaged_road/candidate.mp4'],
  ['koramangala-ejipura-pothole', 'pothole', '100 Feet Road, Ejipura Flyover', 12.9422, 77.6228, 'dashcam_more_sensitive/potholes_detected.mp4'],
  ['orr-bellandur-congestion', 'congestion', 'Outer Ring Road, Bellandur Flyover', 12.9270, 77.6766, 'demo_traffic/annotated.mp4'],
  ['orr-marathahalli-congestion', 'congestion', 'Outer Ring Road, Marathahalli Bridge', 12.9591, 77.6972, 'demo_highway/annotated.mp4'],
  ['old-madras-krpuram-waterlogging', 'waterlogging', 'Old Madras Road, KR Puram Flyover', 13.0060, 77.6951, 'demo_waterlogging/annotated.mp4'],
  ['whitefield-hopefarm-road-damage', 'road_damage', 'Whitefield Main Road, Hope Farm Flyover', 12.9697, 77.7490, 'damaged_road_dashcam/candidate.mp4'],
].map(([video_id, alert_type, location_name, latitude, longitude, video_file]) => ({
  id: `sample-road-${video_id}`,
  video_id,
  alert_type,
  event_type: alert_type,
  severity: 'medium',
  latitude,
  longitude,
  location_name,
  video_file,
  status: 'evidence_only',
  active: false,
  is_demo: true,
  evidence_only: true,
  is_map_attachment: true,
}));

let clipCatalogPromise;

export function getAttachedClipCatalog() {
  if (!clipCatalogPromise) {
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
    clipCatalogPromise = fetch(`${apiBase.replace(/\/$/, '')}/user/map-clips`)
      .then(async response => {
        if (!response.ok) throw new Error(`Could not load clip details (${response.status})`);
        const data = await response.json();
        return data.clips || [];
      })
      .catch(error => { clipCatalogPromise = null; throw error; });
  }
  return clipCatalogPromise;
}

function distanceMeters(a, b) {
  const latitude = (Number(a.latitude) + Number(b.latitude)) / 2;
  const north = (Number(a.latitude) - Number(b.latitude)) * 111_000;
  const east = (Number(a.longitude) - Number(b.longitude)) * 111_000 * Math.cos(latitude * Math.PI / 180);
  return Math.hypot(north, east);
}

export function withAttachedRoadPins(records = [], separationMeters = 140) {
  const located = records.filter(item => Number.isFinite(Number(item.latitude)) && Number.isFinite(Number(item.longitude)));
  return [
    ...located,
    ...attachedRoadPins.filter(pin => !located.some(item => distanceMeters(item, pin) < separationMeters)),
  ];
}

export function attachedVideoUrl(videoId, suffix = '/video') {
  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
  return `${apiBase.replace(/\/$/, '')}/user/map-clips/${encodeURIComponent(videoId)}${suffix}`;
}

export { attachedRoadPins };
