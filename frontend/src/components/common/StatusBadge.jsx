/** Small status badge. tone: default | primary | success */
export default function StatusBadge({ tone = "default", children }) {
  const toneClass = tone === "primary" ? "badge-primary" : tone === "success" ? "badge-success" : "";
  return <span className={`badge ${toneClass}`.trim()}>{children}</span>;
}
