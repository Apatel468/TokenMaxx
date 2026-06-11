/**
 * Login page — email + password form.
 *
 * On success the parent App receives the user object and shows the Chat tab.
 */
import { useState } from "react";
import { login as loginApi } from "../api/auth.js";

export default function Login({ onSuccess, onGoSignup }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      // POST /auth/login — only for existing accounts
      const data = await loginApi(email.trim(), password);
      onSuccess(data.user);
    } catch (err) {
      setError(err.message || "Login failed");
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

        <h2 className="auth-card__title">Log in</h2>
        <p className="auth-card__hint">
          Sign in to access your chats from any device.
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
              autoComplete="current-password"
            />
          </label>

          {error && <p className="auth-form__error">{error}</p>}

          <button
            type="submit"
            className="auth-form__submit"
            disabled={loading}
          >
            {loading ? "Signing in…" : "Log in"}
          </button>
        </form>

        <p className="auth-card__footer">
          No account?{" "}
          <button type="button" className="auth-link" onClick={onGoSignup}>
            Sign up
          </button>
        </p>
      </div>
    </div>
  );
}
