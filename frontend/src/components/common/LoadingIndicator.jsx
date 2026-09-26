export default function LoadingIndicator({ label }) {
  return (
    <div className="flex items-center gap-3 text-sm text-secondary" role="status">
      <span className="flex gap-1.5" aria-hidden="true">
        <span className="load-dot" />
        <span className="load-dot" />
        <span className="load-dot" />
      </span>
      <span className="meta">{label}</span>
    </div>
  );
}
