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
