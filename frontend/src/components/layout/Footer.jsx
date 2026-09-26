import SectionLabel from "../common/SectionLabel.jsx";

export default function Footer() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-start justify-between gap-3 px-4 py-6 sm:flex-row sm:items-center sm:px-6">
        <div className="flex flex-col gap-1">
          <SectionLabel as="span">TOM — private by design</SectionLabel>
          <span className="meta">Local · No external AI calls</span>
        </div>
        <p className="meta text-left sm:text-right">
          Not a substitute for professional care.
        </p>
      </div>
    </footer>
  );
}
