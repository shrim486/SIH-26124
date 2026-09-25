import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { governmentApi } from "../api/userApi";

export default function GovernmentRoute({ children }) {
  const location = useLocation();

  const authenticated = governmentApi.isAuthenticated();

  if (!authenticated) {
    return (
      <Navigate
        to="/government-login"
        replace
        state={{
          from: location.pathname,
        }}
      />
    );
  }

  return children;
}