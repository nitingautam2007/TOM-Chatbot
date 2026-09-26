/** Small uppercase eyebrow label. */
export default function SectionLabel({ children, className = "", as: Tag = "p" }) {
  return <Tag className={`label ${className}`}>{children}</Tag>;
}
