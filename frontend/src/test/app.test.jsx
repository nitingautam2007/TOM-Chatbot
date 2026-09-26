import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const api = vi.hoisted(() => ({
  sendChatMessage: vi.fn(),
  getConversationMessages: vi.fn(),
  listConversations: vi.fn(),
  getPhq9State: vi.fn(),
  startPhq9: vi.fn(),
  answerPhq9: vi.fn(),
  completePhq9: vi.fn(),
}));

vi.mock("../services/api.js", () => api);

import Chat from "../pages/Chat.jsx";
import ChatInput from "../components/chat/ChatInput.jsx";
import Dashboard from "../pages/Dashboard.jsx";

function typeMessage(text) {
  const textarea = screen.getByLabelText("Message");
  fireEvent.change(textarea, { target: { value: text } });
  return textarea;
}

beforeEach(() => {
  // reset (not clear): mockRejectedValueOnce queues survive mockClear
  // and would leak the next test's first call.
  vi.resetAllMocks();
  sessionStorage.clear();
  localStorage.clear();
});

describe("chat", () => {
  it("sends a message and renders TOM's reply", async () => {
    api.sendChatMessage.mockResolvedValue({
      conversation_id: "c1",
      response: "Hello, I am here with you.",
      is_safety: false,
    });
    render(
      <MemoryRouter>
        <Chat />
      </MemoryRouter>,
    );
    typeMessage("hi tom");
    fireEvent.click(screen.getByLabelText("Send message"));

    expect(await screen.findByText("hi tom")).toBeInTheDocument();
    expect(screen.getByText("Hello, I am here with you.")).toBeInTheDocument();
    expect(sessionStorage.getItem("tom_conversation_id")).toBe("c1");
    // One user bubble + one bot bubble.
    expect(screen.getAllByRole("article")).toHaveLength(2);
  });

  it("renders crisis replies with the distinct safety bubble", async () => {
    api.sendChatMessage.mockResolvedValue({
      conversation_id: "c2",
      response: "I am really sorry you are carrying this.",
      is_safety: true,
    });
    render(
      <MemoryRouter>
        <Chat />
      </MemoryRouter>,
    );
    typeMessage("I want to hurt myself");
    fireEvent.click(screen.getByLabelText("Send message"));

    await screen.findByText("I am really sorry you are carrying this.");
    const safety = document.querySelector(".bubble-safety");
    expect(safety).not.toBeNull();
    expect(safety.textContent).toContain("I am really sorry");
    expect(document.querySelector(".bubble-bot")).toBeNull();
  });

  it("keeps the typed text and shows an alert when the send fails", async () => {
    api.sendChatMessage.mockRejectedValue(new Error("Cannot reach the server"));
    render(
      <MemoryRouter>
        <Chat />
      </MemoryRouter>,
    );
    const textarea = typeMessage("do not lose me");
    fireEvent.click(screen.getByLabelText("Send message"));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Cannot reach the server",
    );
    expect(textarea).toHaveValue("do not lose me");
    // Failure must not append the message to the conversation log.
    expect(screen.queryAllByRole("article")).toHaveLength(0);

    // Dismissible.
    fireEvent.click(screen.getByLabelText("Dismiss error"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("recovers from a stale conversation id by starting a fresh one", async () => {
    sessionStorage.setItem("tom_conversation_id", "gone");
    api.getConversationMessages.mockResolvedValue([]);
    api.sendChatMessage
      .mockRejectedValueOnce(
        Object.assign(new Error("Conversation not found"), { status: 404 }),
      )
      .mockResolvedValueOnce({
        conversation_id: "fresh",
        response: "New start.",
        is_safety: false,
      });
    render(
      <MemoryRouter>
        <Chat />
      </MemoryRouter>,
    );
    // Send is disabled while the stored conversation restores; wait for it
    // so the send below really carries the restored id.
    expect(screen.getByLabelText("Message")).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    await waitFor(() =>
      expect(screen.getByLabelText("Message")).toHaveAttribute(
        "aria-disabled",
        "false",
      ),
    );
    typeMessage("hello");
    fireEvent.click(screen.getByLabelText("Send message"));

    expect(await screen.findByText("New start.")).toBeInTheDocument();
    expect(api.sendChatMessage).toHaveBeenCalledTimes(2);
    expect(api.sendChatMessage.mock.calls[0][1]).toBe("gone");
    expect(api.sendChatMessage.mock.calls[1][1]).toBeNull();
    expect(sessionStorage.getItem("tom_conversation_id")).toBe("fresh");
  });

  it("sends only once for a rapid double-click", async () => {
    let release;
    api.sendChatMessage.mockReturnValue(
      new Promise((resolve) => {
        release = () =>
          resolve({
            conversation_id: "c3",
            response: "ok",
            is_safety: false,
          });
      }),
    );
    render(
      <MemoryRouter>
        <Chat />
      </MemoryRouter>,
    );
    const textarea = typeMessage("dup guard");
    const send = screen.getByLabelText("Send message");
    fireEvent.click(send);
    fireEvent.click(send);
    expect(api.sendChatMessage).toHaveBeenCalledTimes(1);
    release();
    expect(await screen.findByText("dup guard")).toBeInTheDocument();
    // Input clears only after the server accepted the message.
    await waitFor(() => expect(textarea).toHaveValue(""));
  });

  it("clears the conversation only after a confirmed second click", async () => {
    api.sendChatMessage.mockResolvedValue({
      conversation_id: "c4",
      response: "reply",
      is_safety: false,
    });
    render(
      <MemoryRouter>
        <Chat />
      </MemoryRouter>,
    );
    typeMessage("please clear me");
    fireEvent.click(screen.getByLabelText("Send message"));
    await screen.findByText("reply");

    const clearButton = () => screen.getByRole("button", { name: /clear/i });
    fireEvent.click(clearButton());
    // Stray double-click: second click lands inside the guard window.
    fireEvent.click(clearButton());
    expect(screen.getByText("reply")).toBeInTheDocument();

    await new Promise((r) => setTimeout(r, 450));
    fireEvent.click(clearButton());
    expect(screen.queryByText("reply")).not.toBeInTheDocument();
    expect(sessionStorage.getItem("tom_conversation_id")).toBeNull();
    expect(screen.getByText("Conversation empty")).toBeInTheDocument();
  });
});

describe("multilingual input", () => {
  it("does not submit while an IME composition is active", () => {
    // jsdom's KeyboardEventInit drops isComposing, so set it on the event.
    function enterEvent(isComposing) {
      const event = new KeyboardEvent("keydown", {
        key: "Enter",
        bubbles: true,
        cancelable: true,
      });
      Object.defineProperty(event, "isComposing", { value: isComposing });
      return event;
    }

    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    const textarea = screen.getByLabelText("Message");
    fireEvent.change(textarea, { target: { value: "namaste" } });
    fireEvent(textarea, enterEvent(true));
    expect(onSend).not.toHaveBeenCalled();
    fireEvent(textarea, enterEvent(false));
    expect(onSend).toHaveBeenCalledWith("namaste");
  });
});

describe("dashboard", () => {
  const wrap = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>);

  it("shows honest empty states when there is no data", async () => {
    api.listConversations.mockResolvedValue([]);
    wrap(<Dashboard />);
    expect(await screen.findByText("None yet")).toBeInTheDocument();
    expect(screen.getByText("No conversations yet")).toBeInTheDocument();
  });

  it("shows real counts and the latest screening result", async () => {
    api.listConversations.mockResolvedValue([
      {
        id: "c1",
        title: "I feel a bit sad today",
        created_at: "2026-09-25T10:00:00Z",
        updated_at: "2026-09-25T10:05:00Z",
      },
    ]);
    api.getPhq9State.mockResolvedValue({
      screening_id: "s1",
      status: "completed",
      score: 12,
      severity: "moderate",
      severity_label: "Moderately severe",
      completed_at: "2026-09-20T09:00:00Z",
    });
    localStorage.setItem("tom_screening_id", "s1");
    wrap(<Dashboard />);

    expect(await screen.findByText("12")).toBeInTheDocument();
    expect(
      screen.getByText(/conversation/, { selector: "span" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/View result/)).toBeInTheDocument();
    expect(screen.getByText(/I feel a bit sad today/)).toBeInTheDocument();
  });

  it("reports failure instead of inventing numbers", async () => {
    api.listConversations.mockRejectedValue(new Error("down"));
    api.getPhq9State.mockRejectedValue(new Error("down"));
    localStorage.setItem("tom_screening_id", "s1");
    wrap(<Dashboard />);

    const messages = await screen.findAllByText(
      /Couldn't load — is the backend running\?/,
    );
    expect(messages).toHaveLength(2);
    expect(screen.queryByText("None yet")).not.toBeInTheDocument();
  });
});
