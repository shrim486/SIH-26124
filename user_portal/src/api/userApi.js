export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

/* ============================================================
   GENERIC API REQUEST
============================================================ */

async function apiRequest(
  endpoint,
  options = {},
  tokenKey = null
) {
  const token = tokenKey
    ? localStorage.getItem(tokenKey)
    : null;

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: options.method || "GET",
    headers,
    body: options.body
      ? JSON.stringify(options.body)
      : undefined,
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;

    try {
      const errorData = await response.json();

      if (errorData?.detail) {
        message = errorData.detail;
      }
    } catch {
      // Ignore invalid JSON response
    }

    if (response.status === 401 && tokenKey) {
      localStorage.removeItem(tokenKey);

      if (tokenKey === "government_token") {
        localStorage.removeItem("government_role");
      }
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}


/* ============================================================
   GOVERNMENT API
============================================================ */

export const governmentApi = {
  login: async (username, password) => {
    const response = await fetch(
      `${API_BASE_URL}/government/login`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          password,
        }),
      }
    );

    let data = {};

    try {
      data = await response.json();
    } catch {
      data = {};
    }

    if (!response.ok) {
      throw new Error(
        data?.detail || "Government login failed"
      );
    }

    if (!data.access_token) {
      throw new Error(
        "Login succeeded but no access token was returned."
      );
    }

    localStorage.setItem(
      "government_token",
      data.access_token
    );

    if (data.role) {
      localStorage.setItem(
        "government_role",
        data.role
      );
    }

    return data;
  },

  logout: () => {
    localStorage.removeItem("government_token");
    localStorage.removeItem("government_role");
  },

  isAuthenticated: () =>
    Boolean(
      localStorage.getItem("government_token")
    ),

  getDashboard: async () =>
    apiRequest(
      "/government/dashboard",
      {},
      "government_token"
    ),

  getStatistics: async () =>
    apiRequest(
      "/government/statistics",
      {},
      "government_token"
    ),

  getEvents: async () =>
    apiRequest(
      "/government/map-events",
      {},
      "government_token"
    ),

  getMapEvents: async () =>
    apiRequest(
      "/government/map-events",
      {},
      "government_token"
    ),

  getAlerts: async () =>
    apiRequest(
      "/government/alerts",
      {},
      "government_token"
    ),

  getRoadIssues: async () =>
    apiRequest(
      "/government/road-issues",
      {},
      "government_token"
    ),

  getAccidents: async () =>
    apiRequest(
      "/government/accidents",
      {},
      "government_token"
    ),

  getFleet: async () =>
    apiRequest(
      "/government/fleet",
      {},
      "government_token"
    ),

  getAnalytics: async () =>
    apiRequest(
      "/government/analytics",
      {},
      "government_token"
    ),
};


/* ============================================================
   CITIZEN API
============================================================ */

export const userApi = {
  startVideoAnalysis: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE_URL}/video-analysis`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.detail || "Video analysis failed to start");
    return data;
  },

  getVideoAnalysis: async (jobId) => {
    const response = await fetch(`${API_BASE_URL}/video-analysis/${jobId}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data?.detail || "Could not read video analysis status");
    return data;
  },

  videoAnalysisUrl: (jobId) => `${API_BASE_URL}/video-analysis/${jobId}/video`,

  getDashboard: async () =>
    apiRequest("/user/dashboard"),

  getMapEvents: async () =>
    apiRequest("/user/map-events"),

  getAlerts: async () =>
    apiRequest("/user/alerts"),

  getNearbyAlerts: async (
    latitude,
    longitude,
    radius_km = 5
  ) =>
    apiRequest(
      `/user/nearby-alerts?latitude=${encodeURIComponent(
        latitude
      )}&longitude=${encodeURIComponent(
        longitude
      )}&radius_km=${encodeURIComponent(
        radius_km
      )}`
    ),

  getReports: async () =>
    apiRequest("/user/reports"),

  reportIssue: async (payload) =>
    apiRequest(
      "/user/reports",
      {
        method: "POST",
        body: payload,
      }
    ),
};

export default userApi;
