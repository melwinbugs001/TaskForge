import { api } from "./client";
import type {
  TaskScheduleInput,
  DiscoverableTeam,
  Team,
  TeamDetail,
  TeamTask,
  TeamTaskBulkInput,
  TeamTaskInput,
  TaskRequestInput,
} from "../types/team";

export async function listTeams(): Promise<Team[]> {
  const response = await api.get<Team[]>("/teams");
  return response.data;
}

export async function createTeam(name: string, is_discoverable: boolean): Promise<Team> {
  const response = await api.post<Team>("/teams", { name, is_discoverable });
  return response.data;
}

export async function discoverTeams(q: string): Promise<DiscoverableTeam[]> {
  const response = await api.get<DiscoverableTeam[]>("/teams/discover", {
    params: { q },
  });
  return response.data;
}

export async function requestToJoin(teamId: number): Promise<void> {
  await api.post(`/teams/${teamId}/join-requests`);
}

export async function reviewJoinRequest(
  teamId: number,
  requestId: number,
  approve: boolean,
): Promise<void> {
  await api.patch(`/teams/${teamId}/join-requests/${requestId}`, { approve });
}

export async function setTeamDiscoverability(
  teamId: number,
  is_discoverable: boolean,
): Promise<Team> {
  const response = await api.patch<Team>(`/teams/${teamId}/discoverability`, {
    is_discoverable,
  });
  return response.data;
}

export async function getTeam(id: number): Promise<TeamDetail> {
  const response = await api.get<TeamDetail>(`/teams/${id}`);
  return response.data;
}

export async function inviteMember(teamId: number, email: string): Promise<void> {
  await api.post(`/teams/${teamId}/invites`, { email });
}

export async function listTeamTasks(teamId: number): Promise<TeamTask[]> {
  const response = await api.get<TeamTask[]>(`/teams/${teamId}/tasks`);
  return response.data;
}

export async function assignTask(teamId: number, task: TeamTaskInput): Promise<TeamTask> {
  const response = await api.post<TeamTask>(`/teams/${teamId}/tasks`, task);
  return response.data;
}

export async function assignTaskToWorkers(
  teamId: number,
  task: TeamTaskBulkInput,
): Promise<TeamTask> {
  const response = await api.post<TeamTask>(`/teams/${teamId}/tasks/bulk`, task);
  return response.data;
}

export async function requestTask(teamId: number, task: TaskRequestInput): Promise<TeamTask> {
  const response = await api.post<TeamTask>(`/teams/${teamId}/task-requests`, task);
  return response.data;
}

export async function reviewTaskRequest(
  taskId: number,
  approved: boolean,
  comment?: string,
): Promise<TeamTask> {
  const response = await api.post<TeamTask>(`/tasks/${taskId}/approval`, {
    approved,
    comment,
  });
  return response.data;
}

export async function updateDeclinedTaskRequest(
  taskId: number,
  task: TaskRequestInput,
): Promise<TeamTask> {
  const response = await api.patch<TeamTask>(`/tasks/${taskId}/request`, task);
  return response.data;
}

export async function updateTaskSchedule(
  taskId: number,
  schedule: TaskScheduleInput,
): Promise<TeamTask> {
  const response = await api.patch<TeamTask>(`/tasks/${taskId}/schedule`, schedule);
  return response.data;
}

export async function submitTask(taskId: number): Promise<TeamTask> {
  const response = await api.post<TeamTask>(`/tasks/${taskId}/submit`);
  return response.data;
}

export async function reviewTask(
  taskId: number,
  assignee_id: number,
  approved: boolean,
  comment?: string,
): Promise<TeamTask> {
  const response = await api.post<TeamTask>(`/tasks/${taskId}/review`, {
    assignee_id,
    approved,
    comment,
  });
  return response.data;
}
