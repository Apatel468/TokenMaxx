/**
 * ChatPage — multi-turn chat with conversation memory (Phase 3A).
 *
 * Left sidebar: past conversations + New Chat
 * Center: message thread + input
 * Right: routing/cost info for the latest reply
 */
import { useCallback, useEffect, useState } from "react";
import { sendChat } from "../api/chat.js";
import { fetchConversation, fetchConversations } from "../api/conversations.js";

function ChatPage({ onChatComplete }) {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /** Reload conversation list in the sidebar */
  const loadConversationList = useCallback(async () => {
    try {
      const list = await fetchConversations();
      setConversations(list);
    } catch {
      // sidebar failure is non-fatal
    }
  }, []);

  useEffect(() => {
    loadConversationList();
  }, [loadConversationList]);

  /** Open an existing conversation from the sidebar */
  async function openConversation(id) {
    setError(null);
    setResult(null);
    try {
      const detail = await fetchConversation(id);
      setConversationId(detail.id);
      setMessages(detail.messages);
    } catch (err) {
      setError(err.message || "Could not load conversation.");
    }
  }

  /** Start a fresh conversation */
  function startNewChat() {
    setConversationId(null);
    setMessages([]);
    setPrompt("");
    setResult(null);
    setError(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed) {
      setError("Please enter a message before submitting.");
      return;
    }

    setLoading(true);
    setError(null);

    // Optimistically show the user message in the thread
    const optimisticUser = { role: "user", content: trimmed, id: `tmp-${Date.now()}` };
    setMessages((prev) => [...prev, optimisticUser]);
    setPrompt("");

    try {
      const data = await sendChat(trimmed, conversationId);
      setConversationId(data.conversation_id);
      setResult(data);

      // Append assistant reply; replace optimistic user with server thread reload
      const detail = await fetchConversation(data.conversation_id);
      setMessages(detail.messages);

      loadConversationList();
      if (onChatComplete) onChatComplete();
    } catch (err) {
      // Remove optimistic message on failure
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      setPrompt(trimmed);
      setError(err.message || "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat-layout">
      {/* ---- Conversation sidebar ---- */}
      <aside className="conv-sidebar panel">
        <div className="conv-sidebar__header">
          <h2 className="panel__title">Conversations</h2>
          <button type="button" className="conv-new-btn" onClick={startNewChat}>
            + New Chat
          </button>
        </div>
        <div className="conv-list">
          {conversations.length === 0 && (
            <p className="panel__hint">No conversations yet.</p>
          )}
          {conversations.map((conv) => (
            <button
              key={conv.id}
              type="button"
              className={`conv-item ${conversationId === conv.id ? "conv-item--active" : ""}`}
              onClick={() => openConversation(conv.id)}
            >
              <span className="conv-item__preview">{conv.preview}</span>
              <span className="conv-item__meta">
                {conv.message_count} msgs ·{" "}
                {new Date(conv.updated_at).toLocaleDateString()}
              </span>
            </button>
          ))}
        </div>
      </aside>

      {/* ---- Message thread + input ---- */}
      <section className="chat-thread panel">
        <h2 className="panel__title">
          {conversationId ? `Conversation #${conversationId}` : "New Conversation"}
        </h2>

        <div className="thread-messages">
          {messages.length === 0 && !loading && (
            <p className="panel__hint">
              Send a message to start. Follow-ups in the same conversation include
              prior context automatically.
            </p>
          )}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`thread-msg thread-msg--${msg.role}`}
            >
              <span className="thread-msg__role">
                {msg.role === "user" ? "You" : "Assistant"}
              </span>
              <p className="thread-msg__text">{msg.content}</p>
            </div>
          ))}
          {loading && (
            <div className="loading-state loading-state--inline">
              <div className="spinner" />
              <p>Routing and generating…</p>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="prompt-form thread-input">
          <textarea
            className="prompt-form__textarea"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Type your message…"
            rows={3}
            disabled={loading}
          />
          <button
            type="submit"
            className="prompt-form__submit"
            disabled={loading || !prompt.trim()}
          >
            {loading ? "Sending…" : "Send"}
          </button>
        </form>

        {error && <div className="alert alert--error">{error}</div>}
      </section>

      {/* ---- Latest routing result ---- */}
      <section className="panel panel--result">
        <h2 className="panel__title">Latest Routing</h2>

        {!result && !loading && (
          <div className="empty-state">
            <p>Send a message to see model routing and cost savings.</p>
          </div>
        )}

        {result && (
          <div className="result">
            <div className="result__grid">
              <div className="stat-card">
                <span className="stat-card__label">Model</span>
                <span className="stat-card__value stat-card__value--model">
                  {result.selected_model}
                </span>
              </div>
              <div className="stat-card">
                <span className="stat-card__label">Task</span>
                <span className="stat-card__value">
                  <span className="task-badge">{result.task_type}</span>
                </span>
              </div>
            </div>
            <div className="reason-box">
              <span className="reason-box__label">Reason</span>
              <p className="reason-box__text">{result.reason_selected}</p>
            </div>
            <div className="cost-row">
              <div className="cost-card">
                <span className="cost-card__label">Actual</span>
                <span className="cost-card__value">
                  ${result.estimated_actual_cost.toFixed(6)}
                </span>
              </div>
              <div className="cost-card cost-card--premium">
                <span className="cost-card__label">Premium</span>
                <span className="cost-card__value">
                  ${result.estimated_premium_cost.toFixed(6)}
                </span>
              </div>
              <div className="cost-card cost-card--savings">
                <span className="cost-card__label">Saved</span>
                <span className="cost-card__value cost-card__value--savings">
                  {result.estimated_savings_percentage.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export default ChatPage;
