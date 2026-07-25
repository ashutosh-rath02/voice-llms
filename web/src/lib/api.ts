// Client-side API layer: token storage, authenticated fetch, refresh-on-401.
//
// Tokens live in localStorage for Milestone 1 simplicity. The hardening pass
// (Phase 7) moves refresh tokens to httpOnly cookies; the interface here
// stays the same, which is why every call goes through this one module.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const BASE = `${API_URL}/api/v1`;

const ACCESS_KEY = "voiceai.access";
const REFRESH_KEY = "voiceai.refresh";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

function saveTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export async function login(email: string, password: string): Promise<void> {
  // The backend login endpoint speaks OAuth2 form-encoding (username=email).
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  if (!res.ok) {
    throw new Error(res.status === 401 ? "Incorrect email or password" : "Login failed");
  }
  const data = await res.json();
  saveTokens(data.access_token, data.refresh_token);
}

export async function logout(): Promise<void> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  clearTokens();
  if (refresh) {
    // Best-effort revocation; local state is already cleared either way.
    await fetch(`${BASE}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    }).catch(() => {});
  }
}

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    clearTokens();
    return false;
  }
  const data = await res.json();
  saveTokens(data.access_token, data.refresh_token);
  return true;
}

export class UnauthorizedError extends Error {}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const doFetch = () =>
    fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        ...(init.headers ?? {}),
        Authorization: `Bearer ${getAccessToken()}`,
        ...(init.body ? { "Content-Type": "application/json" } : {}),
      },
    });

  let res = await doFetch();
  if (res.status === 401 && (await tryRefresh())) {
    res = await doFetch(); // one retry with the rotated token
  }
  if (res.status === 401) throw new UnauthorizedError("Session expired");
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return (await res.json()) as T;
}
