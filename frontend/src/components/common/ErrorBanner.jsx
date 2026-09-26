import { AlertCircle, X } from "lucide-react";

export default function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div role="alert" className="alert-danger mb-4 flex items-start gap-3 px-4 py-3 text-sm">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-danger" aria-hidden="true" />
      <div className="flex-1">
        <p className="label text-ink">Something went wrong</p>
        <p className="mt-1 break-words text-ink">{message}</p>
      </div>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border-strong bg-surface text-secondary hover:bg-surface-dim"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      ) : null}
    </div>
  );
}
