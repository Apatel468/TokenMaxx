/**
 * Auth API — signup, login, logout, and current user profile.
 *
 * Signup MUST call POST /auth/signup (creates a new user).
 * Login MUST call POST /auth/login (checks an existing user).
 */
import { authFetch, clearToken, setToken } from "./http.js";
import { API_BASE } from "./config.js";

const SIGNUP_URL = `${API_BASE}/auth/signup`;
const LOGIN_URL = `${API_BASE}/auth/login`;

/** Turn FastAPI error bodies into a single string for the UI. */
function parseApiError(body, fallback) {
  if (!body?.detail) return fallback;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail.map((item) => item.msg || String(item)).join(", ");
  }
  return fallback;
}

/** POST /auth/signup — create a new account (never calls /auth/login). */
export async function signup(email, password) {
  // Discard any stale JWT so signup cannot be confused with an old session
  clearToken();

  const response = await fetch(SIGNUP_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiError(body, "Signup failed"));
  }

  const data = await response.json();
  if (!data.access_token || !data.user) {
    throw new Error("Signup succeeded but the server response was incomplete.");
  }

  setToken(data.access_token);
  return data;
}

/** POST /auth/login — verify an existing account (never calls /auth/signup). */
export async function login(email, password) {
  clearToken();

  const response = await fetch(LOGIN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiError(body, "Login failed"));
  }

  const data = await response.json();
  if (!data.access_token || !data.user) {
    throw new Error("Login succeeded but the server response was incomplete.");
  }

  setToken(data.access_token);
  return data;
}

/** POST /auth/logout — tell the server; always clear token locally */
export async function logout() {
  try {
    await authFetch("/auth/logout", { method: "POST" });
  } catch {
    // still clear token if the network call fails
  }
  clearToken();
}

/** GET /auth/me — validate stored token and return user profile */
export function fetchMe() {
  return authFetch("/auth/me");
}
