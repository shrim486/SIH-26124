import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { governmentApi } from "../api/userApi";


export default function GovernmentLogin() {

  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [error, setError] =
    useState("");

  const [loading, setLoading] =
    useState(false);


  const handleLogin = async (e) => {

    e.preventDefault();

    setError("");
    setLoading(true);

    try {

      await governmentApi.login(
        username.trim(),
        password
      );

      const destination = location.state?.from;
      navigate(typeof destination === 'string' && (destination === '/government' || destination.startsWith('/government?') || destination.startsWith('/government/')) ? destination : '/government', {replace:true});

    } catch (err) {

      setError(
        err.message ||
        "Invalid government credentials"
      );

    } finally {

      setLoading(false);

    }
  };


  return (
    <main className="government-login-screen">
      <section className="government-login-card">
        <header className="government-login-intro">
          <span className="government-login-brand">GENMAPS</span>
          <h1>Government Authority</h1>
          <p>Restricted access for authorized urban administration personnel.</p>
        </header>

        <form className="government-login-form" onSubmit={handleLogin}>
          <label htmlFor="authority-username">Authority username</label>
          <input
            id="authority-username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />

          <label htmlFor="authority-password">Password</label>
          <input
            id="authority-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />

          {error && <div className="government-login-error" role="alert">{error}</div>}

          <button type="submit" disabled={loading}>
            {loading ? "Authenticating..." : "Secure Authority Login"}
          </button>
        </form>

        <footer className="government-login-footer">Restricted government system</footer>
      </section>
    </main>
  );
}
