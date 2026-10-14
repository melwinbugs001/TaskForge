import axios from "axios";

export const TOKEN_KEY = "agentforge_access_token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 20_000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item?.msg === "string" ? item.msg : "Invalid input"))
        .join(". ");
    }
    if (!error.response) {
      return "Cannot reach TaskForge API. Make sure the backend is running.";
    }
    return `Request failed (${error.response.status}). Please try again.`;
  }
  return "An unexpected error occurred. Please try again.";
}
