import { FileText, Image, LoaderCircle, X } from 'lucide-react'
import type { Attachment } from '../../types/api'

interface Props {
  attachment: Attachment
  onRemove: (attachment: Attachment) => void
}

export function AttachmentPreview({ attachment, onRemove }: Props) {
  const isImage = attachment.content_type.startsWith('image/')
  const status = attachment.uploading
    ? 'Processing locally…'
    : attachment.extraction_status === 'no_text_detected'
      ? 'No readable text found'
      : attachment.extraction_status === 'ocr_unavailable'
        ? 'OCR unavailable'
        : isImage
          ? 'OCR ready'
          : 'Ready'
  return (
    <div className="group flex max-w-56 items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2">
      {attachment.uploading ? (
        <LoaderCircle className="h-4 w-4 shrink-0 animate-spin text-cyan-300" />
      ) : isImage ? (
        <Image className="h-4 w-4 shrink-0 text-cyan-300" />
      ) : (
        <FileText className="h-4 w-4 shrink-0 text-cyan-300" />
      )}
      <div className="min-w-0 flex-1">
        <div className="truncate text-xs font-medium text-slate-200">{attachment.filename}</div>
        <div className="text-[10px] text-slate-500">
          {attachment.uploading ? status : `${status} · ${Math.max(1, Math.round(attachment.size_bytes / 1024))} KB`}
        </div>
      </div>
      {!attachment.uploading && (
        <button
          type="button"
          onClick={() => onRemove(attachment)}
          className="rounded-md p-1 text-slate-500 transition hover:bg-white/10 hover:text-white"
          aria-label={`Remove ${attachment.filename}`}
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  )
}
