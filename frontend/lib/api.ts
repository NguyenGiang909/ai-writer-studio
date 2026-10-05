export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request(path: string, init?: RequestInit) {
  const r = await fetch(`${API}${path}`, { cache: "no-store", ...init });
  if (!r.ok) {
    let detail = `API ${r.status}`;
    try {
      const body = await r.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new ApiError(r.status, detail);
  }
  return r.json();
}

export function getJSON(path: string) {
  return request(path);
}
export function postJSON(path: string, body?: unknown, signal?: AbortSignal) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
}
export function patchJSON(path: string, body: unknown) {
  return request(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
export function delJSON(path: string) {
  return request(path, { method: "DELETE" });
}
