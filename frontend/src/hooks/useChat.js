import { useCallback, useEffect, useRef, useState } from "react";
import { getConversationMessages, sendChatMessage } from "../services/api.js";

const STORAGE_KEY = "tom_conversation_id";

let tempId = 1;

function toUiMessage(m) {
  return {
    id: m.id ?? `temp-${tempId++}`,
    role: m.role,
    content: m.content,
    is_safety: m.is_safety ?? false,
    // Phase 10 flag is ephemeral (not persisted) — restored history never
    // re-offers an exercise.
    suggest_exercise: m.suggest_exercise ?? false,
    timestamp: m.created_at ?? new Date().toISOString(),
  };
}

/**
 * Chat state: messages, active conversation_id, loading/error.
 * Persists conversation_id across refreshes and restores history.
 * All API calls go through services/api.js.
 */
export default function useChat() {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [isSending, setIsSending] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState(null);
  // Synchronous re-entry guard: state updates are async, so two clicks in
  // the same tick would both see isSending === false and double-post.
  const inFlightRef = useRef(false);

  // Restore an existing conversation after refresh.
  // No restoredRef guard: under StrictMode the effect runs twice; each run
  // has its own `cancelled` flag, so the second run always finishes.
  useEffect(() => {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (!stored) return undefined;

    let cancelled = false;

    (async () => {
      try {
        setIsLoadingHistory(true);
        const rows = await getConversationMessages(stored);
        if (cancelled) return;
        setConversationId(stored);
        setMessages(rows.map(toUiMessage));
      } catch (err) {
        if (cancelled) return;
        if (err.status === 404) {
          // Conversation is gone for good — start fresh quietly.
          sessionStorage.removeItem(STORAGE_KEY);
          setConversationId(null);
          setMessages([]);
        } else {
          // Transient failure (network/5xx): keep the id so continuity
          // survives; surface the error instead of wiping history.
          setConversationId(stored);
          setError(err.message);
        }
      } finally {
        if (!cancelled) setIsLoadingHistory(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const sendMessage = useCallback(
    async (text) => {
      const content = text.trim();
      if (!content || inFlightRef.current) return false;

      setError(null);
      inFlightRef.current = true;
      setIsSending(true);

      try {
        let data;
        try {
          data = await sendChatMessage(content, conversationId);
        } catch (err) {
          // Stale conversation id (server DB reset): drop it and start a
          // fresh conversation rather than failing the send permanently.
          if (err.status !== 404 || !conversationId) throw err;
          sessionStorage.removeItem(STORAGE_KEY);
          setConversationId(null);
          data = await sendChatMessage(content, null);
        }
        setConversationId(data.conversation_id);
        sessionStorage.setItem(STORAGE_KEY, data.conversation_id);
        setMessages((prev) => [
          ...prev,
          toUiMessage({ role: "user", content }),
          toUiMessage({
            role: "assistant",
            content: data.response,
            is_safety: data.is_safety,
            suggest_exercise: data.suggest_exercise,
          }),
        ]);
        return true;
      } catch (err) {
        setError(err.message);
        return false;
      } finally {
        inFlightRef.current = false;
        setIsSending(false);
      }
    },
    [conversationId],
  );

  const dismissError = useCallback(() => setError(null), []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  return {
    messages,
    isSending,
    isLoadingHistory,
    error,
    sendMessage,
    dismissError,
    clearChat,
  };
}
