export type GoalStatus =
  | "draft"
  | "running"
  | "waiting_for_approval"
  | "completed"
  | "failed"
  | "cancelled";

export interface User {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Goal {
  id: number;
  user_id: number;
  title: string;
  description: string;
  status: GoalStatus;
  final_report: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  due_at: string | null;
}

export interface GoalList {
  items: Goal[];
  total: number;
  limit: number;
  offset: number;
}

export interface GoalInput {
  title: string;
  description: string;
  due_at?: string | null;
}

export interface GoalUpdate {
  title?: string;
  description?: string;
  due_at?: string | null;
}
