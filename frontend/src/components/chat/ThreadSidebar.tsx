import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { apiFetch } from "@/lib/api"
import type { Thread } from "@/types"

interface ThreadSidebarProps {
  activeThreadId: string | null
  onSelectThread: (threadId: string) => void
  onThreadCreated: (thread: Thread) => void
  onThreadDeleted: (threadId: string) => void
  refreshKey: number
}

export function ThreadSidebar({
  activeThreadId,
  onSelectThread,
  onThreadCreated,
  onThreadDeleted,
  refreshKey,
}: ThreadSidebarProps) {
  const [threads, setThreads] = useState<Thread[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchThreads()
  }, [refreshKey])

  async function fetchThreads() {
    try {
      const res = await apiFetch("/api/threads")
      const data = await res.json()
      setThreads(data)
    } catch (err) {
      console.error("Failed to fetch threads:", err)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateThread() {
    try {
      const res = await apiFetch("/api/threads", {
        method: "POST",
        body: JSON.stringify({ title: "New Chat" }),
      })
      const thread: Thread = await res.json()
      setThreads((prev) => [thread, ...prev])
      onThreadCreated(thread)
    } catch (err) {
      console.error("Failed to create thread:", err)
    }
  }

  async function handleDeleteThread(threadId: string, e: React.MouseEvent) {
    e.stopPropagation()
    try {
      await apiFetch(`/api/threads/${threadId}`, { method: "DELETE" })
      setThreads((prev) => prev.filter((t) => t.id !== threadId))
      onThreadDeleted(threadId)
    } catch (err) {
      console.error("Failed to delete thread:", err)
    }
  }

  return (
    <div className="flex w-72 flex-col border-r bg-muted/30">
      <div className="p-3">
        <Button onClick={handleCreateThread} className="w-full" size="sm">
          + New Chat
        </Button>
      </div>
      <ScrollArea className="flex-1">
        {loading ? (
          <div className="px-3 py-2 text-sm text-muted-foreground">
            Loading...
          </div>
        ) : threads.length === 0 ? (
          <div className="px-3 py-2 text-sm text-muted-foreground">
            No conversations yet
          </div>
        ) : (
          <div className="space-y-1 px-2">
            {threads.map((thread) => (
              <div
                key={thread.id}
                onClick={() => onSelectThread(thread.id)}
                className={`group flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-sm transition-colors hover:bg-accent ${
                  activeThreadId === thread.id
                    ? "bg-accent text-accent-foreground"
                    : ""
                }`}
              >
                <span className="truncate">{thread.title}</span>
                <button
                  onClick={(e) => handleDeleteThread(thread.id, e)}
                  className="ml-2 shrink-0 opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                  aria-label="Delete thread"
                >
                  &times;
                </button>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
