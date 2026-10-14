import { api } from "./client";
import type { Goal, GoalInput, GoalList, GoalUpdate } from "../types/api";

export async function listGoals(limit = 100, offset = 0): Promise<GoalList> {
  const response = await api.get<GoalList>("/goals", {
    params: { limit, offset },
  });
  return response.data;
}

export async function getGoal(id: number): Promise<Goal> {
  const response = await api.get<Goal>(`/goals/${id}`);
  return response.data;
}

export async function createGoal(input: GoalInput): Promise<Goal> {
  const response = await api.post<Goal>("/goals", input);
  return response.data;
}

export async function updateGoal(id: number, input: GoalUpdate): Promise<Goal> {
  const response = await api.patch<Goal>(`/goals/${id}`, input);
  return response.data;
}

export async function completeGoal(id: number): Promise<Goal> {
  const response = await api.post<Goal>(`/goals/${id}/complete`);
  return response.data;
}

export async function deleteGoal(id: number): Promise<void> {
  await api.delete(`/goals/${id}`);
}
