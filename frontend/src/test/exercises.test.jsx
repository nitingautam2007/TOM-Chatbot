import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import Exercises from "../pages/Exercises.jsx";
import Chat from "../pages/Chat.jsx";

const api = vi.hoisted(() => ({
  sendChatMessage: vi.fn(),
  getConversationMessages: vi.fn(),
}));

vi.mock("../services/api.js", () => api);

function renderExercises() {
  return render(
    <MemoryRouter initialEntries={["/exercises"]}>
      <Routes>
        <Route path="/exercises" element={<Exercises />} />
        <Route path="/chat" element={<p>chat page</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

// The card's accessible name is its whole content, so address cards by the
// unique visible title and click the enclosing button.
function exerciseCard(title) {
  return screen.getByText(title).closest("button");
}

function openExercise(title) {
  fireEvent.click(exerciseCard(title));
}

beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("exercise list", () => {
  it("renders all four exercises", () => {
    renderExercises();
    expect(
      screen.getByRole("heading", { name: "Quick exercises" }),
    ).toBeInTheDocument();
    for (const title of [
      "Breathing",
      "Grounding (5-4-3-2-1)",
      "Muscle relaxation",
      "Calm moment",
    ]) {
      expect(exerciseCard(title)).toBeInTheDocument();
    }
    // Honest, non-clinical framing is visible on the list.
    expect(screen.getByText(/never a substitute/i)).toBeInTheDocument();
  });
});

describe("breathing exercise", () => {
  it("starts and counts down the first phase", () => {
    vi.useFakeTimers();
    renderExercises();
    openExercise("Breathing");

    expect(screen.getByText("Step 1 of 15")).toBeInTheDocument();
    expect(screen.getByText("Press Start to begin.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(screen.getByText("4s left")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText("3s left")).toBeInTheDocument();

    // Inhale (4s) elapses → the Hold phase begins.
    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(screen.getByRole("heading", { level: 2, name: "Hold" })).toBeInTheDocument();
    expect(screen.getByText("Step 2 of 15")).toBeInTheDocument();
  });

  it("pauses and resumes the countdown", () => {
    vi.useFakeTimers();
    renderExercises();
    openExercise("Breathing");
    const toggle = screen.getByRole("button", { name: "Start" });

    fireEvent.click(toggle);
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText("3s left")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pause" }));
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(screen.getByText("3s left")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Resume" }));
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText("2s left")).toBeInTheDocument();
  });
});

describe("grounding exercise", () => {
  it("advances one manual step at a time", () => {
    renderExercises();
    openExercise("Grounding (5-4-3-2-1)");

    expect(screen.getByText("Step 1 of 5")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "5 things you see" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Step 2 of 5")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "4 things you can touch" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(
      screen.getByRole("heading", { level: 2, name: "3 things you can hear" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuetext",
      "Step 3 of 5",
    );
  });
});

describe("completion and feedback", () => {
  it("finishes, collects feedback, and returns to the list", () => {
    renderExercises();
    openExercise("Muscle relaxation");

    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    fireEvent.click(screen.getByRole("button", { name: "Finish" }));

    expect(
      screen.getByRole("heading", { name: "How do you feel now?" }),
    ).toBeInTheDocument();
    // Leaving never depends on giving feedback.
    expect(
      screen.getByRole("button", { name: "Back to chat" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Better" }));
    // Feedback only — no score, no diagnosis.
    expect(screen.getByRole("status")).toHaveTextContent(/feedback only/i);
    expect(screen.getByRole("status")).toHaveTextContent(/does not score/i);

    fireEvent.click(screen.getByRole("button", { name: "Try another exercise" }));
    expect(screen.getByRole("heading", { name: "Quick exercises" })).toBeInTheDocument();
  });

  it("returns to the chat from the feedback screen", () => {
    renderExercises();
    openExercise("Calm moment");
    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    fireEvent.click(screen.getByRole("button", { name: "Finish" }));
    fireEvent.click(screen.getByRole("button", { name: "Better" }));

    fireEvent.click(screen.getByRole("button", { name: "Back to chat" }));
    expect(screen.getByText("chat page")).toBeInTheDocument();
  });

  it("exits an exercise back to the list", () => {
    renderExercises();
    openExercise("Calm moment");
    fireEvent.click(screen.getByRole("button", { name: "Exit" }));
    expect(screen.getByRole("heading", { name: "Quick exercises" })).toBeInTheDocument();
  });
});

describe("keyboard navigation", () => {
  it("opens an exercise from a focused card and starts it from the keyboard", () => {
    renderExercises();
    const card = exerciseCard("Breathing");
    card.focus();
    expect(card).toHaveFocus();

    // jsdom does not run the Enter→click default action; activation is the
    // native button's job — assert focus + activation reach the player.
    fireEvent.click(card);
    const start = screen.getByRole("button", { name: "Start" });
    start.focus();
    expect(start).toHaveFocus();
    fireEvent.click(start);
    expect(screen.getByRole("button", { name: "Pause" })).toBeInTheDocument();

    // Every control is a real, reachable button.
    for (const name of ["Pause", "Next", "Finish", "Exit"]) {
      const el = screen.getByRole("button", { name });
      expect(el).toBeEnabled();
      el.focus();
      expect(el).toHaveFocus();
    }
  });
});

describe("reduced motion", () => {
  it("keeps the timer working when prefers-reduced-motion matches", () => {
    vi.useFakeTimers();
    const original = window.matchMedia;
    window.matchMedia = (query) => ({
      matches: query.includes("prefers-reduced-motion"),
      media: query,
      onchange: null,
      addEventListener() {},
      removeEventListener() {},
      addListener() {},
      removeListener() {},
      dispatchEvent: () => false,
    });

    try {
      renderExercises();
      openExercise("Calm moment");
      fireEvent.click(screen.getByRole("button", { name: "Start" }));
      expect(screen.getByText("20s left")).toBeInTheDocument();
      act(() => {
        vi.advanceTimersByTime(1000);
      });
      expect(screen.getByText("19s left")).toBeInTheDocument();
    } finally {
      window.matchMedia = original;
    }
  });
});

describe("chat exercise suggestion", () => {
  const wrap = (ui) =>
    render(
      <MemoryRouter initialEntries={["/chat"]}>
        <Routes>
          <Route path="/chat" element={ui} />
          <Route path="/exercises" element={<p>exercises page</p>} />
        </Routes>
      </MemoryRouter>,
    );

  it("offers the exercise after a flagged stress reply and opens the page", async () => {
    api.sendChatMessage.mockResolvedValue({
      conversation_id: "c1",
      response: "That sounds like a lot to hold.",
      is_safety: false,
      suggest_exercise: true,
    });
    wrap(<Chat />);
    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "I am stressed about my exams" },
    });
    fireEvent.click(screen.getByLabelText("Send message"));

    const offer = await screen.findByRole("button", {
      name: /Try a quick exercise/,
    });
    fireEvent.click(offer);
    expect(screen.getByText("exercises page")).toBeInTheDocument();
  });

  it("never offers an exercise on a safety reply", async () => {
    api.sendChatMessage.mockResolvedValue({
      conversation_id: "c2",
      response: "I am really sorry you are carrying this.",
      is_safety: true,
      // Even a bad server flag must not survive the safety guard.
      suggest_exercise: true,
    });
    wrap(<Chat />);
    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "I want to hurt myself" },
    });
    fireEvent.click(screen.getByLabelText("Send message"));

    await screen.findByText("I am really sorry you are carrying this.");
    expect(
      screen.queryByRole("button", { name: /Try a quick exercise/ }),
    ).not.toBeInTheDocument();
  });

  it("does not offer an exercise on a normal reply without the flag", async () => {
    api.sendChatMessage.mockResolvedValue({
      conversation_id: "c3",
      response: "Hello, I am here with you.",
      is_safety: false,
    });
    wrap(<Chat />);
    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "hi tom" },
    });
    fireEvent.click(screen.getByLabelText("Send message"));

    await screen.findByText("Hello, I am here with you.");
    expect(
      screen.queryByRole("button", { name: /Try a quick exercise/ }),
    ).not.toBeInTheDocument();
  });
});
