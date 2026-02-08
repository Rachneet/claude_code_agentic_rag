import { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"
import { Upload } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

const ACCEPTED_TYPES = {
  "text/plain": [".txt"],
  "text/markdown": [".md"],
  "text/csv": [".csv"],
  "application/json": [".json"],
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/html": [".html", ".htm"],
}

const MAX_SIZE = 10 * 1024 * 1024 // 10MB

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>
  uploading: boolean
}

export function FileUpload({ onUpload, uploading }: FileUploadProps) {
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setError(null)
      if (acceptedFiles.length === 0) return

      try {
        await onUpload(acceptedFiles[0])
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed")
      }
    },
    [onUpload],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    multiple: false,
    disabled: uploading,
    onDropRejected: (rejections) => {
      const rejection = rejections[0]
      if (rejection?.errors[0]?.code === "file-too-large") {
        setError("File too large. Maximum size is 10MB.")
      } else if (rejection?.errors[0]?.code === "file-invalid-type") {
        setError("Unsupported file type. Allowed: .txt, .md, .csv, .json, .pdf, .docx, .html")
      } else {
        setError(rejection?.errors[0]?.message || "File rejected")
      }
    },
  })

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
          isDragActive
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-primary/50"
        } ${uploading ? "pointer-events-none opacity-50" : ""}`}
      >
        <input {...getInputProps()} />
        <Upload className="mb-3 h-8 w-8 text-muted-foreground" />
        {uploading ? (
          <p className="text-sm text-muted-foreground">Uploading...</p>
        ) : isDragActive ? (
          <p className="text-sm text-primary">Drop the file here</p>
        ) : (
          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              Drag and drop a file here, or click to select
            </p>
            <p className="mt-1 text-xs text-muted-foreground/70">
              Supported: .txt, .md, .csv, .json, .pdf, .docx, .html (max 10MB)
            </p>
          </div>
        )}
      </div>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
