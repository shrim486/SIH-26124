import React from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import UserLayout from "./components/UserLayout";
import GovernmentRoute from "./components/GovernmentRoute";

import UserDashboard from "./pages/UserDashboard";
import LiveMap from "./pages/LiveMap";
import ReportIssue from "./pages/ReportIssue";
import MyReports from "./pages/MyReports";

import GovernmentLogin from "./pages/GovernmentLogin";
import GovernmentDashboard from "./pages/GovernmentDashboard";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* =====================================================
            CITIZEN PORTAL
            These routes belong ONLY to citizens.
        ===================================================== */}

        <Route
          path="/"
          element={
            <UserLayout>
              <UserDashboard />
            </UserLayout>
          }
        />

        <Route
          path="/map"
          element={
            <UserLayout>
              <LiveMap />
            </UserLayout>
          }
        />

        <Route
          path="/report"
          element={
            <UserLayout>
              <ReportIssue />
            </UserLayout>
          }
        />

        <Route
          path="/reports"
          element={
            <UserLayout>
              <MyReports />
            </UserLayout>
          }
        />


        {/* =====================================================
            GOVERNMENT LOGIN
            Separate entry point.
        ===================================================== */}

        <Route
          path="/government-login"
          element={<GovernmentLogin />}
        />


        {/* =====================================================
            GOVERNMENT PORTAL
            EVERYTHING government stays under /government/*
        ===================================================== */}

        <Route
          path="/government/*"
          element={
            <GovernmentRoute>
              <GovernmentDashboard />
            </GovernmentRoute>
          }
        />


        {/* =====================================================
            UNKNOWN ROUTES
            Never send unknown government-looking routes
            into the citizen portal accidentally.
        ===================================================== */}

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />

      </Routes>
    </BrowserRouter>
  );
}