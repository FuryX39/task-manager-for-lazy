import { FormEvent, useMemo, useState } from "react";
import type { Category, Task } from "../types";
import { formatTime, isoFromLocal } from "../utils";

interface Props {
  dateKey: string;
  tasks: Task[];
  categories: Category[];
  currentCategoryId: number | undefined;
  onClose: () => void;
  onAddTask: (title: string, notes: string | null, dueIso: string) => Promise<void>;
  onToggleTask: (t: Task) => Promise<void>;
  onDeleteTask: (id: number) => Promise<void>;
  onSetCategory: (categoryId: number | null) => Promise<void>;
}

export default function DayModal({
  dateKey,
  tasks,
  categories,
  currentCategoryId,
  onClose,
  onAddTask,
  onToggleTask,
  onDeleteTask,
  onSetCategory,
}: Props) {
  const [time, setTime] = useState("09:00");
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const sorted = useMemo(
    () => [...tasks].sort((a, b) => a.due_at.localeCompare(b.due_at)),
    [tasks],
  );

  const dateLabel = useMemo(() => {
    const [y, m, d] = dateKey.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "long",
      year: "numeric",
      weekday: "long",
    });
  }, [dateKey]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    try {
      setErr(null);
      await onAddTask(title.trim(), notes.trim() || null, isoFromLocal(dateKey, time));
      setTitle("");
      setNotes("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка");
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <header className="modal-header">
          <h2>{dateLabel}</h2>
          <button type="button" className="btn-ghost" onClick={onClose}>
            ✕
          </button>
        </header>

        <section className="modal-section">
          <p className="section-label">Метка дня</p>
          <div className="category-pills">
            <button
              type="button"
              className={`pill ${currentCategoryId === undefined ? "active" : ""}`}
              onClick={() => onSetCategory(null)}
              style={{ borderColor: "var(--border)" }}
            >
              Без метки
            </button>
            {categories.map((c) => (
              <button
                type="button"
                key={c.id}
                className={`pill ${currentCategoryId === c.id ? "active" : ""}`}
                onClick={() => onSetCategory(c.id)}
                style={{
                  borderColor: c.color,
                  background:
                    currentCategoryId === c.id ? c.color : `${c.color}22`,
                }}
              >
                <span className="dot" style={{ background: c.color }} />
                {c.name}
              </button>
            ))}
          </div>
        </section>

        <section className="modal-section">
          <p className="section-label">Задачи на день</p>
          {sorted.length === 0 ? (
            <p className="empty">Пока пусто</p>
          ) : (
            <ul className="task-list">
              {sorted.map((t) => (
                <li
                  key={t.id}
                  className={`task-item ${t.completed ? "completed" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={t.completed}
                    onChange={() => onToggleTask(t)}
                  />
                  <div>
                    <p className="task-title">
                      <span className="task-time">{formatTime(t.due_at)}</span>
                      {t.title}
                    </p>
                    {t.notes && <p className="task-notes">{t.notes}</p>}
                  </div>
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={() => onDeleteTask(t.id)}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="modal-section">
          <p className="section-label">Новая задача</p>
          {err && <p className="error">{err}</p>}
          <form className="form-grid form-grid-row" onSubmit={submit}>
            <label className="time-field">
              Время
              <input
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                required
              />
            </label>
            <label className="grow">
              Название
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Что сделать"
                required
              />
            </label>
            <label className="full">
              Заметки
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Необязательно"
              />
            </label>
            <button type="submit" className="btn-primary">
              Добавить
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
