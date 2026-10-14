export type TeamRole = "leader" | "worker";
export type TeamTaskStatus =
  | "pending_approval"
  | "assigned"
  | "submitted"
  | "completed"
  | "declined";

export interface Team {
  id: number;
  name: string;
  is_discoverable: boolean;
  leader_id: number;
  created_at: string;
  role: TeamRole;
  member_count: number;
  pending_invite_count: number;
}

export interface TeamMember {
  user_id: number;
  email: string;
  role: TeamRole;
  joined_at: string;
}

export interface TeamInvite {
  email: string;
  created_at: string;
  accepted: boolean;
}

export interface TeamDetail extends Team {
  members: TeamMember[];
  invites: TeamInvite[];
  join_requests: TeamJoinRequest[];
}

export interface TeamJoinRequest {
  id: number;
  team_id: number;
  user_id: number;
  email: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
}

export interface DiscoverableTeam {
  id: number;
  name: string;
  member_count: number;
  request_status: TeamJoinRequest["status"] | null;
}

export interface TeamTask {
  id: number;
  team_id: number;
  title: string;
  description: string;
  assignee_id: number;
  assigned_by: number;
  requested_by: number | null;
  assignee_email?: string;
  start_at: string;
  deadline_at: string;
  status: TeamTaskStatus;
  submitted_at: string | null;
  completed_at: string | null;
  review_comment: string | null;
  assignments: TeamTaskAssignment[];
  current_assignment: TeamTaskAssignment | null;
  created_at: string;
  updated_at: string;
}

export interface TeamTaskAssignment {
  user_id: number;
  email: string;
  status: TeamTaskStatus;
  submitted_at: string | null;
  completed_at: string | null;
  review_comment: string | null;
}

export interface TeamTaskInput {
  title: string;
  description: string;
  assignee_id: number;
  start_at: string;
  deadline_at: string;
}

export interface TeamTaskBulkInput {
  title: string;
  description: string;
  assignee_ids: number[];
  start_at: string;
  deadline_at: string;
}

export interface TaskRequestInput {
  title: string;
  description: string;
  start_at: string;
  deadline_at: string;
}

export interface TaskScheduleInput {
  start_at: string;
  deadline_at: string;
}
