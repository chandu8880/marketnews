export function timeAgo(isoString) {
  const then = new Date(isoString).getTime();
  const now = Date.now();
  const diffSec = Math.max(0, Math.floor((now - then) / 1000));

  if (diffSec < 60) return "just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
  timeZone: "Asia/Kolkata",
});

// Absolute IST date+time, e.g. "26 Jul 2026, 3:45 pm" - shown alongside the
// relative "x ago" so it's clear exactly when an article/result was published.
export function formatDateTime(isoString) {
  try {
    return DATE_TIME_FORMATTER.format(new Date(isoString));
  } catch {
    return "";
  }
}
