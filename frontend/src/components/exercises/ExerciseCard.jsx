import { ArrowRight } from "lucide-react";

export default function ExerciseCard({ exercise, onSelect }) {
  return (
    <button
      type="button"
      className="card flex flex-col p-5 text-left transition hover:border-primary"
      onClick={() => onSelect(exercise)}
    >
      <span className="label">{exercise.duration}</span>
      <span className="display mt-1 text-lg text-ink">{exercise.title}</span>
      <span className="mt-2 flex-1 text-sm leading-relaxed text-secondary">
        {exercise.description}
      </span>
      <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-primary">
        Start
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </span>
    </button>
  );
}
