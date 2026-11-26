const START = { year: 2025, month: 1 };
const END = { year: 2026, month: 12 };

export function buildMonths() {
  const months = [];
  let year = START.year;
  let month = START.month;
  while (year < END.year || (year === END.year && month <= END.month)) {
    months.push(`${year}-${String(month).padStart(2, "0")}`);
    month += 1;
    if (month > 12) {
      month = 1;
      year += 1;
    }
  }
  return months;
}

export function formatMonthLabel(value) {
  const [year, month] = value.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, 1));
  return date.toLocaleString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
}
