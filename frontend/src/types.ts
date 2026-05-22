export interface Task {
  id: number;
  title: string;
  notes: string | null;
  due_at: string;
  completed: boolean;
  reminder_sent: boolean;
  created_at: string;
}

export interface TelegramStatus {
  linked: boolean;
  link_code: string | null;
}

export interface Category {
  id: number;
  name: string;
  color: string;
  sort_order: number;
}

export interface DayMark {
  day: string; // YYYY-MM-DD
  category_id: number;
}

export interface BulkResult {
  created: number;
  tasks: Task[];
}

export interface AppConfig {
  timezone: string;
  reminder_repeat_minutes: number;
  snooze_minutes: number;
}

export interface User {
  id: number;
  email: string;
  display_name: string;
  has_password: boolean;
  has_google: boolean;
  telegram_linked: boolean;
  is_admin: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface AdminUser {
  id: number;
  email: string;
  display_name: string;
  is_admin: boolean;
  has_password: boolean;
  has_google: boolean;
  telegram_linked: boolean;
  created_at: string;
  last_login_at: string | null;
}
