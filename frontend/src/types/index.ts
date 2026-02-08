export interface Thread {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  thread_id: string
  role: "user" | "assistant"
  content: string
  created_at: string
}

export type AppView = "chat" | "documents"

export interface DocumentMetadata {
  title: string
  document_type: "article" | "report" | "tutorial" | "notes" | "email" | "code" | "data" | "other"
  topics: string[]
  entities: string[]
  language: string
  summary: string
}

export interface Document {
  id: string
  filename: string
  file_size: number
  mime_type: string
  status: "pending" | "extracting" | "chunking" | "embedding" | "completed" | "failed"
  chunk_count: number
  storage_path: string | null
  error_message: string | null
  metadata: DocumentMetadata | null
  created_at: string
  updated_at: string
}
