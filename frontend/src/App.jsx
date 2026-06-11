/**
 * App shell — auth gate, tab navigation, and logout.
 *
 * Unauthenticated users see Login/Signup; after login they land on Chat.
 * Admins get an extra "Admin" tab for employee usage metrics.
 */
import { useEffect, useState } from "react";
import AnalyticsDashboard from "./components/AnalyticsDashboard.jsx";
import AdminDashboard from "./components/AdminDashboard.jsx";
import ChatPage from "./components/ChatPage.jsx";
import Login from "./components/Login.jsx";
import ModelControls from "./components/ModelControls.jsx";
import Signup from "./components/Signup.jsx";
import { fetchMe, logout } from "./api/auth.js";
import { clearToken, getToken } from "./api/http.js";
import "./App.css";

function App() {
  const [user, setUser] = useState(null);
  const [authView, setAuthView] = useState("login");
  const [authChecking, setAuthChecking] = useState(true);
  const [activeTab, setActiveTab] = useState("chat");
  const [analyticsRefresh, setAnalyticsRefresh] = useState(0);

  // On first load, restore session from localStorage JWT if still valid.
  // If the token changes during signup/login, ignore stale /auth/me results.
  useEffect(() => {
    let cancelled = false;
    const tokenAtStart = getToken();

    async function restoreSession() {
      if (!tokenAtStart) {
        if (!cancelled) setAuthChecking(false);
        return;
      }
      try {
        const profile = await fetchMe();
        if (!cancelled && getToken() === tokenAtStart) {
          setUser(profile);
        }
      } catch {
        if (!cancelled && getToken() === tokenAtStart) {
          clearToken();
        }
      } finally {
        if (!cancelled) setAuthChecking(false);
      }
    }

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  /** After signup or login: land on Chat without calling /auth/me again. */
  function handleAuthSuccess(profile) {
    setUser(profile);
    setActiveTab("chat");
    setAuthView("login");
  }

  function handleChatComplete() {
    setAnalyticsRefresh((n) => n + 1);
  }

  async function handleLogout() {
    await logout();
    setUser(null);
    setAuthView("login");
    setActiveTab("chat");
  }

  if (authChecking) {
    return (
      <div className="auth-page">
        <p className="auth-page__loading">Loading…</p>
      </div>
    );
  }

  if (!user) {
    if (authView === "signup") {
      return (
        <Signup
          onSuccess={handleAuthSuccess}
          onGoLogin={() => setAuthView("login")}
        />
      );
    }
    return (
      <Login
        onSuccess={handleAuthSuccess}
        onGoSignup={() => setAuthView("signup")}
      />
    );
  }

  const isAdmin = user.role === "admin";

  return (
    <div className="app">
      <header className="header">
        <div className="header__brand">
          <div className="header__logo" aria-hidden="true">
            <span className="header__logo-mark">T</span>
          </div>
          <div>
            <h1 className="header__title">TokenMaxx</h1>
            <p className="header__subtitle">
              Maximum Intelligence, Minimum Cost
            </p>
          </div>
        </div>

        <nav className="nav-tabs">
          <button
            type="button"
            className={`nav-tabs__btn ${activeTab === "chat" ? "nav-tabs__btn--active" : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            Chat
          </button>
          <button
            type="button"
            className={`nav-tabs__btn ${activeTab === "analytics" ? "nav-tabs__btn--active" : ""}`}
            onClick={() => setActiveTab("analytics")}
          >
            Analytics
          </button>
          <button
            type="button"
            className={`nav-tabs__btn ${activeTab === "settings" ? "nav-tabs__btn--active" : ""}`}
            onClick={() => setActiveTab("settings")}
          >
            Model Controls
          </button>
          {isAdmin && (
            <button
              type="button"
              className={`nav-tabs__btn ${activeTab === "admin" ? "nav-tabs__btn--active" : ""}`}
              onClick={() => setActiveTab("admin")}
            >
              Admin
            </button>
          )}
        </nav>

        <div className="header__user">
          <span className="header__email" title={user.email}>
            {user.email}
          </span>
          {isAdmin && <span className="header__badge">Admin</span>}
          <button
            type="button"
            className="header__logout"
            onClick={handleLogout}
          >
            Log out
          </button>
        </div>
      </header>

      <main className="app-main main">
        {activeTab === "chat" && (
          <ChatPage onChatComplete={handleChatComplete} />
        )}
        {activeTab === "analytics" && (
          <AnalyticsDashboard onRefresh={analyticsRefresh} />
        )}
        {activeTab === "settings" && (
          <ModelControls isAdmin={isAdmin} />
        )}
        {activeTab === "admin" && isAdmin && <AdminDashboard />}
      </main>

      <footer className="app-footer">
        <span className="app-footer__brand">TokenMaxx</span>
        <span className="app-footer__tagline">Maximum Intelligence, Minimum Cost</span>
      </footer>
    </div>
  );
}

export default App;
