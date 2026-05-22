import { FormEvent, useState } from "react";
import type { User } from "../types";

interface Props {
  user: User;
  onSave: (payload: {
    display_name?: string;
    email?: string;
    current_password?: string;
    new_password?: string;
  }) => Promise<void>;
  onLogout: () => Promise<void>;
  onDeleteAccount: () => Promise<void>;
}

export default function Profile({ user, onSave, onLogout, onDeleteAccount }: Props) {
  const [displayName, setDisplayName] = useState(user.display_name);
  const [email, setEmail] = useState(user.email);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    const payload: {
      display_name?: string;
      email?: string;
      current_password?: string;
      new_password?: string;
    } = {};
    if (displayName.trim() !== user.display_name) payload.display_name = displayName.trim();
    if (email.trim().toLowerCase() !== user.email) payload.email = email.trim();
    if (newPassword) {
      payload.new_password = newPassword;
      if (currentPassword) payload.current_password = currentPassword;
    }
    if (Object.keys(payload).length === 0) {
      setMsg("Изменений нет");
      return;
    }
    try {
      setBusy(true);
      await onSave(payload);
      setCurrentPassword("");
      setNewPassword("");
      setMsg("Профиль обновлен");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="settings">
      <section className="panel">
        <h2>Профиль</h2>
        <p className="hint">Измените имя, email или пароль для входа.</p>
        {err && <p className="error">{err}</p>}
        {msg && <p className="status-ok">{msg}</p>}

        <form className="form-grid" onSubmit={submit}>
          <label>
            Display name
            <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required />
          </label>
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Текущий пароль
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder={user.has_password ? "Нужен для смены пароля" : "Можно оставить пустым"}
            />
          </label>
          <label>
            Новый пароль
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Минимум 8 символов"
            />
          </label>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Сохраняю..." : "Сохранить"}
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>Сессия и аккаунт</h2>
        <div className="actions-row">
          <button type="button" className="btn-ghost" onClick={onLogout}>
            Выйти
          </button>
          <button
            type="button"
            className="btn-danger"
            onClick={() => {
              if (
                confirm(
                  "Удалить аккаунт и все данные (задачи, категории, привязку Telegram)? Это действие необратимо.",
                )
              ) {
                onDeleteAccount();
              }
            }}
          >
            Удалить аккаунт
          </button>
        </div>
      </section>
    </div>
  );
}

