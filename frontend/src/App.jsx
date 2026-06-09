/**
 * App shell — tab navigation between Chat and Analytics views.
 */
import { useState } from "react";
import AnalyticsDashboard from "./components/AnalyticsDashboard.jsx";
import ChatPage from "./components/ChatPage.jsx";
import "./App.css";

function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [analyticsRefresh, setAnalyticsRefresh] = useState(0);

  function handleChatComplete() {
    setAnalyticsRefresh((n) => n + 1);
  }

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
        </nav>
      </header>

      <main className="app-main main">
        {activeTab === "chat" ? (
          <ChatPage onChatComplete={handleChatComplete} />
        ) : (
          <AnalyticsDashboard onRefresh={analyticsRefresh} />
        )}
      </main>

      <footer className="app-footer">
        <span className="app-footer__brand">TokenMaxx</span>
        <span className="app-footer__tagline">Maximum Intelligence, Minimum Cost</span>
      </footer>
    </div>
  );
}

export default App;
