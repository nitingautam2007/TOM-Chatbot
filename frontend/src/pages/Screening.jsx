import { useEffect, useRef, useState } from "react";
import { ShieldAlert } from "lucide-react";
import Button from "../components/common/Button.jsx";
import Card from "../components/common/Card.jsx";
import LoadingIndicator from "../components/common/LoadingIndicator.jsx";
import SectionLabel from "../components/common/SectionLabel.jsx";
import StatusBadge from "../components/common/StatusBadge.jsx";
import ErrorBanner from "../components/common/ErrorBanner.jsx";
import {
  answerPhq9,
  completePhq9,
  getPhq9State,
  startPhq9,
} from "../services/api.js";

const IDLE = "idle";
const LOADING = "loading";
const ACTIVE = "active";
const DONE = "done";

// Survives tab close so a lost id cannot strand an in-progress session.
// Exported: Dashboard reads the same key to show the latest result.
export const SCREENING_KEY = "tom_screening_id";

function pad(n) {
  return String(n).padStart(2, "0");
}

function Progress({ current, total }) {
  const pct = Math.round((current / total) * 100);
  return (
    <div className="mb-6">
      <div className="mb-2 flex items-center justify-between">
        <span className="label text-ink">
          Question {pad(current)} / {pad(total)}
        </span>
        <span className="meta">{pct}%</span>
      </div>
      <div
        className="progress"
        role="progressbar"
        aria-valuenow={current}
        aria-valuemin={1}
        aria-valuemax={total}
        aria-label="Screening progress"
      >
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ResultCard({ result, onRestart, headingRef }) {
  const safetyFirst =
    result.safety && result.safety.requires_safety_response;

  return (
    <Card className="p-6 sm:p-8">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <div>
          <SectionLabel>Result</SectionLabel>
          <h1
            ref={headingRef}
            tabIndex={-1}
            className="display mt-1 text-xl outline-none sm:text-2xl"
          >
            Check-in complete
          </h1>
          <p className="meta mt-1">Over the last 2 weeks</p>
        </div>
        <StatusBadge tone="success">Done</StatusBadge>
      </div>

      {safetyFirst ? (
        <div className="alert-danger mb-5 p-4" role="alert">
          <div className="mb-2 flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-danger" aria-hidden="true" />
            <span className="label text-ink">Safety check</span>
          </div>
          <p className="whitespace-pre-wrap break-words text-sm leading-relaxed text-ink">
            {result.safety.safety_response ||
              "Please reach out to someone you trust or local support right now."}
          </p>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="card-subtle p-4">
          <p className="label">Score</p>
          <p className="display mt-2 text-4xl">
            {result.score}
            <span className="text-lg text-secondary"> / 27</span>
          </p>
        </div>
        <div className="card-subtle p-4">
          <p className="label">Severity</p>
          <p className="display mt-2 text-xl break-words">
            {result.severity_label}
          </p>
        </div>
      </div>

      {result.safety && result.safety.item9_positive && !safetyFirst ? (
        <p className="notice-warn mt-4 break-words p-3 text-sm text-ink" role="alert">
          You reported thoughts of death or self-harm. If you are struggling,
          please reach out to a trusted person or professional support.
        </p>
      ) : null}

      <p className="mt-5 break-words text-sm leading-relaxed text-secondary">
        {result.disclaimer}
      </p>

      {result.score >= 10 && !safetyFirst ? (
        <p className="mt-3 text-sm leading-relaxed text-secondary">
          Scores in this range often benefit from a conversation with a
          qualified professional who can offer proper support.
        </p>
      ) : null}

      <Button className="mt-6" onClick={onRestart}>
        Start a new check-in
      </Button>
    </Card>
  );
}

export default function Screening() {
  const [phase, setPhase] = useState(IDLE); // idle | loading | active | done
  const [screening, setScreening] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  // A stored id is being restored — block Start so the resume effect cannot
  // be overwritten by a second, racing session.
  const [resuming, setResuming] = useState(false);
  const questionRef = useRef(null);
  const introRef = useRef(null);
  const retryRef = useRef(null);
  const resultRef = useRef(null);

  // A phase/question change unmounts whatever the user was focused on, which
  // would drop focus to <body>. Park it on the heading of the new view.
  useEffect(() => {
    if (phase === DONE) resultRef.current?.focus();
    else if (phase === IDLE) introRef.current?.focus();
    else if (screening?.complete_ready) retryRef.current?.focus();
    else if (phase === ACTIVE) questionRef.current?.focus();
  }, [phase, screening?.question_number, screening?.complete_ready]);

  // Resume an in-progress (or completed) session after refresh.
  // The id is intentionally kept on completion so the result survives a
  // refresh and the Dashboard can show it.
  useEffect(() => {
    const stored = localStorage.getItem(SCREENING_KEY);
    if (!stored) return undefined;
    let cancelled = false;
    setResuming(true);
    (async () => {
      try {
        const state = await getPhq9State(stored);
        if (cancelled) return;
        if (state.status === "completed") {
          setScreening({ result: state });
          setPhase(DONE);
        } else {
          setScreening(state);
          setPhase(ACTIVE);
        }
      } catch (err) {
        if (cancelled) return;
        if (err.status === 404) {
          localStorage.removeItem(SCREENING_KEY);
        } else {
          // Surface resume failures instead of silently staying idle.
          setError(err.message);
        }
      } finally {
        if (!cancelled) setResuming(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleStart() {
    setPhase(LOADING);
    setError("");
    try {
      const data = await startPhq9();
      localStorage.setItem(SCREENING_KEY, data.screening_id);
      setScreening(data);
      setSelected(null);
      setPhase(ACTIVE);
    } catch (err) {
      setError(err.message);
      setPhase(IDLE);
    }
  }

  function handleSelect(value) {
    if (submitting) return;
    setSelected(value);
  }

  async function handleComplete() {
    if (!screening || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const result = await completePhq9(screening.screening_id);
      setScreening((s) => ({ ...s, result }));
      setPhase(DONE);
    } catch (err) {
      // Stay active with complete_ready so the user can retry — never
      // re-ask an already-answered question.
      setError(err.message);
      // The retry view did not mount, so the focus effect never ran.
      retryRef.current?.focus();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmitAnswer() {
    if (selected === null || !screening || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const next = await answerPhq9(
        screening.screening_id,
        screening.question_number,
        selected,
      );
      setSelected(null);
      setScreening((s) => ({
        ...s,
        question_number: next.question_number,
        question: next.question,
        answered_count: next.answered_count,
        complete_ready: next.complete_ready,
      }));
      if (next.complete_ready) {
        setSubmitting(false);
        await handleComplete();
        return;
      }
    } catch (err) {
      if (err.status === 409) {
        // The server already recorded this answer (double submit / stale
        // question). Adopt its authoritative state instead of stranding
        // the user on a question that no longer exists.
        try {
          const fresh = await getPhq9State(screening.screening_id);
          setScreening(fresh);
          setSelected(null);
          setError("");
        } catch (resyncErr) {
          setError(resyncErr.message);
        }
        questionRef.current?.focus();
      } else {
        setError(err.message);
        // The question did not change, so the focus effect never ran and
        // the disabled submit button dropped focus to <body>.
        questionRef.current?.focus();
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleRestart() {
    localStorage.removeItem(SCREENING_KEY);
    setScreening(null);
    setSelected(null);
    setError("");
    setPhase(IDLE);
  }

  // Arrows must move within a radiogroup — role="radio" promises it.
  function handleChoiceKeyDown(event) {
    const delta = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[
      event.key
    ];
    const choices = screening.choices || [];
    if (!delta || submitting || choices.length === 0) return;
    event.preventDefault();
    const index = choices.findIndex((choice) => choice.value === selected);
    const base = index < 0 ? (delta > 0 ? -1 : choices.length) : index;
    const next = Math.min(Math.max(base + delta, 0), choices.length - 1);
    handleSelect(choices[next].value);
    event.currentTarget.querySelectorAll("button")[next]?.focus();
  }

  if (phase === LOADING && !screening) {
    return (
      <div className="mx-auto max-w-2xl px-4 sm:px-6 py-14">
        <LoadingIndicator label="Starting check-in…" />
      </div>
    );
  }

  if (phase === DONE && screening?.result) {
    return (
      <div className="mx-auto max-w-2xl px-4 sm:px-6 py-10 sm:py-14">
        <ResultCard
          result={screening.result}
          onRestart={handleRestart}
          headingRef={resultRef}
        />
      </div>
    );
  }

  if (phase !== ACTIVE || !screening) {
    return (
      <div className="mx-auto max-w-2xl px-4 sm:px-6 py-10 sm:py-14">
        <header className="section-head mb-6">
          <SectionLabel>Depressive-symptom screening</SectionLabel>
          <h1
            ref={introRef}
            tabIndex={-1}
            className="display mt-2 text-2xl outline-none sm:text-3xl"
          >
            PHQ-9 questionnaire
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-secondary">
            9 questions about the last 2 weeks. Structured screening — not a
            diagnosis. Answers stay on this device&apos;s server database and
            are never sent to external services.
          </p>
        </header>

          <ErrorBanner message={error} onDismiss={() => setError("")} />

          <Card className="p-6 sm:p-8">
            <SectionLabel>Status</SectionLabel>
            <h2 className="h-display mt-2 text-xl">Ready for check-in?</h2>
            <p className="mb-6 mt-3 text-sm leading-relaxed text-secondary">
              Over the last 2 weeks, how often have you been bothered by the
              following problems? Each question has the same four frequency
              choices (0–3).
            </p>
            <Button size="lg" onClick={handleStart} disabled={resuming}>
              {resuming ? "Restoring…" : "Start check-in"}
            </Button>
          </Card>
      </div>
    );
  }

  const total = screening.total_questions || 9;

  // All 9 answered but complete() failed earlier — offer a retry only.
  if (screening.complete_ready) {
    return (
      <div className="mx-auto max-w-2xl px-4 sm:px-6 py-10 sm:py-14">
        <Progress current={total} total={total} />
        <ErrorBanner message={error} onDismiss={() => setError("")} />
        <Card className="p-6 sm:p-8">
          <SectionLabel>Almost done</SectionLabel>
          <h1
            ref={retryRef}
            tabIndex={-1}
            className="h-display mt-2 text-xl outline-none"
          >
            All 9 questions answered
          </h1>
          <p className="mb-6 mt-3 text-sm leading-relaxed text-secondary">
            Submit to see your screening result.
          </p>
          <Button onClick={handleComplete} disabled={submitting}>
            {submitting ? "Finishing…" : "Finish screening"}
          </Button>
        </Card>
      </div>
    );
  }

  const current = screening.question_number || 1;
  const last = current === total;

  return (
    <div className="mx-auto max-w-2xl px-4 sm:px-6 py-10 sm:py-14">
      <header className="section-head mb-6">
        <SectionLabel>Depressive-symptom screening</SectionLabel>
        <h1 className="display mt-2 text-2xl sm:text-3xl">
          PHQ-9 questionnaire
        </h1>
        <p className="meta mt-2">
          {screening.timeframe || "Over the last 2 weeks"}
        </p>
      </header>

      <Progress current={current} total={total} />

      <ErrorBanner message={error} onDismiss={() => setError("")} />

      <Card className="p-6 sm:p-8">
        <SectionLabel className="mb-3">
          Question {pad(current)} of {pad(total)}
        </SectionLabel>
        <h2
          ref={questionRef}
          tabIndex={-1}
          className="h-display mb-6 text-lg leading-snug sm:text-xl outline-none"
        >
          {screening.question}
        </h2>

        <div
          className="grid gap-3"
          role="radiogroup"
          aria-label="Frequency over the last 2 weeks"
          onKeyDown={handleChoiceKeyDown}
        >
          {(screening.choices || []).map((choice, index) => {
            const active = selected === choice.value;
            // Roving tabindex: one tab stop for the whole radiogroup.
            const tabbable = active || (selected === null && index === 0);
            return (
              <button
                key={choice.value}
                type="button"
                role="radio"
                aria-checked={active}
                tabIndex={tabbable ? 0 : -1}
                onClick={() => handleSelect(choice.value)}
                disabled={submitting}
                className="choice px-4 py-4"
              >
                <span
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-semibold ${
                    active ? "bg-primary text-white" : "bg-surface-dim text-secondary"
                  }`}
                  aria-hidden="true"
                >
                  {choice.value}
                </span>
                <span className="text-sm font-medium">{choice.label}</span>
              </button>
            );
          })}
        </div>

        <div className="mt-6 flex flex-col gap-3 border-t border-border pt-5 sm:flex-row sm:items-center sm:justify-between">
          <span className="meta">
            {selected !== null
              ? "Selected — submit when ready"
              : "Select a frequency to continue"}
          </span>
          <Button
            onClick={handleSubmitAnswer}
            disabled={selected === null || submitting}
          >
            {submitting
              ? "Saving…"
              : last
                ? "Submit screening"
                : "Next question"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
