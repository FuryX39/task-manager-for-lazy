import { useMemo } from "react";
import { useTz } from "../TzContext";
import type { AdminUser } from "../types";

interface Props {
  users: AdminUser[];
}

function fmt(iso: string | null, tz: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("ru-RU", {
    timeZone: tz,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AdminPanel({ users }: Props) {
  const tz = useTz();

  const stats = useMemo(() => {
    const total = users.length;
    const tg = users.filter((u) => u.telegram_linked).length;
    const google = users.filter((u) => u.has_google).length;
    return { total, tg, google };
  }, [users]);

  return (
    <div className="settings">
      <section className="panel">
        <h2>Админ-панель</h2>
        <p className="hint">
          Профили пользователей (без задач). Всего: {stats.total}, Telegram: {stats.tg}, Google: {stats.google}
        </p>

        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Имя</th>
                <th>Email</th>
                <th>Admin</th>
                <th>Auth</th>
                <th>Telegram</th>
                <th>Создан</th>
                <th>Последний вход</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td>{u.display_name}</td>
                  <td>{u.email}</td>
                  <td>{u.is_admin ? "Да" : "Нет"}</td>
                  <td>
                    {[u.has_password ? "Пароль" : null, u.has_google ? "Google" : null]
                      .filter(Boolean)
                      .join(" + ") || "—"}
                  </td>
                  <td>{u.telegram_linked ? "Привязан" : "—"}</td>
                  <td>{fmt(u.created_at, tz)}</td>
                  <td>{fmt(u.last_login_at, tz)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

