import { formatMonthLabel } from "../months.js";

export default function MonthScrubber({ months, value, onChange }) {
  const index = Math.max(0, months.indexOf(value));

  return (
    <div className="scrubber">
      <div className="scrubber-meta">
        <span className="scrubber-label">Month</span>
        <strong>{formatMonthLabel(value)}</strong>
      </div>
      <input
        className="scrubber-range"
        type="range"
        min={0}
        max={months.length - 1}
        step={1}
        value={index}
        onChange={(event) => onChange(months[Number(event.target.value)])}
        aria-label="Select month"
      />
      <div className="scrubber-ends">
        <span>{formatMonthLabel(months[0])}</span>
        <span>{formatMonthLabel(months[months.length - 1])}</span>
      </div>
    </div>
  );
}
