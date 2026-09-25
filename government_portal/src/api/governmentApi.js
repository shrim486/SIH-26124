const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000/api/v1';

async function request(endpoint, options = {}) {
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
    if (response.status === 401) {
      sessionStorage.removeItem('government_token');
      window.dispatchEvent(new Event('government-unauthorized'));
    }
    const text = await response.text();
    throw new Error(text || `API request failed: ${response.status}`);
  }

  return response.json();
}

export const governmentApi = {
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
  getFleet() {
    return request('/government/fleet');
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
