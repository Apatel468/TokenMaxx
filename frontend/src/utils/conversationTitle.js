/**
 * Client-side conversation title helper.
 * Titles are generated on the backend after the first assistant reply.
 */

const PLACEHOLDER = "New Chat";

export function resolveChatTitle({
  conversationId,
  savedTitle,
  messages,
  conversations,
}) {
  if (!conversationId && messages.length === 0) {
    return "New Conversation";
  }

  if (savedTitle?.trim() && savedTitle.trim() !== PLACEHOLDER) {
    return savedTitle.trim();
  }

  const fromList = conversations.find((c) => c.id === conversationId);
  if (fromList?.title?.trim() && fromList.title.trim() !== PLACEHOLDER) {
    return fromList.title.trim();
  }

  if (conversationId) {
    return PLACEHOLDER;
  }

  return "New Conversation";
}

export function resolveSidebarTitle(conv) {
  if (conv.title?.trim() && conv.title.trim() !== PLACEHOLDER) {
    return conv.title.trim();
  }
  return PLACEHOLDER;
}
