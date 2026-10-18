export type User = { id?: number; username: string; email?: string; role?: string }
export type TaskState = { task_id: string; status: string; result?: unknown; error?: string }
export type Answer = {
  query?: string; answer?: string; agent?: string; sources?: Array<Record<string, unknown>>;
  database_rows?: Array<Record<string, unknown>>; tools_used?: string[]; [key: string]: unknown
}
