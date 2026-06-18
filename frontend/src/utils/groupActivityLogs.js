/**
 * Group flat activity logs into request-level cards for the Logs UI.
 */

const CHAT_PIPELINE_EVENTS = new Set([
  "chat_request_received",
  "prompt_enhancement_started",
  "prompt_enhancement_completed",
  "rag_search_started",
  "rag_chunks_retrieved",
  "routing_started",
  "routing_completed",
  "model_call_started",
  "model_call_completed",
  "model_call_failed",
]);

const REGENERATE_EVENTS = new Set([
  "regenerate_started",
  "regenerate_completed",
  "model_call_failed",
]);

const DOCUMENT_EVENTS = new Set([
  "document_upload_started",
  "document_indexed",
]);

const PIPELINE_TERMINATORS = new Set([
  "model_call_completed",
  "model_call_failed",
  "regenerate_completed",
]);

function parseLogTime(createdAt) {
  if (!createdAt) return 0;
  const parsed = Date.parse(createdAt);
  if (!Number.isNaN(parsed)) return parsed;
  const match = String(createdAt).match(/(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
  if (!match) return 0;
  let hours = Number(match[1]);
  const minutes = Number(match[2]);
  const meridiem = match[3]?.toUpperCase();
  if (meridiem === "PM" && hours < 12) hours += 12;
  if (meridiem === "AM" && hours === 12) hours = 0;
  return hours * 3600000 + minutes * 60000;
}

export function formatLogTimeShort(createdAt) {
  if (!createdAt) return "—";
  const match = String(createdAt).match(/(\d{1,2}:\d{2}\s*(?:AM|PM)?)/i);
  if (match) return match[1].replace(/\s+/g, " ").trim();
  const parsed = Date.parse(createdAt);
  if (!Number.isNaN(parsed)) {
    return new Date(parsed).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  return createdAt;
}

function isPipelineEvent(eventType) {
  return (
    CHAT_PIPELINE_EVENTS.has(eventType) ||
    REGENERATE_EVENTS.has(eventType) ||
    DOCUMENT_EVENTS.has(eventType)
  );
}

function groupKeyForLog(log) {
  const meta = log.metadata || {};
  if (meta.request_id) return `req:${meta.request_id}`;
  if (log.conversation_id && log.message_id) {
    return `conv:${log.conversation_id}:msg:${log.message_id}`;
  }
  return null;
}

function summarizeGroup(events) {
  const sorted = [...events].sort(
    (a, b) => parseLogTime(a.created_at) - parseLogTime(b.created_at)
  );
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  const hasError = sorted.some(
    (e) => e.level === "error" || e.event_type === "model_call_failed"
  );
  const completed = sorted.some((e) =>
    PIPELINE_TERMINATORS.has(e.event_type)
  );

  let status = "success";
  if (hasError) status = "error";
  else if (!completed && isPipelineEvent(first?.event_type)) status = "in_progress";

  let model = "";
  let provider = "";
  let promptPreview = "";

  for (const event of sorted) {
    const meta = event.metadata || {};
    if (!promptPreview && meta.prompt_preview) {
      promptPreview = meta.prompt_preview;
    }
    if (!promptPreview && meta.filename) {
      promptPreview = `Document: ${meta.filename}`;
    }
    if (meta.model) model = meta.model;
    if (meta.provider) provider = meta.provider;
  }

  if (!promptPreview) {
    const starter = sorted.find((e) => e.event_type === "chat_request_received");
    promptPreview = starter?.message || first?.message || "Activity";
  }

  const kind = REGENERATE_EVENTS.has(first?.event_type)
    ? "regenerate"
    : DOCUMENT_EVENTS.has(first?.event_type)
      ? "document"
      : CHAT_PIPELINE_EVENTS.has(first?.event_type)
        ? "chat"
        : "other";

  const requestId = sorted.find((e) => e.metadata?.request_id)?.metadata?.request_id;

  return {
    id: requestId || `group-${first.id}`,
    kind,
    timestamp: first.created_at,
    lastTimestamp: last.created_at,
    promptPreview,
    status,
    model,
    provider,
    eventCount: sorted.length,
    userEmail: first.user_email || null,
    conversationId: first.conversation_id,
    events: sorted,
  };
}

function assignBurstGroups(logsOldestFirst, used) {
  const groups = [];
  let current = [];

  const flush = () => {
    if (current.length === 0) return;
    groups.push(summarizeGroup(current));
    current.forEach((e) => used.add(e.id));
    current = [];
  };

  for (const log of logsOldestFirst) {
    if (used.has(log.id) || !isPipelineEvent(log.event_type)) continue;

    if (current.length === 0) {
      current.push(log);
      continue;
    }

    const prev = current[current.length - 1];
    const gap = parseLogTime(log.created_at) - parseLogTime(prev.created_at);
    const sameConversation =
      log.conversation_id != null &&
      log.conversation_id === prev.conversation_id;

    if (
      PIPELINE_TERMINATORS.has(prev.event_type) ||
      (sameConversation && gap > 120000) ||
      (!sameConversation && gap > 60000)
    ) {
      flush();
    }
    current.push(log);
  }
  flush();
  return groups;
}

/**
 * @param {Array} logs — newest first from API
 * @returns {Array} grouped summaries, newest first
 */
export function groupActivityLogs(logs) {
  if (!Array.isArray(logs) || logs.length === 0) return [];

  const used = new Set();
  const buckets = new Map();

  for (const log of logs) {
    const key = groupKeyForLog(log);
    if (!key) continue;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(log);
    used.add(log.id);
  }

  const groups = [...buckets.values()].map(summarizeGroup);

  const oldestFirst = [...logs].reverse();
  groups.push(...assignBurstGroups(oldestFirst, used));

  for (const log of logs) {
    if (used.has(log.id)) continue;
    groups.push(summarizeGroup([log]));
    used.add(log.id);
  }

  groups.sort(
    (a, b) => parseLogTime(b.timestamp) - parseLogTime(a.timestamp)
  );
  return groups;
}
