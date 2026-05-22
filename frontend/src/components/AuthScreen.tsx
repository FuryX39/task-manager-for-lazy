import { FormEvent, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { User } from "../types";

declare global {
  interface Window {
    google?: any;
  }
}

interface Props {
  onAuth: (u: User) => void;
}

function ensureGoogleScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      "script[src='https://accounts.google.com/gsi/client']",
    );
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Google SDK load failed")), {
        once: true,
      });
      return;
    }
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Google SDK load failed"));
    document.head.appendChild(s);
  });
}

export default function AuthScreen({ onAuth }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const googleRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const clientId = (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID as string | undefined;
    if (!clientId || !googleRef.current) return;
    let cancelled = false;
    ensureGoogleScript()
      .then(() => {
        if (cancelled || !window.google?.accounts?.id) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (resp: { credential: string }) => {
            try {
              const user = await api.loginGoogle(resp.credential);
              onAuth(user);
            } catch (e) {
              setErr(e instanceof Error ? e.message : "Не удалось войти через Google");
            }
          },
        });
        window.google.accounts.id.renderButton(googleRef.current, {
          type: "standard",
          shape: "rectangular",
          size: "large",
          width: 300,
          text: "continue_with",
        });
      })
      .catch(() => {
        setErr("Не удалось загрузить Google login");
      });
    return () => {
      cancelled = true;
    };
  }, [onAuth]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      if (mode === "login") {
        const user = await api.login({ email, password });
        onAuth(user);
      } else {
        const user = await api.register({
          email,
          display_name: displayName.trim(),
          password,
        });
        onAuth(user);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка авторизации");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="panel auth-panel">
        <h2>{mode === "login" ? "Вход" : "Регистрация"}</h2>
        <p className="hint">У каждого пользователя свой календарь, задачи и Telegram-привязка.</p>
        {err && <p className="error">{err}</p>}

        <form className="form-grid" onSubmit={submit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          {mode === "register" && (
            <label>
              Display name
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
            </label>
          )}
          <label>
            Пароль
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? "..." : mode === "login" ? "Войти" : "Создать аккаунт"}
          </button>
        </form>

        <div className="auth-divider">или</div>
        <div ref={googleRef} />

        <div className="actions-row">
          {mode === "login" ? (
            <button type="button" className="btn-ghost btn-sm" onClick={() => setMode("register")}>
              Нет аккаунта? Зарегистрироваться
            </button>
          ) : (
            <button type="button" className="btn-ghost btn-sm" onClick={() => setMode("login")}>
              Уже есть аккаунт? Войти
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

