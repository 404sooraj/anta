const DEFAULT_HTTP_PORT = "8000";

function normalizeBaseUrl(url: string): string {
  return url.replace(/\/$/, "");
}

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const fromEnv = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (fromEnv) {
      return normalizeBaseUrl(fromEnv);
    }
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:${DEFAULT_HTTP_PORT}`;
  }

  return normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000");
}

export function getWsBaseUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_WS_BASE_URL;
  if (fromEnv) {
    return normalizeBaseUrl(fromEnv);
  }
  const httpBase = getApiBaseUrl();
  return httpBase.replace(/^http/, "ws");
}

export function buildApiUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const base = getApiBaseUrl();
  return `${base}${path.startsWith("/") ? "" : "/"}${path}`;
}

export function buildWsUrl(path: string): string {
  if (path.startsWith("ws://") || path.startsWith("wss://")) {
    return path;
  }
  const base = getWsBaseUrl();
  return `${base}${path.startsWith("/") ? "" : "/"}${path}`;
}
