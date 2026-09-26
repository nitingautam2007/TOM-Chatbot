import { useRef, useState } from "react";
import { Trash2 } from "lucide-react";
import useChat from "../hooks/useChat.js";
import ChatWindow from "../components/chat/ChatWindow.jsx";
import ChatInput from "../components/chat/ChatInput.jsx";
import Card from "../components/common/Card.jsx";
import Button from "../components/common/Button.jsx";
import SectionLabel from "../components/common/SectionLabel.jsx";
import StatusBadge from "../components/common/StatusBadge.jsx";
import ErrorBanner from "../components/common/ErrorBanner.jsx";

export default function Chat() {
  const {
    messages,
    isSending,
    isLoadingHistory,
    error,
    sendMessage,
    dismissError,
    clearChat,
  } = useChat();
  const [confirmClear, setConfirmClear] = useState(false);
  const [status, setStatus] = useState("");
  // A habitual double-click must not clear the conversation: the second
  // click only counts once the confirm state has been visibly armed.
  const armedAtRef = useRef(0);

  function handleClear() {
    if (confirmClear) {
      if (Date.now() - armedAtRef.current < 400) return;
      clearChat();
      setConfirmClear(false);
      setStatus("Conversation cleared");
      document.getElementById("chat-message")?.focus();
    } else {
      armedAtRef.current = Date.now();
      setConfirmClear(true);
      setStatus("");
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-4 py-6 sm:px-6 sm:py-8">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <SectionLabel>Conversation</SectionLabel>
          <h1 className="display mt-1 text-2xl sm:text-3xl">TOM</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <StatusBadge tone="primary">Chat</StatusBadge>
            <StatusBadge tone="success">Local</StatusBadge>
            {messages.length > 0 ? (
              <StatusBadge>{messages.length} messages</StatusBadge>
            ) : null}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {messages.length > 0 ? (
            <Button
              variant={confirmClear ? "danger" : "secondary"}
              size="sm"
              disabled={isSending}
              onClick={handleClear}
              onBlur={() => setConfirmClear(false)}
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              {confirmClear ? "Confirm clear?" : "Clear"}
            </Button>
          ) : null}
          <span className="sr-only" role="status">
            {confirmClear
              ? "Press again to confirm clearing the conversation"
              : status}
          </span>
        </div>
      </div>

      <ErrorBanner message={error} onDismiss={dismissError} />

      <Card className="flex min-h-[240px] flex-1 flex-col overflow-hidden p-0">
        <ChatWindow
          messages={messages}
          isSending={isSending}
          isLoading={isLoadingHistory}
        />
        <ChatInput onSend={sendMessage} disabled={isSending || isLoadingHistory} />
      </Card>
    </div>
  );
}
