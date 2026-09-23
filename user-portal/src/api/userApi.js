const API_BASE_URL = "http://127.0.0.1:8000/api/v1";


/* ============================================================
   GENERIC API REQUEST
============================================================ */

async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem("government_token");

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
      // Ignore invalid JSON
    }

    if (response.status === 401) {
      localStorage.removeItem("government_token");
      localStorage.removeItem("government_role");
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

  /* ============================================================
     LOGIN
  ============================================================ */

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


  /* ============================================================
     LOGOUT
  ============================================================ */

  logout: () => {
    localStorage.removeItem("government_token");
    localStorage.removeItem("government_role");
  },


  /* ============================================================
     AUTH CHECK
  ============================================================ */

  isAuthenticated: () => {
    return Boolean(
      localStorage.getItem("government_token")
    );
  },


  /* ============================================================
     GOVERNMENT DASHBOARD
  ============================================================ */

  getDashboard: async () => {
    return apiRequest(
      "/government/dashboard"
    );
  },


  getStatistics: async () => {
    return apiRequest(
      "/government/statistics"
    );
  },


  /* ============================================================
     MAP
  ============================================================ */

  getEvents: async () => {
    return apiRequest(
      "/government/map-events"
    );
  },


  getMapEvents: async () => {
    return apiRequest(
      "/government/map-events"
    );
  },


  /* ============================================================
     ALERTS
  ============================================================ */

  getAlerts: async () => {
    return apiRequest(
      "/government/alerts"
    );
  },


  /* ============================================================
     ROAD ISSUES
  ============================================================ */

  getRoadIssues: async () => {
    return apiRequest(
      "/government/road-issues"
    );
  },


  /* ============================================================
     ACCIDENTS
  ============================================================ */

  getAccidents: async () => {
    return apiRequest(
      "/government/accidents"
    );
  },


  /* ============================================================
     FLEET
  ============================================================ */

  getFleet: async () => {
    return apiRequest(
      "/government/fleet"
    );
  },


  /* ============================================================
     ANALYTICS
  ============================================================ */

  getAnalytics: async () => {
    return apiRequest(
      "/government/analytics"
    );
  },
};


/* ============================================================
   CITIZEN API
============================================================ */

/*
   IMPORTANT:

   Your current UserDashboard is using userApi.

   For now, keep this alias so your existing citizen pages
   do not immediately break.
*/

export const userApi = governmentApi;

export default governmentApi;