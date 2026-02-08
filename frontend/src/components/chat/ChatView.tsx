import { useCallback, useEffect, useRef, useState } from "react"
import { apiFetch, apiStreamChat } from "@/lib/api"
import type { Message } from "@/types"
import { MessageInput } from "./MessageInput"
import { MessageList } from "./MessageList"

interface ChatViewProps {
  threadId: string | null
  onTitleUpdated: () => void
}

type ChatState = "idle" | "sending" | "streaming"

export function ChatView({ threadId, onTitleUpdated }: ChatViewProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [chatState, setChatState] = useState<ChatState>("idle")
  const [streamingContent, setStreamingContent] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const streamingRef = useRef("")

  useEffect(() => {
    if (!threadId) {
      setMessages([])
      return
    }
    loadMessages(threadId)
  }, [threadId])

  async function loadMessages(tid: string, showLoading = true) {
    if (showLoading) setLoadingMessages(true)
    try {
      const res = await apiFetch(`/api/threads/${tid}/messages`)
      const data: Message[] = await res.json()
      setMessages(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load messages")
    } finally {
      setLoadingMessages(false)
    }
  }

  const handleSend = useCallback(
    async (content: string) => {
      if (!threadId || chatState !== "idle") return

      setError(null)
      setChatState("sending")
      streamingRef.current = ""

      // Optimistic user message
      const optimisticMsg: Message = {
        id: `temp-${Date.now()}`,
        thread_id: threadId,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, optimisticMsg])
      setStreamingContent("")

      const isFirstMessage = messages.length === 0

      await apiStreamChat(
        threadId,
        content,
        (token) => {
          setChatState("streaming")
          streamingRef.current += token
          setStreamingContent((prev) => prev + token)
        },
        (messageId) => {
          // Append assistant message directly from streamed content (no re-fetch flash)
          const assistantMsg: Message = {
            id: messageId,
            thread_id: threadId,
            role: "assistant",
            content: streamingRef.current,
            created_at: new Date().toISOString(),
          }
          setMessages((prev) => [...prev, assistantMsg])
          setStreamingContent("")
          setChatState("idle")

          if (isFirstMessage) {
            onTitleUpdated()
          }
        },
        (err) => {
          setChatState("idle")
          setStreamingContent("")
          setError(err)
        },
      )
    },
    [threadId, chatState, messages.length, onTitleUpdated],
  )

  if (!threadId) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground">
        Select or create a thread to start chatting
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col">
      <MessageList
        messages={messages}
        streamingContent={streamingContent}
        isStreaming={chatState !== "idle"}
        loading={loadingMessages}
      />
      {error && (
        <div className="px-4">
          <p className="mx-auto max-w-3xl text-sm text-destructive">{error}</p>
        </div>
      )}
      <MessageInput onSend={handleSend} disabled={chatState !== "idle"} />
    </div>
  )
}
