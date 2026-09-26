import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import Button from "../common/Button.jsx";

const MAX_LENGTH = 4000; // matches backend ChatRequest.max_length

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  // Auto-grow for multi-line (Shift+Enter) input up to the max-h-40 cap.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const canSend = value.trim().length > 0 && !disabled;
  const nearLimit = value.length > 3600;

  async function submit() {
    if (!canSend) return;
    try {
      const ok = await onSend(value);
      // Only clear the input when the server accepted the message.
      if (ok) setValue("");
    } finally {
      // Always restore focus — including after errors — so the keyboard
      // user is not dropped to <body> when the textarea was re-enabled.
      textareaRef.current?.focus();
    }
  }

  function handleKeyDown(event) {
    // isComposing: let IME (Hindi/Hinglish phonetic input) commit on Enter.
    // React's synthetic event does not carry isComposing — read the native one.
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent?.isComposing
    ) {
      event.preventDefault();
      submit();
    }
    // Shift+Enter inserts a newline (default behaviour)
  }

  return (
    <div className="border-t border-border bg-surface px-4 py-4 sm:px-6">
      <div className="mx-auto flex w-full max-w-3xl items-end gap-2">
        <label htmlFor="chat-message" className="sr-only">
          Message
        </label>
        <textarea
          id="chat-message"
          ref={textareaRef}
          rows={1}
          value={value}
          maxLength={MAX_LENGTH}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          aria-disabled={disabled}
          placeholder="Tell TOM what's on your mind…"
          className="input max-h-40 min-h-12 flex-1 resize-none px-4 py-3 text-sm"
          aria-describedby="chat-disclaimer"
        />
        <Button
          className="h-12 w-12 shrink-0 px-0!"
          onClick={submit}
          disabled={!canSend}
          aria-label="Send message"
        >
          <Send className="h-5 w-5" aria-hidden="true" />
        </Button>
      </div>
      <div className="mx-auto mt-2 flex w-full max-w-3xl items-start justify-between gap-3">
        <p id="chat-disclaimer" className="meta">
          Enter to send · Shift+Enter for newline · Support companion, not a
          medical professional. In a crisis, contact local emergency services.
        </p>
        <span className="meta shrink-0" aria-live={value.length >= MAX_LENGTH ? "polite" : "off"}>
          {nearLimit ? `${value.length}/${MAX_LENGTH}` : ""}
        </span>
      </div>
    </div>
  );
}
