const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000/api/v1';

async function request(endpoint, options = {}, responseType = 'json') {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(sessionStorage.getItem('government_token')
        ? { Authorization: `Bearer ${sessionStorage.getItem('government_token')}` }
        : {}),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      sessionStorage.removeItem('government_token');
      window.dispatchEvent(new Event('government-unauthorized'));
    }
    let message = `Request failed (${response.status}). Please retry.`;
    try { const data = await response.json(); if (data.detail) message = Array.isArray(data.detail) ? data.detail.map(row => row.msg).join('; ') : data.detail; } catch { /* Non-JSON upstream error. */ }
    const error = new Error(message); error.status = response.status; throw error;
  }

  if (responseType === 'frame') return {blob:await response.blob(), capturedAt:response.headers.get('X-Captured-At'), processing:response.headers.get('X-Frame-Processing')};
  return response.json();
}

export const governmentApi = {
  checkSession(signal) { return request('/government/auth-check', {signal, cache:'no-store'}); },
  getRecords(archive = false, signal) { return request(`/government/records?archive=${archive}`, {signal}); },
  getCameraFrame(id, signal) { return request(`/government/fleet/cameras/${id}/frame`, {signal, cache:'no-store'}, 'frame'); },
  getIssues(params = {}, signal) { return request(`/government/issues?${new URLSearchParams(params)}`, {signal}); },
  updateIssueStatus(id, status, note = '') { return request(`/government/issues/${id}/status`, {method: 'PATCH', body: JSON.stringify({status, note})}); },
  getIssueHistory(id) { return request(`/government/issues/${id}/history`); },
  addBus(data) { return request('/government/fleet/buses', {method: 'POST', body: JSON.stringify(data)}); },
  editBus(id, data) { return request(`/government/fleet/buses/${id}`, {method: 'PUT', body: JSON.stringify(data)}); },
  addCamera(data) { return request('/government/fleet/cameras', {method: 'POST', body: JSON.stringify(data)}); },
  updateCamera(id, status) { return request(`/government/fleet/cameras/${id}`, {method: 'PATCH', body: JSON.stringify({status})}); },
  updatePosition(id, data) { return request(`/government/fleet/buses/${id}/position`, {method: 'POST', body: JSON.stringify(data)}); },
  getPositionHistory(id,hours=24,signal) { return request(`/government/fleet/buses/${id}/history?hours=${hours}`,{signal}); },
  editCamera(id,data) { return request(`/government/fleet/cameras/${id}`,{method:'PUT',body:JSON.stringify(data)}); },
  async login(username, password) {
    const data = await request('/government/login', {
      method: 'POST', body: JSON.stringify({ username, password }),
    });
    sessionStorage.setItem('government_token', data.access_token);
  },
  // DASHBOARD
  getStatistics() {
    return request('/government/statistics');
  },

  getDashboard() {
    return request('/government/dashboard');
  },

  // ALERTS
  getAlerts(params = {}) {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.append(key, value);
      }
    });

    const suffix = query.toString() ? `?${query}` : '';

    return request(`/government/alerts${suffix}`);
  },

  updateAlertStatus(id, status) {
    return request(`/government/alerts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },

  // ROAD ISSUES
  getRoadIssues(params = {}) {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.append(key, value);
      }
    });

    const suffix = query.toString() ? `?${query}` : '';

    return request(`/government/road-issues${suffix}`);
  },

  updateRoadIssueStatus(id, status) {
    return request(`/government/road-issues/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },

  // VIOLATIONS
  getViolations(params = {}) {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.append(key, value);
      }
    });

    const suffix = query.toString() ? `?${query}` : '';

    return request(`/government/violations${suffix}`);
  },

  updateViolationStatus(id, status) {
    return request(`/government/violations/${id}/status`, {method:'PATCH',body:JSON.stringify({status})});
  },
  getDetectionIncidents() { return request('/government/analysis-results/incidents'); },
  // ACCIDENTS
  getAccidents(params = {}) {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.append(key, value);
      }
    });

    const suffix = query.toString() ? `?${query}` : '';

    return request(`/government/accidents${suffix}`);
  },

  // FLEET
  getFleet(signal) {
    return request('/government/fleet', {signal});
  },

  // ANALYTICS
  getAnalytics() {
    return request('/government/analytics');
  },

  // MAP
  getMapEvents() {
    return request('/government/map-events');
  },
};
