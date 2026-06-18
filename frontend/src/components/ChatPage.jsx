/**

 * ChatPage — multi-turn chat with conversation memory (Phase 3A).

 *

 * Left sidebar: past conversations + New Chat

 * Center: message thread + input

 * Right: routing/cost info for the latest reply

 */

import { useCallback, useEffect, useState } from "react";

import { regenerateChat, streamChat } from "../api/chat.js";

import { fetchConversation, fetchConversations } from "../api/conversations.js";

import PromptEnhancementViewer from "./PromptEnhancementViewer.jsx";
import { CostMetricCard, SavingsMetricCard } from "./CostMetricDisplay.jsx";

import { resolveChatTitle, resolveSidebarTitle } from "../utils/conversationTitle.js";

/** Merge regenerate API metadata into the Latest Routing panel state. */
function applyRegenerateToRoutingResult(previousResult, regenData) {
  if (!previousResult) return previousResult;

  return {
    ...previousResult,
    selected_model: regenData.model_label || regenData.model_used,
    selected_model_id: regenData.model_used,
    reason_selected: regenData.regeneration_reason,
    task_type: regenData.task_type || previousResult.task_type,
    estimated_actual_cost: regenData.actual_cost,
    estimated_premium_cost: regenData.premium_cost,
    estimated_savings_percentage: regenData.savings_percentage,
    input_tokens: regenData.input_tokens,
    output_tokens: regenData.output_tokens,
    was_user_selected: regenData.was_user_selected !== false,
    used_fallback: false,
    fallback_message: "",
    routing_score: 0,
    assistant_message_id: regenData.assistant_message_id,
  };
}

function RagContextMeta({ ragUsed = false, filenames = [] }) {
  if (!ragUsed) return null;

  const safeFilenames = Array.isArray(filenames) ? filenames : [];

  return (
    <div className="rag-context-meta">
      <span className="rag-context-badge">Document Context Used</span>
      {safeFilenames.length > 0 && (
        <span className="rag-context-sources">
          Sources: {safeFilenames.join(", ")}
        </span>
      )}
    </div>
  );
}



