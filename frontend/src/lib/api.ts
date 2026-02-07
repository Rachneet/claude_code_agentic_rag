import { supabase } from "./supabase"

const API_URL = import.meta.env.VITE_API_URL

async function getAccessToken(): Promise<string> {
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (session?.access_token) return session.access_token

  // Fallback: try refreshing the session
  const { data: refreshed } = await supabase.auth.refreshSession()
  if (refreshed.session?.access_token) return refreshed.session.access_token

  throw new Error("Not authenticated")
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = await getAccessToken()

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
    ...options.headers,
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response
}

export async function apiStreamChat(
  threadId: string,
  message: string,
  onToken: (content: string) => void,
  onDone: (messageId: string) => void,
  onError: (error: string) => void,
) {
  let token: string
  try {
    token = await getAccessToken()
  } catch {
    onError("Not authenticated")
    return
  }

  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ thread_id: threadId, message }),
  })

  if (!response.ok) {
    const err = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }))
    onError(err.detail || `HTTP ${response.status}`)
    return
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split("\n")
    buffer = lines.pop() || ""

    let currentEvent = ""
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7)
      } else if (line.startsWith("data: ")) {
        const data = JSON.parse(line.slice(6))
        if (currentEvent === "token") onToken(data.content)
        else if (currentEvent === "done") onDone(data.message_id)
        else if (currentEvent === "error") onError(data.detail)
      }
    }
  }
}
