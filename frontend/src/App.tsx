import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import BulkForm from "./components/BulkForm";
import Calendar from "./components/Calendar";
import DayModal from "./components/DayModal";
import Settings from "./components/Settings";
import type { Category, DayMark, Task, TelegramStatus } from "./types";
import { dueDateKey } from "./utils";

type Tab = "calendar" | "bulk" | "settings";

export default function App() {
  const [tab, setTab] = useState<Tab>("calendar");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [dayMarks, setDayMarks] = useState<DayMark[]>([]);
  const [telegram, setTelegram] = useState<TelegramStatus>({ linked: false, link_code: null });
  const [cursor, setCursor] = useState<Date>(() => {
    const d = new Date();
    d.setDate(1);
    return d;
  });
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setError(null);
      const [t, c, m, tg] = await Promise.all([
        api.listTasks(),
        api.listCategories(),
        api.listDayMarks(),
        api.telegramStatus(),
      ]);
      setTasks(t);
      setCategories(c);
      setDayMarks(m);
      setTelegram(tg);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    }
  }, []);

  useEffect(() => {
    reload();
    const id = setInterval(reload, 60_000);
    return () => clearInterval(id);
  }, [reload]);

  const dayTasks = useMemo(() => {
    if (!selectedDay) return [];
    return tasks.filter((t) => dueDateKey(t.due_at) === selectedDay);
  }, [tasks, selectedDay]);

  const currentDayCategoryId = useMemo(() => {
    if (!selectedDay) return undefined;
    return dayMarks.find((m) => m.day === selectedDay)?.category_id;
  }, [dayMarks, selectedDay]);

  async function handleAddTask(title: string, notes: string | null, dueIso: string) {
    await api.createTask({ title, notes, due_at: dueIso });
    await reload();
  }

  async function handleToggleTask(t: Task) {
    await api.updateTask(t.id, { completed: !t.completed });
    await reload();
  }

  async function handleDeleteTask(id: number) {
    await api.deleteTask(id);
    await reload();
  }

  async function handleSetCategory(categoryId: number | null) {
    if (!selectedDay) return;
    await api.setDayMark(selectedDay, categoryId);
    await reload();
  }

  async function handleBulk(body: { title: string; notes: string | null; due_ats: string[] }) {
    const res = await api.bulkCreate(body);
    await reload();
    return res.created;
  }

  async function handleCreateCategory(name: string, color: string) {
    const order = categories.length === 0 ? 10 : Math.max(...categories.map((c) => c.sort_order)) + 10;
    await api.createCategory({ name, color, sort_order: order });
    await reload();
  }

  async function handleUpdateCategory(
    id: number,
    patch: Partial<{ name: string; color: string }>,
  ) {
    await api.updateCategory(id, patch);
    await reload();
  }

  async function handleDeleteCategory(id: number) {
    await api.deleteCategory(id);
    await reload();
  }

  async function handleLinkTelegram() {
    const status = await api.createLinkCode();
    setTelegram(status);
  }

  async function handleUnlinkTelegram() {
    const status = await api.unlinkTelegram();
    setTelegram(status);
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Таск-менеджер</h1>
          <p className="subtitle">Календарь, цветные метки дней и напоминания в Telegram</p>
        </div>
        <nav className="tabs">
          <button
            type="button"
            className={`tab ${tab === "calendar" ? "active" : ""}`}
            onClick={() => setTab("calendar")}
          >
            Календарь
          </button>
          <button
            type="button"
            className={`tab ${tab === "bulk" ? "active" : ""}`}
            onClick={() => setTab("bulk")}
          >
            Массовое добавление
          </button>
          <button
            type="button"
            className={`tab ${tab === "settings" ? "active" : ""}`}
            onClick={() => setTab("settings")}
          >
            Настройки
          </button>
        </nav>
      </header>

      {error && <p className="error">{error}</p>}

      <main className="app-main">
        {tab === "calendar" && (
          <Calendar
            cursor={cursor}
            onChangeCursor={setCursor}
            tasks={tasks}
            categories={categories}
            dayMarks={dayMarks}
            onSelectDay={setSelectedDay}
          />
        )}
        {tab === "bulk" && <BulkForm onSubmit={handleBulk} />}
        {tab === "settings" && (
          <Settings
            categories={categories}
            telegram={telegram}
            onCreateCategory={handleCreateCategory}
            onUpdateCategory={handleUpdateCategory}
            onDeleteCategory={handleDeleteCategory}
            onLinkTelegram={handleLinkTelegram}
            onUnlinkTelegram={handleUnlinkTelegram}
          />
        )}
      </main>

      <footer className="legend">
        <span className="legend-title">Легенда:</span>
        {categories.length === 0 && <span className="hint">нет категорий</span>}
        {categories.map((c) => (
          <span key={c.id} className="legend-item">
            <span className="dot" style={{ background: c.color }} />
            {c.name}
          </span>
        ))}
      </footer>

      {selectedDay && (
        <DayModal
          dateKey={selectedDay}
          tasks={dayTasks}
          categories={categories}
          currentCategoryId={currentDayCategoryId}
          onClose={() => setSelectedDay(null)}
          onAddTask={handleAddTask}
          onToggleTask={handleToggleTask}
          onDeleteTask={handleDeleteTask}
          onSetCategory={handleSetCategory}
        />
      )}
    </div>
  );
}
