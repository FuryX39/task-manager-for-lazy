import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { Task, TelegramStatus } from "./types";

function toLocalInputValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatDue(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function groupTasks(tasks: Task[]) {
  const now = Date.now();
  const active: Task[] = [];
  const overdue: Task[] = [];
  const done: Task[] = [];

  for (const t of tasks) {
    if (t.completed) {
      done.push(t);
      continue;
    }
    if (new Date(t.due_at).getTime() < now) {
      overdue.push(t);
    } else {
      active.push(t);
    }
  }

  return { active, overdue, done };
}

function TaskRow({
  task,
  overdue,
  onToggle,
  onDelete,
}: {
  task: Task;
  overdue: boolean;
  onToggle: (t: Task) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <li
      className={`task-item ${task.completed ? "completed" : ""} ${overdue ? "overdue" : ""}`}
    >
      <input
        type="checkbox"
        checked={task.completed}
        onChange={() => onToggle(task)}
        aria-label={`Выполнено: ${task.title}`}
      />
      <div>
        <p className="task-title">{task.title}</p>
        <p className="task-meta">{formatDue(task.due_at)}</p>
        {task.notes && <p className="task-notes">{task.notes}</p>}
      </div>
      <button type="button" className="btn-danger" onClick={() => onDelete(task.id)}>
        Удалить
      </button>
    </li>
  );
}

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [tg, setTg] = useState<TelegramStatus>({ linked: false, link_code: null });
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [dueAt, setDueAt] = useState(() => {
    const d = new Date();
    d.setMinutes(d.getMinutes() + 30 - (d.getMinutes() % 15));
    d.setSeconds(0, 0);
    return toLocalInputValue(d);
  });

  const load = useCallback(async () => {
    try {
      setError(null);
      const [taskList, status] = await Promise.all([
        api.listTasks(),
        api.telegramStatus(),
      ]);
      setTasks(taskList);
      setTg(status);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 60_000);
    return () => clearInterval(id);
  }, [load]);

  const groups = useMemo(() => groupTasks(tasks), [tasks]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    try {
      setError(null);
      const due = new Date(dueAt);
      await api.createTask({
        title: title.trim(),
        notes: notes.trim() || null,
        due_at: due.toISOString(),
      });
      setTitle("");
      setNotes("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать задачу");
    }
  }

  async function toggleTask(task: Task) {
    try {
      setError(null);
      await api.updateTask(task.id, { completed: !task.completed });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка обновления");
    }
  }

  async function deleteTask(id: number) {
    if (!confirm("Удалить задачу?")) return;
    try {
      setError(null);
      await api.deleteTask(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка удаления");
    }
  }

  async function linkTelegram() {
    try {
      setError(null);
      const status = await api.createLinkCode();
      setTg(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка привязки");
    }
  }

  async function unlinkTelegram() {
    try {
      setError(null);
      const status = await api.unlinkTelegram();
      setTg(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка отвязки");
    }
  }

  return (
    <>
      <h1>Таск-менеджер</h1>
      <p className="subtitle">Задачи по дате и времени с напоминаниями в Telegram</p>

      {error && <p className="error">{error}</p>}

      <section className="panel">
        <h2>Telegram</h2>
        <div className="telegram-box">
          {tg.linked ? (
            <>
              <p className="status-ok">Бот привязан — напоминания придут в Telegram.</p>
              <div className="actions-row">
                <button type="button" className="btn-ghost" onClick={unlinkTelegram}>
                  Отвязать
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="hint">
                Создайте бота у @BotFather, укажите токен в .env, затем привяжите чат.
              </p>
              {tg.link_code ? (
                <>
                  <p className="hint">Отправьте боту команду (код действует 15 минут):</p>
                  <div className="telegram-code">/link {tg.link_code}</div>
                </>
              ) : (
                <button type="button" className="btn-primary" onClick={linkTelegram}>
                  Привязать Telegram
                </button>
              )}
            </>
          )}
        </div>
      </section>

      <section className="panel">
        <h2>Новая задача</h2>
        <form className="form-grid" onSubmit={handleSubmit}>
          <label>
            Название
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Например: созвон с командой"
              required
            />
          </label>
          <label>
            Дата и время
            <input
              type="datetime-local"
              value={dueAt}
              onChange={(e) => setDueAt(e.target.value)}
              required
            />
          </label>
          <label>
            Заметки (необязательно)
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Детали задачи"
            />
          </label>
          <button type="submit" className="btn-primary">
            Добавить
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>Задачи</h2>
        {tasks.length === 0 ? (
          <p className="empty">Пока нет задач — добавьте первую выше.</p>
        ) : (
          <>
            {groups.overdue.length > 0 && (
              <>
                <p className="section-label">Просрочено</p>
                <ul className="task-list">
                  {groups.overdue.map((t) => (
                    <TaskRow
                      key={t.id}
                      task={t}
                      overdue
                      onToggle={toggleTask}
                      onDelete={deleteTask}
                    />
                  ))}
                </ul>
              </>
            )}
            {groups.active.length > 0 && (
              <>
                <p className="section-label">Предстоящие</p>
                <ul className="task-list">
                  {groups.active.map((t) => (
                    <TaskRow
                      key={t.id}
                      task={t}
                      overdue={false}
                      onToggle={toggleTask}
                      onDelete={deleteTask}
                    />
                  ))}
                </ul>
              </>
            )}
            {groups.done.length > 0 && (
              <>
                <p className="section-label">Выполнено</p>
                <ul className="task-list">
                  {groups.done.map((t) => (
                    <TaskRow
                      key={t.id}
                      task={t}
                      overdue={false}
                      onToggle={toggleTask}
                      onDelete={deleteTask}
                    />
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </section>
    </>
  );
}
