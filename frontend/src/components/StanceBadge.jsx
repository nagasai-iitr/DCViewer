export default function StanceBadge({ stance }) {
  if (!stance) return null;
  return <span className={`stance stance-${stance}`}>{stance}</span>;
}
