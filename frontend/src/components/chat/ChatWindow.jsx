import { useEffect, useRef } from "react";
import { MessageSquareDashed } from "lucide-react";
import ChatMessage from "./ChatMessage.jsx";
import EmptyState from "../common/EmptyState.jsx";
import LoadingIndicator from "../common/LoadingIndicator.jsx";

export default function ChatWindow({ messages, isSending, isLoading }) {
  const scrollRef = useRef(null);
  // Tracked continuously so a reply arriving while the user is reading
  // history does not yank them to the bottom.
  const nearBottomRef = useRef(true);

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    nearBottomRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    // isSending: the user just sent — follow their own message anywhere.
    if (!nearBottomRef.current && !isSending) return;
    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    // Scroll the log itself, never the document — a nested scroller must
    // not drag the page (and sticky navbar) along with it.
    el.scrollTo({
      top: el.scrollHeight,
      behavior: prefersReduced ? "auto" : "smooth",
    });
  }, [messages, isSending, isLoading]);

  const isEmpty = messages.length === 0 && !isSending && !isLoading;

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      tabIndex={0}
      className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6"
      role="log"
      aria-label="Chat messages"
    >
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
        {isLoading ? (
          <div className="flex justify-center py-6">
            <LoadingIndicator label="Loading conversation…" />
          </div>
        ) : isEmpty ? (
          <EmptyState
            icon={MessageSquareDashed}
            title="Conversation empty"
            description="Share what's on your mind — a greeting, a thought, or anything you'd like to talk about. This stays on your machine."
          />
        ) : (
          messages.map((message) => <ChatMessage key={message.id} message={message} />)
        )}

        {isSending ? (
          <div className="flex gap-3">
            <span
              aria-hidden="true"
              className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-tom-accent text-white"
            >
              <MessageSquareDashed className="h-4 w-4" />
            </span>
            <div className="bubble-bot px-4 py-3">
              <LoadingIndicator label="TOM is thinking…" />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
