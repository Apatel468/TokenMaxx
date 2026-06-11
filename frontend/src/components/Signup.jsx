/**
 * Signup page — create a new TokenMaxx account.
 *
 * Passwords are hashed on the server (bcrypt); we only send them over HTTPS in production.
 */
import { useState } from "react";
import { signup as signupApi } from "../api/auth.js";

export default function Signup({ onSuccess, onGoLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      // POST /auth/signup — creates user, returns JWT; parent redirects to Chat
      const data = await signupApi(email.trim(), password);
      onSuccess(data.user);
    } catch (err) {
      setError(err.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-card__brand">
          <span className="auth-card__logo">T</span>
          <h1>TokenMaxx</h1>
          <p>Maximum Intelligence, Minimum Cost</p>
        </div>

        <h2 className="auth-card__title">Create account</h2>
        <p className="auth-card__hint">
          Your chats will be saved to your account.
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-form__label">
            Email
            <input
              type="email"
              className="auth-form__input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </label>

          <label className="auth-form__label">
            Password
            <input
              type="password"
              className="auth-form__input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </label>

          <label className="auth-form__label">
            Confirm password
            <input
              type="password"
              className="auth-form__input"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              autoComplete="new-password"
            />
          </label>

          {error && <p className="auth-form__error">{error}</p>}

          <button
            type="submit"
            className="auth-form__submit"
            disabled={loading}
          >
            {loading ? "Creating account…" : "Sign up"}
          </button>
        </form>

        <p className="auth-card__footer">
          Already have an account?{" "}
          <button type="button" className="auth-link" onClick={onGoLogin}>
            Log in
          </button>
        </p>
      </div>
    </div>
  );
}
