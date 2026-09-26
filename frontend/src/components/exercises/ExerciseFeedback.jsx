import { useEffect, useRef, useState } from "react";
import Button from "../common/Button.jsx";
import Card from "../common/Card.jsx";
import SectionLabel from "../common/SectionLabel.jsx";

const OPTIONS = ["Better", "About the same", "Worse"];

export default function ExerciseFeedback({ onBackToList, onBackToChat }) {
  const [choice, setChoice] = useState(null);
  const headingRef = useRef(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    <Card className="p-6 sm:p-8">
      <SectionLabel>Exercise complete</SectionLabel>
      <h1 ref={headingRef} tabIndex={-1} className="display mt-1 text-xl sm:text-2xl">
        How do you feel now?
      </h1>
      <p className="meta mt-2">One tap — quick feedback only, not a measurement.</p>

      <div
        className="mt-6 grid gap-3 sm:grid-cols-3"
        role="group"
        aria-label="How do you feel now?"
      >
        {OPTIONS.map((option) => (
          <Button
            key={option}
            variant={choice === option ? "primary" : "secondary"}
            onClick={() => setChoice(option)}
            aria-pressed={choice === option}
          >
            {option}
          </Button>
        ))}
      </div>

      {choice ? (
        <div className="mt-6 border-t border-border pt-5" role="status">
          <p className="text-sm leading-relaxed text-ink">
            Thanks for sharing — you felt <strong>{choice.toLowerCase()}</strong>.
          </p>
          <p className="mt-2 text-sm leading-relaxed text-secondary">
            This is feedback only. TOM does not score, track, or diagnose how
            you feel.
          </p>
        </div>
      ) : null}

      {/* Leaving never depends on giving feedback. */}
      <div className="mt-6 flex flex-wrap gap-3 border-t border-border pt-5">
        <Button onClick={onBackToChat}>Back to chat</Button>
        <Button variant="secondary" onClick={onBackToList}>
          Try another exercise
        </Button>
      </div>
    </Card>
  );
}
