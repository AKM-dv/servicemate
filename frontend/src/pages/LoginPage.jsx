import { useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../services/apiClient.js";
import { useAuth } from "../context/AuthContext.jsx";

const LoginPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [pin, setPin] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (pin.length !== 6 || !/^[0-9]+$/.test(pin)) {
      setError("Enter a valid 6-digit pin");
      return;
    }
    setIsSubmitting(true);
    setError("");
    try {
      const response = await apiClient.post("/auth/login", { pin });
      if (response.data?.session) {
        localStorage.setItem("servicemate_session_token", response.data.session);
      }
      login();
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.response?.data?.error || "Unable to login. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="auth-brand">
          <img
            src="https://github.com/AKM-dv/servicemate/blob/main/Group%2064.png?raw=true"
            alt="Service Mate"
          />
          <h1>Service Mate CRM</h1>
          <p>Enter the 6-digit access pin to continue.</p>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="pin">Access Pin</label>
          <input
            id="pin"
            name="pin"
            type="password"
            inputMode="numeric"
            pattern="[0-9]{6}"
            maxLength={6}
            value={pin}
            onChange={(event) => setPin(event.target.value.replace(/[^0-9]/g, ""))}
            required
          />
          {error && <div className="auth-error">{error}</div>}
          <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Verifying..." : "Unlock"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
