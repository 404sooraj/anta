const rawBase =
  typeof process.env.NEXT_PUBLIC_API_ENDPOINT === "string" &&
  process.env.NEXT_PUBLIC_API_ENDPOINT.trim() !== ""
    ? process.env.NEXT_PUBLIC_API_ENDPOINT.trim()
    : "http://localhost:8000";

/** API base URL (no trailing slash). Use getApiUrl(path) for full URLs. */
export const API_CONFIG = {
  API_BASE: rawBase.replace(/\/$/, ""),
  getApiUrl(path: string) {
    const p = path.startsWith("/") ? path : `/${path}`;
    return `${API_CONFIG.API_BASE}${p}`;
  },
};