function ChatPage({ onChatComplete, enhancePrompts = true }) {

  const [conversationId, setConversationId] = useState(null);

  const [conversationTitle, setConversationTitle] = useState(null);

  const [messages, setMessages] = useState([]);

  const [conversations, setConversations] = useState([]);

  const [prompt, setPrompt] = useState("");

  const [result, setResult] = useState(null);

  const [loading, setLoading] = useState(false);

  const [streamingMessageId, setStreamingMessageId] = useState(null);

  const [regeneratingModel, setRegeneratingModel] = useState(null);

  const [error, setError] = useState(null);



  const chatTitle = resolveChatTitle({

    conversationId,

    savedTitle: conversationTitle,

    messages,

    conversations,

  });



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

      setConversationTitle(detail.title || null);

      setMessages(detail.messages);

    } catch (err) {

      setError(err.message || "Could not load conversation.");

    }

  }



  /** Start a fresh conversation */

  function startNewChat() {

    setConversationId(null);

    setConversationTitle(null);

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



    const optimisticUser = { role: "user", content: trimmed, id: `tmp-${Date.now()}` };
    const streamId = `stream-${Date.now()}`;
    const optimisticAssistant = {
      role: "assistant",
      content: "",
      id: streamId,
      streaming: true,
      response_label: "Router Selected",
    };

    setMessages((prev) => [...prev, optimisticUser, optimisticAssistant]);
    setStreamingMessageId(streamId);
    setPrompt("");



    let routingApplied = false;

    try {

      await streamChat({
        prompt: trimmed,
        conversationId,
        enhancePrompt: enhancePrompts,
        onRoutingComplete: (routingData) => {
          routingApplied = true;
          setResult({
            ...routingData,
            mock_response: "",
            estimated_actual_cost: 0,
            estimated_premium_cost: 0,
            estimated_savings_percentage: 0,
            conversation_id: conversationId,
            user_message_id: 0,
            assistant_message_id: 0,
          });
        },
        onToken: ({ content }) => {
          if (!content) return;
          setMessages((prev) =>
            prev.map((message) =>
              message.id === streamId
                ? { ...message, content: message.content + content }
                : message
            )
          );
        },
        onComplete: async (data) => {
          setConversationId(data.conversation_id);
          if (data.title?.trim()) {
            setConversationTitle(data.title.trim());
          }

          const detail = await fetchConversation(data.conversation_id);
          setConversationTitle(detail.title?.trim() || data.title?.trim() || null);
          setMessages(detail.messages);
          setResult(data);
          loadConversationList();
          if (onChatComplete) onChatComplete();
        },
        onError: (errorData) => {
          throw new Error(errorData?.message || "Streaming failed.");
        },
      });

    } catch (err) {

      setMessages((prev) =>
        prev.filter(
          (message) => message.id !== optimisticUser.id && message.id !== streamId
        )
      );
      if (!routingApplied) {
        setResult(null);
      }
      setPrompt(trimmed);

      setError(err.message || "Could not reach the backend.");

    } finally {

      setStreamingMessageId(null);
      setLoading(false);

    }

  }



  async function handleRegenerate(modelId) {
    if (!result?.conversation_id || !result?.user_message_id) return;
    if (regeneratingModel || loading) return;

    setRegeneratingModel(modelId);
    setError(null);

    try {
      const regenData = await regenerateChat(
        result.conversation_id,
        result.user_message_id,
        modelId,
      );
      const detail = await fetchConversation(result.conversation_id);
      setMessages(detail.messages);
      setResult((prev) => applyRegenerateToRoutingResult(prev, regenData));
      if (onChatComplete) onChatComplete();
    } catch (err) {
      setError(err.message || "Could not regenerate with that model.");
    } finally {
      setRegeneratingModel(null);
    }
  }



  const recommendations =
    result?.top_recommendations?.length > 0
      ? result.top_recommendations
      : (result?.candidate_models || []).slice(0, 5).map((c) => ({
          model_id: c.model_id,
          provider: c.provider || "groq",
          ranking_score: c.score ?? c.ranking_score ?? 0,
          estimated_cost: c.estimated_cost ?? 0,
          estimated_latency: c.estimated_latency ?? 0,
          available: c.available !== false,
          disabled_reason: c.disabled_reason || "",
        }));



  return (

    <div className="chat-page">

      <div className="chat-layout">

        {/* ---- Conversation sidebar ---- */}

        <aside className="conv-sidebar panel">

          <div className="conv-sidebar__header">

            <h2 className="panel__title conv-sidebar__title">Conversations</h2>

            <button type="button" className="conv-new-btn" onClick={startNewChat}>

              + New

            </button>

          </div>

          <div className="conv-list conversation-list">

            {conversations.length === 0 && (

              <p className="panel__hint">No conversations yet. Start your first TokenMaxx chat.</p>

            )}

            {conversations.map((conv) => (

              <button

                key={conv.id}

                type="button"

                className={`conv-item ${conversationId === conv.id ? "conv-item--active" : ""}`}

                onClick={() => openConversation(conv.id)}

              >

                <span className="conv-item__preview">

                  {resolveSidebarTitle(conv)}

                </span>

                <span className="conv-item__meta">

                  {conv.message_count} msgs ·{" "}

                  {conv.updated_at}

                </span>

              </button>

            ))}

          </div>

        </aside>



        {/* ---- Message thread + input ---- */}

        <section className="chat-thread panel">

          <h2 className="panel__title chat-thread__title">{chatTitle}</h2>



          <div className="thread-messages messages">

            {messages.length === 0 && !loading && (

              <p className="panel__hint">
                Welcome to TokenMaxx. Send a message to route intelligently and minimize cost.
                Follow-ups in the same conversation include prior context automatically.
              </p>

            )}

            {messages.map((msg) => {

              const isRegenerated =
                msg.role === "assistant" &&
                msg.response_label === "User Selected Model" &&
                msg.selected_model;

              const isStreaming = msg.id === streamingMessageId || msg.streaming;
              const isActiveStream = msg.id === streamingMessageId;
              const ragUsed =
                Boolean(msg.rag_used) ||
                (isActiveStream && Boolean(result?.rag_used));
              const ragFilenames =
                Array.isArray(msg.source_filenames) && msg.source_filenames.length > 0
                  ? msg.source_filenames
                  : isActiveStream && Array.isArray(result?.source_filenames)
                    ? result.source_filenames
                    : [];

              return (

              <div

                key={msg.id}

                className={`thread-msg thread-msg--${msg.role}`}

              >

                {msg.role === "user" ? (
                  <>
                    <span className="thread-msg__role">You</span>
                    <p className="thread-msg__text">{msg.content}</p>
                  </>
                ) : isRegenerated ? (
                  <>
                    <p className="thread-msg__model-switch">
                      User switched model to &ldquo;{msg.selected_model}&rdquo;
                    </p>
                    <p className="thread-msg__text">{msg.content}</p>
                    <RagContextMeta ragUsed={ragUsed} filenames={ragFilenames} />
                    <PromptEnhancementViewer
                      originalPrompt={msg.original_prompt}
                      enhancedPrompt={msg.enhanced_prompt}
                      enhancementMethod={msg.enhancement_method}
                      promptAnalysis={msg.prompt_analysis}
                    />
                  </>
                ) : (
                  <>
                    <span className="thread-msg__role">
                      {isStreaming && !msg.content
                        ? "Assistant (typing…)"
                        : msg.response_label || "Assistant"}
                    </span>
                    <p className="thread-msg__text">
                      {msg.content}
                      {isStreaming && (
                        <span className="thread-msg__cursor" aria-hidden="true" />
                      )}
                    </p>
                    {!isStreaming && (
                      <RagContextMeta ragUsed={ragUsed} filenames={ragFilenames} />
                    )}
                    {!isStreaming && (
                      <PromptEnhancementViewer
                        originalPrompt={msg.original_prompt}
                        enhancedPrompt={msg.enhanced_prompt}
                        enhancementMethod={msg.enhancement_method}
                        promptAnalysis={msg.prompt_analysis}
                      />
                    )}
                  </>
                )}

              </div>

            );

            })}

            {loading && !streamingMessageId && (

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

        <section className="panel panel--result routing-panel">

          <h2 className="panel__title routing-panel__title">Latest Routing</h2>



          <div className="routing-panel__body">

            {!result && !loading && (

              <div className="empty-state empty-state--compact">

                <p>Send a message to see TokenMaxx model routing and cost savings.</p>

              </div>

            )}



            {result && (

              <div className="result">

                <div className="routing-panel__info">

                  {result.used_fallback && result.fallback_message && !result.was_user_selected && (
                    <div className="routing-fallback-badge" role="status">
                      {result.fallback_message}
                    </div>
                  )}

                  {result.was_user_selected && (
                    <div className="routing-user-selected-badge" role="status">
                      User Selected
                    </div>
                  )}

                  {result.rag_used && (
                    <RagContextMeta
                      ragUsed={Boolean(result.rag_used)}
                      filenames={
                        Array.isArray(result.source_filenames)
                          ? result.source_filenames
                          : []
                      }
                    />
                  )}

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

                    {result.classification_confidence > 0 && (
                      <div className="stat-card">
                        <span className="stat-card__label">Confidence</span>
                        <span className="stat-card__value">
                          {(result.classification_confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}

                    <div className="stat-card">

                      <span className="stat-card__label">Enhancement</span>

                      <span className="stat-card__value">

                        {result.enhancement_method === "disabled" ? "OFF" : "ON"}

                      </span>

                    </div>

                    {result.routing_score > 0 && !result.was_user_selected && (

                      <div className="stat-card">

                        <span className="stat-card__label">Routing Score</span>

                        <span className="stat-card__value">

                          {result.routing_score.toFixed(1)}

                        </span>

                      </div>

                    )}

                    {result.complexity_level && !result.was_user_selected && (
                      <div className="stat-card">
                        <span className="stat-card__label">Complexity</span>
                        <span className="stat-card__value">
                          {result.complexity_level}
                          {result.complexity_score > 0 && (
                            <span className="stat-card__sub">
                              {" "}
                              ({Number(result.complexity_score).toFixed(2)})
                            </span>
                          )}
                        </span>
                      </div>
                    )}

                  </div>

                  {result.provider_availability &&
                    Object.keys(result.provider_availability).length > 0 && (
                      <div className="routing-providers">
                        <span className="routing-candidates__label">
                          Provider keys
                        </span>
                        <div className="routing-providers__chips">
                          {Object.entries(result.provider_availability).map(
                            ([provider, available]) => (
                              <span
                                key={provider}
                                className={`provider-badge provider-badge--${provider} ${
                                  available ? "" : "provider-badge--unavailable"
                                }`}
                              >
                                {provider}
                                {available ? " ✓" : " — no key"}
                              </span>
                            )
                          )}
                        </div>
                      </div>
                    )}

                  {result.routing_explanation?.length > 0 && (
                    <div className="routing-explanation">
                      <span className="routing-candidates__label">
                        Why this model
                      </span>
                      <ul className="routing-explanation__list">
                        {result.routing_explanation.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {result.top_candidate_scores?.length > 0 && (
                    <div className="routing-candidates">
                      <span className="routing-candidates__label">
                        Top candidate scores
                      </span>
                      <ul className="routing-candidates__list">
                        {result.top_candidate_scores.map((candidate, index) => (
                          <li
                            key={candidate.model_id}
                            className={`routing-candidates__item ${
                              candidate.model_id === result.selected_model_id
                                ? "routing-candidates__item--selected"
                                : ""
                            }`}
                          >
                            <span className="routing-candidates__rank">
                              #{index + 1}
                            </span>
                            <span className="routing-candidates__id">
                              {candidate.model_id}
                              {candidate.provider && (
                                <span className="routing-candidates__provider">
                                  {" "}
                                  · {candidate.provider}
                                </span>
                              )}
                            </span>
                            <span className="routing-candidates__score">
                              {Number(candidate.score).toFixed(1)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {recommendations.length > 0 && (

                    <div className="model-recommendations">

                      <span className="model-recommendations__label">

                        Regenerate with another model

                      </span>

                      <p className="model-recommendations__hint">

                        Click a model to generate a new response (one call per click).

                      </p>

                      <div className="model-recommendations__chips">

                        {recommendations.map((rec) => {

                          const isSelected =
                            rec.model_id === result.selected_model_id;

                          const isDisabled = !rec.available;

                          const isLoading = regeneratingModel === rec.model_id;

                          return (

                            <button

                              key={rec.model_id}

                              type="button"

                              className={`model-chip ${

                                isSelected ? "model-chip--selected" : ""

                              } ${isDisabled ? "model-chip--disabled" : ""}`}

                              disabled={

                                isDisabled || !!regeneratingModel || loading

                              }

                              title={

                                isDisabled

                                  ? rec.disabled_reason

                                  : `Score ${rec.ranking_score.toFixed(1)} · ~$${Number(rec.estimated_cost).toFixed(6)} · ~${Math.round(rec.estimated_latency)}ms`

                              }

                              onClick={() => handleRegenerate(rec.model_id)}

                            >

                              <span className="model-chip__id">

                                {rec.model_id}

                              </span>

                              {isSelected && (
                                <span className="model-chip__badge">
                                  {result.was_user_selected ? "User Selected" : "Router"}
                                </span>
                              )}

                              {isLoading && (

                                <span className="model-chip__loading">…</span>

                              )}

                              {isDisabled && (

                                <span className="model-chip__lock">

                                  {rec.disabled_reason}

                                </span>

                              )}

                            </button>

                          );

                        })}

                      </div>

                    </div>

                  )}

                  <div className="reason-box">

                    <span className="reason-box__label">Reason</span>

                    <p className="reason-box__text">{result.reason_selected}</p>

                  </div>

                  {result.classification_reason && (
                    <div className="reason-box reason-box--classification">
                      <span className="reason-box__label">
                        Classification
                        {result.classification_method === "llm" ? " (AI)" : ""}
                      </span>
                      <p className="reason-box__text">
                        {result.classification_reason}
                      </p>
                    </div>
                  )}

                </div>



                <div className="routing-panel__costs">

                  <div className="cost-row">

                    <CostMetricCard
                      label="Actual"
                      cost={result.estimated_actual_cost}
                      inputTokens={result.input_tokens}
                      outputTokens={result.output_tokens}
                    />

                    <CostMetricCard
                      label="Premium Equivalent"
                      cost={result.estimated_premium_cost}
                      inputTokens={result.input_tokens}
                      outputTokens={result.output_tokens}
                      variant="cost-card--premium"
                    />

                    <SavingsMetricCard
                      label="Saved"
                      actualCost={result.estimated_actual_cost}
                      premiumCost={result.estimated_premium_cost}
                      savingsPercentage={result.estimated_savings_percentage}
                      inputTokens={result.input_tokens}
                      outputTokens={result.output_tokens}
                      compact
                    />

                  </div>

                </div>

              </div>

            )}

          </div>

        </section>

      </div>

    </div>

  );

}



export default ChatPage;


