export function pad(n: number): string {
  return String(n).padStart(2, "0");
}

export function toLocalDateKey(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Возвращает naive ISO без TZ — сервер интерпретирует как локальное время в APP_TIMEZONE. */
export function isoFromLocal(dateKey: string, time: string): string {
  const t = time.length === 5 ? `${time}:00` : time;
  return `${dateKey}T${t}`;
}

/** YYYY-MM-DD дня, в который попадает iso по часовому поясу tz. */
export function dueDateKey(iso: string, tz: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(iso));
  const y = parts.find((p) => p.type === "year")?.value ?? "";
  const m = parts.find((p) => p.type === "month")?.value ?? "";
  const d = parts.find((p) => p.type === "day")?.value ?? "";
  return `${y}-${m}-${d}`;
}

export function formatTime(iso: string, tz: string): string {
  return new Date(iso).toLocaleTimeString("ru-RU", {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDate(iso: string, tz: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    timeZone: tz,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function formatDateLong(dateKey: string): string {
  const [y, m, d] = dateKey.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
    weekday: "long",
  });
}

export function monthTitle(d: Date): string {
  const text = d.toLocaleDateString("ru-RU", { month: "long", year: "numeric" });
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function eachDateInRange(fromKey: string, toKey: string): string[] {
  const [fy, fm, fd] = fromKey.split("-").map(Number);
  const [ty, tm, td] = toKey.split("-").map(Number);
  const start = new Date(fy, fm - 1, fd);
  const end = new Date(ty, tm - 1, td);
  if (start > end) return [];
  const out: string[] = [];
  const cur = new Date(start);
  while (cur <= end) {
    out.push(toLocalDateKey(cur));
    cur.setDate(cur.getDate() + 1);
  }
  return out;
}

export function weekdayMonFirst(d: Date): number {
  return (d.getDay() + 6) % 7;
}

export const WEEKDAY_LABELS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

export function buildMonthGrid(d: Date): Date[] {
  const year = d.getFullYear();
  const month = d.getMonth();
  const first = new Date(year, month, 1);
  const offset = weekdayMonFirst(first);
  const start = new Date(year, month, 1 - offset);
  const days: Date[] = [];
  for (let i = 0; i < 42; i++) {
    const day = new Date(start);
    day.setDate(start.getDate() + i);
    days.push(day);
  }
  return days;
}
