import { FileText, Trash2, AlertCircle, CheckCircle, Loader2, Clock } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { Document } from "@/types"

interface DocumentListProps {
  documents: Document[]
  onDelete: (id: string) => void
  deleting: string | null
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const PROCESSING_STAGES = ["extracting", "chunking", "embedding"] as const

function StepIndicator({ status }: { status: Document["status"] }) {
  const labels = ["Extract", "Chunk", "Embed"]
  const currentIdx = PROCESSING_STAGES.indexOf(status as typeof PROCESSING_STAGES[number])

  return (
    <div className="flex items-center gap-1 text-xs">
      {PROCESSING_STAGES.map((_, i) => {
        const isDone = i < currentIdx
        const isCurrent = i === currentIdx
        return (
          <span key={i} className="flex items-center gap-0.5">
            {i > 0 && <span className="text-muted-foreground mx-0.5">&rarr;</span>}
            {isDone && <span className="text-green-600 font-medium">&#10003; {labels[i]}</span>}
            {isCurrent && (
              <span className="text-blue-600 font-medium flex items-center gap-0.5">
                <Loader2 className="h-3 w-3 animate-spin" />
                {labels[i]}
              </span>
            )}
            {!isDone && !isCurrent && <span className="text-muted-foreground">{labels[i]}</span>}
          </span>
        )
      })}
    </div>
  )
}

function StatusBadge({ status }: { status: Document["status"] }) {
  if (status === "extracting" || status === "chunking" || status === "embedding") {
    return <StepIndicator status={status} />
  }

  switch (status) {
    case "pending":
      return (
        <Badge variant="secondary" className="gap-1">
          <Clock className="h-3 w-3" />
          Pending
        </Badge>
      )
    case "completed":
      return (
        <Badge variant="secondary" className="gap-1 text-green-600">
          <CheckCircle className="h-3 w-3" />
          Completed
        </Badge>
      )
    case "failed":
      return (
        <Badge variant="destructive" className="gap-1">
          <AlertCircle className="h-3 w-3" />
          Failed
        </Badge>
      )
  }
}

export function DocumentList({ documents, onDelete, deleting }: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <FileText className="mb-3 h-12 w-12 opacity-30" />
        <p className="text-sm">No documents uploaded yet</p>
        <p className="mt-1 text-xs">Upload a file above to get started</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="flex items-center justify-between rounded-lg border p-3"
        >
          <div className="flex items-center gap-3 overflow-hidden">
            <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{doc.filename}</p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{formatFileSize(doc.file_size)}</span>
                {doc.status === "completed" && doc.chunk_count > 0 && (
                  <span>{doc.chunk_count} chunks</span>
                )}
                {doc.status === "failed" && doc.error_message && (
                  <span className="text-destructive" title={doc.error_message}>
                    {doc.error_message.slice(0, 50)}
                    {doc.error_message.length > 50 ? "..." : ""}
                  </span>
                )}
              </div>
              {doc.status === "completed" && doc.metadata && (
                <div className="mt-1 flex flex-wrap gap-1">
                  <Badge variant="outline" className="text-xs">
                    {doc.metadata.document_type}
                  </Badge>
                  {doc.metadata.topics.slice(0, 3).map((topic) => (
                    <Badge key={topic} variant="secondary" className="text-xs">
                      {topic}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <StatusBadge status={doc.status} />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(doc.id)}
              disabled={deleting === doc.id}
              className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
            >
              {deleting === doc.id ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      ))}
    </div>
  )
}
