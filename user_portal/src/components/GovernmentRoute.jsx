import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { governmentApi } from "../api/userApi";
import useGovernmentAccess from '../../../shared/useGovernmentAccess';

const access = {
  getToken:()=>sessionStorage.getItem('government_token'),
  verify:signal=>governmentApi.checkSession(signal),
  clear:()=>{sessionStorage.removeItem('government_token');sessionStorage.removeItem('government_role');localStorage.removeItem('government_token');localStorage.removeItem('government_role');},
};

export default function GovernmentRoute({ children }) {
  const location = useLocation();

  const {status} = useGovernmentAccess(access);

  if (status==='checking') return <main className="civic-signin civic-ui"><p role="status">Checking government session…</p></main>;
  if (status!=='verified') {
    return (
      <Navigate
        to="/government-login"
        replace
        state={{
          from: location.pathname + location.search,
        }}
      />
    );
  }

  return children;
}
