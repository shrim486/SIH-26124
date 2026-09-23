import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { governmentApi } from "../api/userApi";


export default function GovernmentLogin() {

  const navigate = useNavigate();

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

      navigate("/government");

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
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background:
          "#050b14",
        color: "#fff",
        padding: "24px",
      }}
    >

      <div
        style={{
          width: "100%",
          maxWidth: "430px",
          padding: "36px",
          borderRadius: "18px",
          background:
            "#0b1625",
          border:
            "1px solid #1d344d",
          boxShadow:
            "0 20px 60px rgba(0,0,0,.45)",
        }}
      >

        <div
          style={{
            marginBottom: "28px",
          }}
        >

          <div
            style={{
              fontSize: "12px",
              letterSpacing: "2px",
              color: "#60a5fa",
              fontWeight: 700,
              marginBottom: "8px",
            }}
          >
            URBAN INTELLIGENCE
          </div>

          <h1
            style={{
              margin: 0,
              fontSize: "28px",
            }}
          >
            Government Authority
          </h1>

          <p
            style={{
              color: "#94a3b8",
              marginTop: "10px",
              lineHeight: 1.5,
            }}
          >
            Restricted access for authorized
            urban administration personnel.
          </p>

        </div>


        <form onSubmit={handleLogin}>

          <label
            style={{
              display: "block",
              marginBottom: "8px",
              color: "#cbd5e1",
            }}
          >
            Authority Username
          </label>

          <input
            type="text"
            value={username}
            onChange={(e) =>
              setUsername(e.target.value)
            }
            autoComplete="username"
            required
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "13px",
              marginBottom: "18px",
              borderRadius: "10px",
              border:
                "1px solid #29435d",
              background:
                "#07111d",
              color: "#fff",
              outline: "none",
            }}
          />


          <label
            style={{
              display: "block",
              marginBottom: "8px",
              color: "#cbd5e1",
            }}
          >
            Password
          </label>

          <input
            type="password"
            value={password}
            onChange={(e) =>
              setPassword(e.target.value)
            }
            autoComplete="current-password"
            required
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "13px",
              marginBottom: "18px",
              borderRadius: "10px",
              border:
                "1px solid #29435d",
              background:
                "#07111d",
              color: "#fff",
              outline: "none",
            }}
          />


          {error && (
            <div
              style={{
                marginBottom: "18px",
                padding: "12px",
                borderRadius: "8px",
                background:
                  "rgba(239,68,68,.1)",
                border:
                  "1px solid rgba(239,68,68,.35)",
                color: "#fca5a5",
                fontSize: "14px",
              }}
            >
              {error}
            </div>
          )}


          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "14px",
              border: "none",
              borderRadius: "10px",
              background:
                "#2563eb",
              color: "#fff",
              fontSize: "15px",
              fontWeight: 700,
              cursor:
                loading
                  ? "not-allowed"
                  : "pointer",
              opacity:
                loading ? 0.7 : 1,
            }}
          >
            {loading
              ? "Authenticating..."
              : "Secure Authority Login"}
          </button>

        </form>


        <div
          style={{
            marginTop: "22px",
            paddingTop: "18px",
            borderTop:
              "1px solid #1d344d",
            color: "#64748b",
            fontSize: "12px",
            textAlign: "center",
          }}
        >
          Restricted government system
        </div>

      </div>

    </div>
  );
}