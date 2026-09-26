export default function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <div
        className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-soft text-accent"
        aria-hidden="true"
      >
        <Icon className="h-7 w-7" />
      </div>
      <h2 className="h-display text-lg text-ink">{title}</h2>
      {description && <p className="mt-2 max-w-sm text-sm leading-relaxed text-secondary">{description}</p>}
    </div>
  );
}
