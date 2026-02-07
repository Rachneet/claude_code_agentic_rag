import type { ReactNode } from "react"
import { Header } from "./Header"

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen flex-col">
      <Header />
      <div className="flex flex-1 overflow-hidden">{children}</div>
    </div>
  )
}
