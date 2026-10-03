const isLocal = typeof window !== "undefined" &&
  (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");

export const API_BASE_URL: string =
  (import.meta as any).env?.VITE_API_BASE_URL ||
  (isLocal ? "http://localhost:8000/api/v1" : "");

export const getWebSocketUrl = (): string => {
  if ((import.meta as any).env?.VITE_WS_URL) {
    return (import.meta as any).env.VITE_WS_URL;
  }
  // Derive WebSocket URL from API_BASE_URL if available
  if (API_BASE_URL) {
    return API_BASE_URL
      .replace(/^https:\/\//, "wss://")
      .replace(/^http:\/\//, "ws://")
      .replace(/\/api\/v1$/, "/api/v1/events/ws");
  }
  if (isLocal) return "ws://localhost:8000/api/v1/events/ws";
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/api/v1/events/ws`;
};


let activeToken: string | null = null;

export const setAuthToken = (token: string | null) => {
  activeToken = token;
  if (token) {
    localStorage.setItem("upay_token", token);
  } else {
    localStorage.removeItem("upay_token");
  }
};

export const getStoredToken = (): string | null => {
  if (!activeToken) {
    activeToken = localStorage.getItem("upay_token");
  }
  return activeToken;
};

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data?.error?.message || data?.detail || "An unexpected error occurred.";
    const err = new Error(errorMsg) as any;
    err.status = response.status;
    err.code = data?.error?.code;
    err.details = data?.error?.details;
    throw err;
  }

  return data as T;
}
