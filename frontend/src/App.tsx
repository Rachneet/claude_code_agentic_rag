import { useCallback, useState } from "react"
import { AuthProvider, useAuth } from "@/contexts/AuthContext"
import { AuthPage } from "@/components/auth/AuthPage"
import { AppLayout } from "@/components/layout/AppLayout"
import { ThreadSidebar } from "@/components/chat/ThreadSidebar"
import { ChatView } from "@/components/chat/ChatView"
import type { Thread } from "@/types"

function AppContent() {
  const { user, loading } = useAuth()
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const handleThreadCreated = useCallback((thread: Thread) => {
    setSelectedThreadId(thread.id)
  }, [])

  const handleThreadDeleted = useCallback(
    (threadId: string) => {
      if (selectedThreadId === threadId) {
        setSelectedThreadId(null)
      }
    },
    [selectedThreadId],
  )

  const handleTitleUpdated = useCallback(() => {
    setRefreshKey((k) => k + 1)
  }, [])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    )
  }

  if (!user) {
    return <AuthPage />
  }

  return (
    <AppLayout>
      <ThreadSidebar
        activeThreadId={selectedThreadId}
        onSelectThread={setSelectedThreadId}
        onThreadCreated={handleThreadCreated}
        onThreadDeleted={handleThreadDeleted}
        refreshKey={refreshKey}
      />
      <ChatView
        threadId={selectedThreadId}
        onTitleUpdated={handleTitleUpdated}
      />
    </AppLayout>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
