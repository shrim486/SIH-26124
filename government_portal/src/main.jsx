import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import RoadIssuesPage from './pages/RoadIssuesPage';
import ViolationsPage from './pages/ViolationsPage';
import AccidentsPage from './pages/AccidentsPage';
import AlertsPage from './pages/AlertsPage';
import FleetPage from './pages/FleetPage';
import AnalyticsPage from './pages/AnalyticsPage';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<DashboardPage />} />
          <Route path="road-issues" element={<RoadIssuesPage />} />
          <Route path="violations" element={<ViolationsPage />} />
          <Route path="accidents" element={<AccidentsPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="fleet" element={<FleetPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
