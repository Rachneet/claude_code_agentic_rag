import { useEffect, useRef, useState, type KeyboardEvent } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

interface MessageInputProps {
  onSend: (message: string) => void
  disabled: boolean
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-focus when input becomes enabled (after streaming completes)
  useEffect(() => {
    if (!disabled) {
      textareaRef.current?.focus()
    }
  }, [disabled])

  function handleSend() {
    const trimmed = input.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setInput("")
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t p-4">
      <div className="mx-auto flex max-w-3xl gap-2">
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (Shift+Enter for newline)"
          disabled={disabled}
          rows={1}
          className="min-h-[44px] resize-none"
        />
        <Button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          size="sm"
          className="self-end"
        >
          Send
        </Button>
      </div>
    </div>
  )
}
