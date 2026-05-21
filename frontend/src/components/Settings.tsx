import { FormEvent, useState } from "react";
import type { Category, TelegramStatus } from "../types";

interface Props {
  categories: Category[];
  telegram: TelegramStatus;
  onCreateCategory: (name: string, color: string) => Promise<void>;
  onUpdateCategory: (id: number, patch: Partial<{ name: string; color: string }>) => Promise<void>;
  onDeleteCategory: (id: number) => Promise<void>;
  onLinkTelegram: () => Promise<void>;
  onUnlinkTelegram: () => Promise<void>;
}

export default function Settings({
  categories,
  telegram,
  onCreateCategory,
  onUpdateCategory,
  onDeleteCategory,
  onLinkTelegram,
  onUnlinkTelegram,
}: Props) {
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState("#3d8bfd");
  const [err, setErr] = useState<string | null>(null);

  async function add(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      setErr(null);
      await onCreateCategory(newName.trim(), newColor);
      setNewName("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка");
    }
  }

  return (
    <div className="settings">
      <section className="panel">
        <h2>Категории дней</h2>
        <p className="hint">Цветные метки для календаря: рабочий день, учёба, выходной и т.д.</p>
        {err && <p className="error">{err}</p>}

        <ul className="category-list">
          {categories.map((c) => (
            <li key={c.id} className="category-row">
              <input
                type="color"
                value={c.color}
                onChange={(e) => onUpdateCategory(c.id, { color: e.target.value })}
                title="Цвет"
              />
              <input
                type="text"
                value={c.name}
                onChange={(e) => onUpdateCategory(c.id, { name: e.target.value })}
              />
              <button
                type="button"
                className="btn-danger btn-sm"
                onClick={() => {
                  if (confirm(`Удалить категорию «${c.name}»? Метки дней с ней пропадут.`)) {
                    onDeleteCategory(c.id);
                  }
                }}
              >
                Удалить
              </button>
            </li>
          ))}
        </ul>

        <form className="form-grid-row category-add" onSubmit={add}>
          <input
            type="color"
            value={newColor}
            onChange={(e) => setNewColor(e.target.value)}
          />
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Новая категория"
            className="grow"
          />
          <button type="submit" className="btn-primary btn-sm">
            Добавить
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>Telegram</h2>
        <div className="telegram-box">
          {telegram.linked ? (
            <>
              <p className="status-ok">Бот привязан — напоминания приходят в Telegram.</p>
              <div className="actions-row">
                <button type="button" className="btn-ghost" onClick={onUnlinkTelegram}>
                  Отвязать
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="hint">Создайте бота у @BotFather и укажите токен в .env на сервере.</p>
              {telegram.link_code ? (
                <>
                  <p className="hint">Отправьте боту команду (код 15 минут):</p>
                  <div className="telegram-code">/link {telegram.link_code}</div>
                </>
              ) : (
                <button type="button" className="btn-primary" onClick={onLinkTelegram}>
                  Привязать Telegram
                </button>
              )}
            </>
          )}
        </div>
      </section>
    </div>
  );
}
