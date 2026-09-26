import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { EXERCISES } from "../data/exercises.js";
import ExerciseCard from "../components/exercises/ExerciseCard.jsx";
import ExercisePlayer from "../components/exercises/ExercisePlayer.jsx";
import ExerciseFeedback from "../components/exercises/ExerciseFeedback.jsx";
import SectionLabel from "../components/common/SectionLabel.jsx";

export default function Exercises() {
  const [selected, setSelected] = useState(null);
  const [finished, setFinished] = useState(false);
  const headingRef = useRef(null);
  const navigate = useNavigate();

  // Unmounting the player/feedback drops focus to <body> — park it on the
  // list heading so keyboard users do not restart from the top of the page.
  useEffect(() => {
    if (!selected) headingRef.current?.focus();
  }, [selected]);

  if (finished && selected) {
    return (
      <div className="mx-auto max-w-2xl px-4 sm:px-6 py-10 sm:py-14">
        <ExerciseFeedback
          onBackToList={() => {
            setFinished(false);
            setSelected(null);
          }}
          onBackToChat={() => navigate("/chat")}
        />
      </div>
    );
  }

  if (selected) {
    return (
      <div className="mx-auto max-w-2xl px-4 sm:px-6 py-10 sm:py-14">
        <ExercisePlayer
          exercise={selected}
          onExit={() => setSelected(null)}
          onFinish={() => setFinished(true)}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-4 sm:px-6 py-10 sm:py-14">
      <header className="section-head mb-6">
        <SectionLabel>Stress relief</SectionLabel>
        <h1
          ref={headingRef}
          tabIndex={-1}
          className="display mt-2 text-2xl sm:text-3xl"
        >
          Quick exercises
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-secondary">
          Short practices you can do right here, offline. Pick one, follow the
          steps, and come back to the chat when you are done.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        {EXERCISES.map((exercise) => (
          <ExerciseCard
            key={exercise.id}
            exercise={exercise}
            onSelect={setSelected}
          />
        ))}
      </div>

      <p className="meta mt-8 max-w-2xl">
        Optional, non-clinical relaxation practices — never a substitute for
        TOM&apos;s safety response or professional support.
      </p>
    </div>
  );
}
