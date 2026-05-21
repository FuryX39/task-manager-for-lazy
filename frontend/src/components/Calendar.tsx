import { useEffect, useMemo, useRef } from "react";
import { useTz } from "../TzContext";
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
  paintActive: boolean;
  onSelectDay: (dateKey: string) => void;
  onPaintDay: (dateKey: string) => void;
  onPaintCommit: (dateKeys: string[]) => void;
}

export default function Calendar({
  cursor,
  onChangeCursor,
  tasks,
  categories,
  dayMarks,
  paintActive,
  onSelectDay,
  onPaintDay,
  onPaintCommit,
}: Props) {
  const tz = useTz();
  const days = useMemo(() => buildMonthGrid(cursor), [cursor]);

  const tasksByDay = useMemo(() => {
    const map = new Map<string, Task[]>();
    for (const t of tasks) {
      const key = dueDateKey(t.due_at, tz);
      const list = map.get(key) ?? [];
      list.push(t);
      map.set(key, list);
    }
    return map;
  }, [tasks, tz]);

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

  const drag = useRef<{ active: boolean; painted: Set<string> }>({
    active: false,
    painted: new Set(),
  });

  useEffect(() => {
    function endDrag() {
      if (!drag.current.active) return;
      const list = Array.from(drag.current.painted);
      drag.current = { active: false, painted: new Set() };
      if (list.length > 0) onPaintCommit(list);
    }
    window.addEventListener("pointerup", endDrag);
    window.addEventListener("pointercancel", endDrag);
    return () => {
      window.removeEventListener("pointerup", endDrag);
      window.removeEventListener("pointercancel", endDrag);
    };
  }, [onPaintCommit]);

  useEffect(() => {
    if (!paintActive && drag.current.active) {
      drag.current = { active: false, painted: new Set() };
    }
  }, [paintActive]);

  function startPaint(dateKey: string) {
    drag.current = { active: true, painted: new Set([dateKey]) };
    onPaintDay(dateKey);
  }

  function continuePaint(dateKey: string) {
    if (!drag.current.active) return;
    if (drag.current.painted.has(dateKey)) return;
    drag.current.painted.add(dateKey);
    onPaintDay(dateKey);
  }

  function shift(delta: number) {
    const next = new Date(cursor);
    next.setDate(1);
    next.setMonth(next.getMonth() + delta);
    onChangeCursor(next);
  }

  return (
    <div className={`calendar ${paintActive ? "paint-mode" : ""}`}>
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
              onClick={(e) => {
                if (paintActive) {
                  e.preventDefault();
                  return;
                }
                onSelectDay(key);
              }}
              onPointerDown={(e) => {
                if (!paintActive) return;
                if (e.button !== 0 && e.pointerType === "mouse") return;
                e.preventDefault();
                startPaint(key);
              }}
              onPointerEnter={() => continuePaint(key)}
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
