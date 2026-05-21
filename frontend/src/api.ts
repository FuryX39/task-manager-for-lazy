import type { BulkResult, Category, DayMark, Task, TelegramStatus } from "./types";

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
  updateTask: (
    id: number,
    body: Partial<{ title: string; notes: string | null; due_at: string; completed: boolean }>,
  ) => request<Task>(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteTask: (id: number) => request<void>(`/tasks/${id}`, { method: "DELETE" }),
  bulkCreate: (body: { title: string; notes: string | null; due_ats: string[] }) =>
    request<BulkResult>("/tasks/bulk", { method: "POST", body: JSON.stringify(body) }),

  listCategories: () => request<Category[]>("/categories"),
  createCategory: (body: { name: string; color: string; sort_order: number }) =>
    request<Category>("/categories", { method: "POST", body: JSON.stringify(body) }),
  updateCategory: (
    id: number,
    body: Partial<{ name: string; color: string; sort_order: number }>,
  ) => request<Category>(`/categories/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteCategory: (id: number) =>
    request<void>(`/categories/${id}`, { method: "DELETE" }),

  listDayMarks: () => request<DayMark[]>("/day-marks"),
  setDayMark: (day: string, category_id: number | null) =>
    request<DayMark | null>(`/day-marks/${day}`, {
      method: "PUT",
      body: JSON.stringify({ category_id }),
    }),

  telegramStatus: () => request<TelegramStatus>("/telegram/status"),
  createLinkCode: () =>
    request<TelegramStatus>("/telegram/link-code", { method: "POST" }),
  unlinkTelegram: () =>
    request<TelegramStatus>("/telegram/unlink", { method: "POST" }),
};
