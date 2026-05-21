import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import BulkForm from "./components/BulkForm";
import Calendar from "./components/Calendar";
import DayModal from "./components/DayModal";
import Settings from "./components/Settings";
import type { Category, DayMark, Task, TelegramStatus } from "./types";
import { dueDateKey } from "./utils";

type Tab = "calendar" | "bulk" | "settings";

// undefined — режим окраски выключен (клик по дню открывает модалку)
// null — ластик (клик по дню снимает метку)
// number — id категории, которой красим
type PaintMode = number | null | undefined;

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
  const [paintMode, setPaintMode] = useState<PaintMode>(undefined);
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

  useEffect(() => {
    if (paintMode === undefined) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setPaintMode(undefined);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [paintMode]);

  const dayTasks = useMemo(() => {
    if (!selectedDay) return [];
    return tasks.filter((t) => dueDateKey(t.due_at) === selectedDay);
  }, [tasks, selectedDay]);

  const currentDayCategoryId = useMemo(() => {
    if (!selectedDay) return undefined;
    return dayMarks.find((m) => m.day === selectedDay)?.category_id;
  }, [dayMarks, selectedDay]);

  const paintCategory = useMemo(() => {
    if (typeof paintMode !== "number") return null;
    return categories.find((c) => c.id === paintMode) ?? null;
  }, [paintMode, categories]);

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

  function handlePaintDay(dateKey: string) {
    if (paintMode === undefined) return;
    setDayMarks((prev) => {
      const filtered = prev.filter((m) => m.day !== dateKey);
      if (paintMode === null) return filtered;
      return [...filtered, { day: dateKey, category_id: paintMode }];
    });
  }

  async function handlePaintCommit(dateKeys: string[]) {
    if (paintMode === undefined || dateKeys.length === 0) return;
    try {
      await api.bulkSetDayMarks(dateKeys, paintMode);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка окраски");
      await reload();
    }
  }

  function togglePaintMode(value: PaintMode) {
    setPaintMode((prev) => (prev === value ? undefined : value));
  }

  async function handleBulk(
    body: { title: string; notes: string | null; due_ats: string[] },
    dateKeys: string[],
    paintCategoryId: number | null,
  ) {
    const res = await api.bulkCreate(body);
    if (paintCategoryId !== null && dateKeys.length > 0) {
      await api.bulkSetDayMarks(dateKeys, paintCategoryId);
    }
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
    if (paintMode === id) setPaintMode(undefined);
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

  const paintLabel =
    paintMode === undefined
      ? null
      : paintMode === null
        ? "Снятие метки"
        : paintCategory?.name ?? "Окраска";

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
          <>
            {paintMode !== undefined && (
              <div
                className="paint-banner"
                style={
                  paintCategory
                    ? { borderColor: paintCategory.color, background: `${paintCategory.color}22` }
                    : undefined
                }
              >
                <span>
                  Режим окраски: <b>{paintLabel}</b>. Кликайте по дням в календаре.
                </span>
                <button type="button" className="btn-ghost btn-sm" onClick={() => setPaintMode(undefined)}>
                  Выйти (Esc)
                </button>
              </div>
            )}
            <Calendar
              cursor={cursor}
              onChangeCursor={setCursor}
              tasks={tasks}
              categories={categories}
              dayMarks={dayMarks}
              paintActive={paintMode !== undefined}
              onSelectDay={setSelectedDay}
              onPaintDay={handlePaintDay}
              onPaintCommit={handlePaintCommit}
            />
          </>
        )}
        {tab === "bulk" && (
          <BulkForm categories={categories} onSubmit={handleBulk} />
        )}
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
        {categories.map((c) => {
          const active = paintMode === c.id;
          return (
            <button
              type="button"
              key={c.id}
              className={`legend-item ${active ? "active" : ""}`}
              style={
                active
                  ? { borderColor: c.color, background: `${c.color}33` }
                  : { borderColor: `${c.color}44` }
              }
              onClick={() => togglePaintMode(c.id)}
              title={active ? "Выключить окраску" : `Красить дни как «${c.name}»`}
            >
              <span className="dot" style={{ background: c.color }} />
              {c.name}
            </button>
          );
        })}
        {categories.length > 0 && (
          <button
            type="button"
            className={`legend-item eraser ${paintMode === null ? "active" : ""}`}
            onClick={() => togglePaintMode(null)}
            title="Снимать метку с дней"
          >
            <span className="dot dot-eraser" />
            Снять метку
          </button>
        )}
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
