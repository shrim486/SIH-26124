// Keep the live alert catalogue authoritative, including resolved removals.
export function routeAlerts(records, compared = [], along = [], showAll = true) {
  const details = new Map(compared.map(item => [item.id, item]));
  for (const item of along) details.set(item.id, item);
  const onRoute = new Set(along.map(item => item.id));
  return records.filter(item => Number.isFinite(item.latitude) && Number.isFinite(item.longitude)
    && Math.abs(item.latitude) <= 90 && Math.abs(item.longitude) <= 180
    && (showAll || onRoute.has(item.id)))
    .map(item => ({...details.get(item.id), ...item, on_route: onRoute.has(item.id)}));
}

export function alertSignature(records) {
  return JSON.stringify(records.map(item => [item.id, item.latitude, item.longitude,
    item.alert_type, item.severity, item.is_demo, item.created_at]).sort((a, b) => a[0] - b[0]));
}
