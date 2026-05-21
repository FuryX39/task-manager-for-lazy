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
