/**
 * App shell — tab navigation between Chat and Analytics views.
 */
import { useState } from "react";
import AnalyticsDashboard from "./components/AnalyticsDashboard.jsx";
import ChatPage from "./components/ChatPage.jsx";
import "./App.css";

function App() {
  const [activeTab, setActiveTab] = useState("chat");
  // Bump this after a chat submit so Analytics refreshes when user switches tabs
  const [analyticsRefresh, setAnalyticsRefresh] = useState(0);

  function handleChatComplete() {
    setAnalyticsRefresh((n) => n + 1);
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header__brand">
          <span className="header__logo">⚡</span>
          <div>
            <h1 className="header__title">SmartLLM Router</h1>
            <p className="header__subtitle">
              Routes prompts to the best Groq model and tracks savings
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
    </div>
  );
}

export default App;
