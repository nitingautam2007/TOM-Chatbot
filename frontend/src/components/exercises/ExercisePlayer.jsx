import { useEffect, useRef, useState } from "react";
import Button from "../common/Button.jsx";
import Card from "../common/Card.jsx";
import SectionLabel from "../common/SectionLabel.jsx";

const IDLE = "idle";
const RUNNING = "running";
const PAUSED = "paused";

const PHASE_CLASS = {
  Inhale: "breath-inhale",
  Hold: "breath-hold",
  Exhale: "breath-exhale",
};

export default function ExercisePlayer({ exercise, onExit, onFinish }) {
  const steps = exercise.steps;
  const [status, setStatus] = useState(IDLE);
  const [stepIndex, setStepIndex] = useState(0);
  const [remaining, setRemaining] = useState(steps[0].seconds ?? null);
  const headingRef = useRef(null);

  const step = steps[stepIndex];
  const timed = Boolean(step.seconds);
  const timedExercise = steps.some((s) => s.seconds);

  // A view switch unmounts whatever had focus (card, feedback) and drops it
  // to <body> — only then park focus on the step heading. Never steal focus
  // from a button the user is already operating during a step change.
  useEffect(() => {
    const focused = document.activeElement;
    if (!focused || focused === document.body) headingRef.current?.focus();
  }, [stepIndex, status]);

  // Ticking countdown for timed steps; cleared on pause, unmount, step change.
  useEffect(() => {
    if (status !== RUNNING || !step.seconds) return undefined;
    const id = setInterval(() => setRemaining((r) => r - 1), 1000);
    return () => clearInterval(id);
  }, [status, stepIndex, step.seconds]);

  // Timed step finished while running → move on (or finish the exercise).
  useEffect(() => {
    if (status !== RUNNING || !step.seconds || remaining > 0) return;
    advance();
  }, [remaining, status, stepIndex, step.seconds]);

  function advance() {
    const next = stepIndex + 1;
    if (next >= steps.length) {
      onFinish();
      return;
    }
    setStepIndex(next);
    setRemaining(steps[next].seconds ?? null);
  }

  const withinStep = step.seconds
    ? (step.seconds - remaining) / step.seconds
    : 0;
  const pct = Math.round(((stepIndex + withinStep) / steps.length) * 100);
  const running = status === RUNNING;
  const orbPhase = PHASE_CLASS[step.label] ?? "";

  return (
    <Card className="p-6 sm:p-8">
      <header className="mb-6 border-b border-border pb-4">
        <SectionLabel>Exercise</SectionLabel>
        <h1 className="display mt-1 text-xl sm:text-2xl">{exercise.title}</h1>
        <p className="meta mt-1">{exercise.duration}</p>
      </header>

      <p className="mb-6 text-sm leading-relaxed text-secondary">
        {exercise.description}
      </p>

      <div className="mb-6">
        <div className="mb-2 flex items-center justify-between">
          <span className="label text-ink">
            Step {stepIndex + 1} of {steps.length}
          </span>
          <span className="meta">{pct}%</span>
        </div>
        <div
          className="progress"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuetext={`Step ${stepIndex + 1} of ${steps.length}`}
          aria-label="Exercise progress"
        >
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="card-subtle flex flex-col items-center p-5 text-center sm:p-6">
        {exercise.animation === "breath" ? (
          <div
            className={`breath-orb ${status !== IDLE ? orbPhase : ""} ${
              status === PAUSED ? "is-paused" : ""
            } mb-5`}
            style={{ animationDuration: `${step.seconds}s` }}
            aria-hidden="true"
          />
        ) : null}

        <h2
          ref={headingRef}
          tabIndex={-1}
          className="h-display text-2xl sm:text-3xl"
        >
          {step.label}
        </h2>
        <p className="mt-3 max-w-md text-sm leading-relaxed text-secondary">
          {step.detail}
        </p>
        <p className="meta mt-4">
          {status === IDLE
            ? "Press Start to begin."
            : timed
              ? `${remaining}s left`
              : "Take your time — press Next when ready."}
        </p>
      </div>

      <p className="sr-only" role="status">
        Step {stepIndex + 1} of {steps.length} — {step.label}
        {status === PAUSED ? " — paused" : ""}
      </p>

      <div className="mt-6 flex flex-wrap gap-3 border-t border-border pt-5">
        {/* Pause only means something where there is a countdown. */}
        {timedExercise || status === IDLE ? (
          <Button onClick={() => setStatus(running ? PAUSED : RUNNING)}>
            {status === IDLE ? "Start" : running ? "Pause" : "Resume"}
          </Button>
        ) : null}
        <Button variant="secondary" onClick={advance} disabled={status === IDLE}>
          Next
        </Button>
        <Button
          variant="secondary"
          onClick={onFinish}
          disabled={status === IDLE}
        >
          Finish
        </Button>
        <Button variant="secondary" onClick={onExit} className="sm:ml-auto">
          Exit
        </Button>
      </div>
    </Card>
  );
}
