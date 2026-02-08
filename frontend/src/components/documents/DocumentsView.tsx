import { useCallback, useEffect, useMemo, useState } from "react"
import { apiDeleteDocument, apiListDocuments, apiUploadDocument } from "@/lib/api"
import { supabase } from "@/lib/supabase"
import { useAuth } from "@/contexts/AuthContext"
import type { Document } from "@/types"
import { FileUpload } from "./FileUpload"
import { DocumentList } from "./DocumentList"

export function DocumentsView() {
  const { user } = useAuth()
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState<string>("all")

  const uniqueTypes = useMemo(() => {
    const types = new Set<string>()
    for (const doc of documents) {
      if (doc.metadata?.document_type) {
        types.add(doc.metadata.document_type)
      }
    }
    return Array.from(types).sort()
  }, [documents])

  const filteredDocuments = useMemo(() => {
    if (typeFilter === "all") return documents
    return documents.filter((d) => d.metadata?.document_type === typeFilter)
  }, [documents, typeFilter])

  const loadDocuments = useCallback(async () => {
    try {
      const docs = await apiListDocuments()
      setDocuments(docs)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  // Subscribe to Realtime updates for document status changes
  useEffect(() => {
    if (!user) return

    const channel = supabase
      .channel("documents-status")
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "documents",
          filter: `user_id=eq.${user.id}`,
        },
        (payload) => {
          const updated = payload.new as Document
          setDocuments((prev) =>
            prev.map((doc) => (doc.id === updated.id ? updated : doc)),
          )
        },
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [user])

  const handleUpload = useCallback(
    async (file: File) => {
      setUploading(true)
      setError(null)
      try {
        const doc = await apiUploadDocument(file)
        setDocuments((prev) => [doc, ...prev])
      } catch (e) {
        throw e // Let FileUpload component handle the error display
      } finally {
        setUploading(false)
      }
    },
    [],
  )

  const handleDelete = useCallback(async (documentId: string) => {
    setDeleting(documentId)
    try {
      await apiDeleteDocument(documentId)
      setDocuments((prev) => prev.filter((d) => d.id !== documentId))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete document")
    } finally {
      setDeleting(null)
    }
  }, [])

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="mx-auto w-full max-w-3xl flex-1 overflow-auto p-6">
        <div className="mb-6">
          <h2 className="text-lg font-semibold">Documents</h2>
          <p className="text-sm text-muted-foreground">
            Upload documents to enable RAG-powered chat responses
          </p>
        </div>

        <div className="mb-6">
          <FileUpload onUpload={handleUpload} uploading={uploading} />
        </div>

        {error && (
          <p className="mb-4 text-sm text-destructive">{error}</p>
        )}

        {uniqueTypes.length > 0 && (
          <div className="mb-4 flex items-center gap-2">
            <label htmlFor="type-filter" className="text-sm text-muted-foreground">
              Filter by type:
            </label>
            <select
              id="type-filter"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="rounded-md border bg-background px-2 py-1 text-sm"
            >
              <option value="all">All types</option>
              {uniqueTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-muted-foreground">Loading documents...</p>
          </div>
        ) : (
          <DocumentList
            documents={filteredDocuments}
            onDelete={handleDelete}
            deleting={deleting}
          />
        )}
      </div>
    </div>
  )
}
