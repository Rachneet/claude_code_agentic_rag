import { Button } from "@/components/ui/button"
import { useAuth } from "@/contexts/AuthContext"
import type { AppView } from "@/types"

interface HeaderProps {
  activeView?: AppView
  onViewChange?: (view: AppView) => void
}

export function Header({ activeView = "chat", onViewChange }: HeaderProps) {
  const { signOut, user } = useAuth()

  return (
    <header className="flex h-14 items-center justify-between border-b px-4">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold">RAG Masterclass</h1>
        {onViewChange && (
          <div className="flex items-center gap-1 rounded-lg bg-muted p-1">
            <Button
              variant={activeView === "chat" ? "default" : "ghost"}
              size="sm"
              className="h-7 px-3 text-xs"
              onClick={() => onViewChange("chat")}
            >
              Chat
            </Button>
            <Button
              variant={activeView === "documents" ? "default" : "ghost"}
              size="sm"
              className="h-7 px-3 text-xs"
              onClick={() => onViewChange("documents")}
            >
              Documents
            </Button>
          </div>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">{user?.email}</span>
        <Button variant="outline" size="sm" onClick={signOut}>
          Sign out
        </Button>
      </div>
    </header>
  )
}
