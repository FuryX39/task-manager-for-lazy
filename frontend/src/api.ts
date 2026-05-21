import type { Task, TelegramStatus } from "./types";

const API = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listTasks: () => request<Task[]>("/tasks"),
  createTask: (body: { title: string; notes: string | null; due_at: string }) =>
    request<Task>("/tasks", { method: "POST", body: JSON.stringify(body) }),
  updateTask: (id: number, body: Partial<{ title: string; notes: string | null; due_at: string; completed: boolean }>) =>
    request<Task>(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteTask: (id: number) =>
    request<void>(`/tasks/${id}`, { method: "DELETE" }),
  telegramStatus: () => request<TelegramStatus>("/telegram/status"),
  createLinkCode: () =>
    request<TelegramStatus>("/telegram/link-code", { method: "POST" }),
  unlinkTelegram: () =>
    request<TelegramStatus>("/telegram/unlink", { method: "POST" }),
};
