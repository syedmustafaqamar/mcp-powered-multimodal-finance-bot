import type { Answer, TaskState, User } from './types'

const BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const tokenKey = 'finsight_token'

export function getToken() { return localStorage.getItem(tokenKey) }
export function saveToken(token: string | null) {
  if (token) localStorage.setItem(tokenKey, token)
  else localStorage.removeItem(tokenKey)
}
async function request<T>(path: string, init: RequestInit = {}, auth = true): Promise<T> {
  const headers = new Headers(init.headers)
  if (
  init.body &&
  !(init.body instanceof FormData) &&
  !(init.body instanceof URLSearchParams) &&
  !headers.has('Content-Type')
) {
  headers.set('Content-Type', 'application/json')
}
  const token = getToken()
  if (auth && token) headers.set('Authorization', `Bearer ${token}`)
  let response: Response
  try { response = await fetch(`${BASE}${path}`, { ...init, headers }) }
  catch { throw new Error(`Cannot reach the API at ${BASE}. Start the FastAPI backend and check VITE_API_BASE_URL.`) }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try { const body = await response.json(); detail = typeof body.detail === 'string' ? body.detail : detail } catch { /* non-JSON error */ }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}
export const api = {
  async login(username: string, password: string) {
    const body = new URLSearchParams({ username, password })
    const data = await request<{access_token: string; user: User}>('/user/login', { method: 'POST', body }, false)
    saveToken(data.access_token); return data.user
  },
  async register(username: string, email: string, password: string) {
    return request<User>('/user/register', { method: 'POST', body: JSON.stringify({ username, email, password }) }, false)
  },
  me: () => request<User>('/user/me'),
  health: () => request<{status: string}>('/health', {}, false),
  ask: (query: string, top_k: number) => request<TaskState>('/ask', { method: 'POST', body: JSON.stringify({ query, top_k }) }),
  search: (query: string, top_k: number) => request<TaskState>('/search', { method: 'POST', body: JSON.stringify({ query, top_k }) }),
  task: (id: string) => request<TaskState>(`/tasks/${encodeURIComponent(id)}`),
  upload: (file: File) => {
    const body = new FormData(); body.append('file', file)
    return request<TaskState & {filename?: string}>('/ingest_document', { method: 'POST', body })
  }
}
export async function pollTask(taskId: string, onStatus?: (status: string) => void, timeoutMs = 600000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    const task = await api.task(taskId)
    onStatus?.(task.status)
    if (['SUCCESS', 'FAILURE', 'REVOKED'].includes(task.status.toUpperCase())) {
      if (task.status.toUpperCase() !== 'SUCCESS') throw new Error(task.error || `Task ${task.status.toLowerCase()}`)
      return task.result
    }
    await new Promise(resolve => setTimeout(resolve, 1800))
  }
  throw new Error('This task is taking longer than expected. Check the worker logs and try again.')
}
export function asAnswer(value: unknown): Answer {
  if (value && typeof value === 'object') return value as Answer
  return { answer: typeof value === 'string' ? value : JSON.stringify(value, null, 2) }
}
