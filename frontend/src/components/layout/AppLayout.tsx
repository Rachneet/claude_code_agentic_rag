import type { ReactNode } from "react"
import { Header } from "./Header"
import type { AppView } from "@/types"

interface AppLayoutProps {
  children: ReactNode
  activeView?: AppView
  onViewChange?: (view: AppView) => void
}

export function AppLayout({ children, activeView, onViewChange }: AppLayoutProps) {
  return (
    <div className="flex h-screen flex-col">
      <Header activeView={activeView} onViewChange={onViewChange} />
      <div className="flex flex-1 overflow-hidden">{children}</div>
    </div>
  )
}
