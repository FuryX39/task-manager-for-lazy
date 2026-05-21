import { useMemo } from "react";
import type { Category, DayMark, Task } from "../types";
import {
  WEEKDAY_LABELS,
  buildMonthGrid,
  dueDateKey,
  monthTitle,
  toLocalDateKey,
} from "../utils";

interface Props {
  cursor: Date;
  onChangeCursor: (d: Date) => void;
  tasks: Task[];
  categories: Category[];
  dayMarks: DayMark[];
  onSelectDay: (dateKey: string) => void;
}

export default function Calendar({
  cursor,
  onChangeCursor,
  tasks,
  categories,
  dayMarks,
  onSelectDay,
}: Props) {
  const days = useMemo(() => buildMonthGrid(cursor), [cursor]);

  const tasksByDay = useMemo(() => {
    const map = new Map<string, Task[]>();
    for (const t of tasks) {
      const key = dueDateKey(t.due_at);
      const list = map.get(key) ?? [];
      list.push(t);
      map.set(key, list);
    }
    return map;
  }, [tasks]);

  const markByDay = useMemo(() => {
    const map = new Map<string, number>();
    for (const m of dayMarks) map.set(m.day, m.category_id);
    return map;
  }, [dayMarks]);

  const categoryById = useMemo(() => {
    const map = new Map<number, Category>();
    for (const c of categories) map.set(c.id, c);
    return map;
  }, [categories]);

  const todayKey = toLocalDateKey(new Date());
  const currentMonth = cursor.getMonth();

  function shift(delta: number) {
    const next = new Date(cursor);
    next.setDate(1);
    next.setMonth(next.getMonth() + delta);
    onChangeCursor(next);
  }

  return (
    <div className="calendar">
      <header className="calendar-header">
        <button type="button" className="btn-ghost" onClick={() => shift(-1)} aria-label="Предыдущий месяц">
          ‹
        </button>
        <h2>{monthTitle(cursor)}</h2>
        <button type="button" className="btn-ghost" onClick={() => shift(1)} aria-label="Следующий месяц">
          ›
        </button>
        <button type="button" className="btn-ghost btn-today" onClick={() => onChangeCursor(new Date())}>
          Сегодня
        </button>
      </header>

      <div className="calendar-weekdays">
        {WEEKDAY_LABELS.map((w) => (
          <div key={w} className="calendar-weekday">
            {w}
          </div>
        ))}
      </div>

      <div className="calendar-grid">
        {days.map((d) => {
          const key = toLocalDateKey(d);
          const inMonth = d.getMonth() === currentMonth;
          const isToday = key === todayKey;
          const dayTasks = tasksByDay.get(key) ?? [];
          const total = dayTasks.length;
          const open = dayTasks.filter((t) => !t.completed).length;
          const catId = markByDay.get(key);
          const cat = catId !== undefined ? categoryById.get(catId) : undefined;
          const style = cat
            ? { borderColor: cat.color, boxShadow: `inset 0 0 0 1px ${cat.color}55` }
            : undefined;
          return (
            <button
              type="button"
              key={key}
              className={`calendar-cell ${inMonth ? "" : "out"} ${isToday ? "today" : ""}`}
              style={style}
              onClick={() => onSelectDay(key)}
              title={cat?.name}
            >
              <div className="cell-top">
                <span className="cell-day">{d.getDate()}</span>
                {cat && (
                  <span className="cell-dot" style={{ background: cat.color }} aria-hidden />
                )}
              </div>
              {total > 0 && (
                <div className="cell-tasks">
                  <span className="cell-count">{open > 0 ? open : "✓"}</span>
                  <span className="cell-count-total">/{total}</span>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
