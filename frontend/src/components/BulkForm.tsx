import { FormEvent, useMemo, useState } from "react";
import { WEEKDAY_LABELS, eachDateInRange, isoFromLocal, toLocalDateKey } from "../utils";

interface Props {
  onSubmit: (body: {
    title: string;
    notes: string | null;
    due_ats: string[];
  }) => Promise<number>;
}

const FULL_WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"];

export default function BulkForm({ onSubmit }: Props) {
  const today = useMemo(() => toLocalDateKey(new Date()), []);
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(today);
  const [time, setTime] = useState("19:00");
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [days, setDays] = useState<boolean[]>([false, false, false, false, false, false, false]);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const preview = useMemo(() => {
    const all = eachDateInRange(dateFrom, dateTo);
    return all.filter((key) => {
      const [y, m, d] = key.split("-").map(Number);
      const wd = (new Date(y, m - 1, d).getDay() + 6) % 7;
      return days[wd];
    });
  }, [dateFrom, dateTo, days]);

  function toggleDay(i: number) {
    setDays((prev) => prev.map((v, idx) => (idx === i ? !v : v)));
  }

  function setAllDays(value: boolean[]) {
    setDays(value);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (!title.trim()) {
      setError("Введите название задачи");
      return;
    }
    if (preview.length === 0) {
      setError("Выберите хотя бы один день недели и непустой диапазон");
      return;
    }
    try {
      setSubmitting(true);
      const due_ats = preview.map((key) => isoFromLocal(key, time));
      const created = await onSubmit({
        title: title.trim(),
        notes: notes.trim() || null,
        due_ats,
      });
      setMessage(`Создано задач: ${created}`);
      setTitle("");
      setNotes("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="panel">
      <h2>Массовое добавление</h2>
      <p className="hint">
        Создайте задачу сразу на выбранные дни недели в заданном диапазоне дат.
      </p>

      {error && <p className="error">{error}</p>}
      {message && <p className="status-ok">{message}</p>}

      <form className="form-grid" onSubmit={submit}>
        <div className="form-grid-row">
          <label className="grow">
            Дата от
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              required
            />
          </label>
          <label className="grow">
            Дата до
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              required
            />
          </label>
          <label className="time-field">
            Время
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              required
            />
          </label>
        </div>

        <div>
          <p className="section-label">Дни недели</p>
          <div className="weekday-toggles">
            {WEEKDAY_LABELS.map((short, i) => (
              <button
                type="button"
                key={short}
                className={`weekday-toggle ${days[i] ? "on" : ""}`}
                onClick={() => toggleDay(i)}
                title={FULL_WEEKDAYS[i]}
              >
                {short}
              </button>
            ))}
          </div>
          <div className="actions-row">
            <button
              type="button"
              className="btn-ghost btn-sm"
              onClick={() => setAllDays([true, true, true, true, true, false, false])}
            >
              Будни
            </button>
            <button
              type="button"
              className="btn-ghost btn-sm"
              onClick={() => setAllDays([false, false, false, false, false, true, true])}
            >
              Выходные
            </button>
            <button
              type="button"
              className="btn-ghost btn-sm"
              onClick={() => setAllDays([true, true, true, true, true, true, true])}
            >
              Все
            </button>
            <button
              type="button"
              className="btn-ghost btn-sm"
              onClick={() => setAllDays([false, false, false, false, false, false, false])}
            >
              Очистить
            </button>
          </div>
        </div>

        <label>
          Название задачи
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Например: тренировка"
            required
          />
        </label>

        <label>
          Заметки
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Необязательно"
          />
        </label>

        <p className="hint">
          Будет создано задач: <b>{preview.length}</b>
          {preview.length > 0 &&
            `, первая ${preview[0]}, последняя ${preview[preview.length - 1]}`}
        </p>

        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Создаю…" : "Создать"}
        </button>
      </form>
    </div>
  );
}
