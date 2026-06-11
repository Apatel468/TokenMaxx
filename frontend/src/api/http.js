/**
 * Shared HTTP helpers — attaches the JWT to every protected API call.
 *
 * The token is stored in localStorage after login/signup so the user
 * stays signed in across page refreshes and browser tabs.
 */
import { API_BASE } from "./config.js";

/** localStorage key for the JWT (never store the plain password here). */
export const TOKEN_KEY = "tokenmaxx_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * fetch() wrapper that adds Authorization: Bearer <token> and parses JSON errors.
 */
export async function authFetch(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body.detail) {
        message =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
      }
    } catch {
      // keep generic message
    }
    if (response.status === 404 || message === "Not Found") {
      message = "The requested API endpoint was not found.";
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
