import { api } from "./client";
import type { AuthToken, User } from "../types/api";

export interface Credentials {
  email: string;
  password: string;
}

export async function register(credentials: Credentials): Promise<User> {
  const response = await api.post<User>("/auth/register", credentials);
  return response.data;
}

export async function login(credentials: Credentials): Promise<AuthToken> {
  const response = await api.post<AuthToken>("/auth/login", credentials);
  return response.data;
}

export async function getMe(): Promise<User> {
  const response = await api.get<User>("/auth/me");
  return response.data;
}
