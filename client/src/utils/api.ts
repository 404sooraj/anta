import axios from "axios";
import { API_CONFIG } from "./config";

const api = axios.create({
  baseURL: API_CONFIG.API_ENDPOINT,
});

// Attach auth token from localStorage on every request (client-side only)
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// On 401 or 403, clear auth and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    if (status === 401 || status === 403) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("user_id");
        localStorage.removeItem("user_name");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

/** User data returned by GET /api/user/me (matches server UserResponse). */
export interface MeResponse {
  user_id: string;
  name: string;
  phone_number?: string | null;
  email?: string | null;
}

/**
 * Fetch the current user from the server using the auth token.
 * Token is sent via the api instance (Bearer from localStorage).
 * Use this to verify the token and get user data after login or on load.
 */
export async function getMe(): Promise<MeResponse> {
  const { data } = await api.get<MeResponse>("/api/user/me");
  return data;
}

export default api;
