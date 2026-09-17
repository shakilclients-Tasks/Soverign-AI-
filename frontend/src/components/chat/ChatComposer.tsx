import { ArrowUp, Paperclip, Square } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { Attachment } from '../../types/api'
import { AttachmentPreview } from './AttachmentPreview'

interface Props {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  onStop: () => void
  onFiles: (files: File[]) => void
  onRemoveAttachment: (attachment: Attachment) => void
  attachments: Attachment[]
  generating: boolean
  disabled?: boolean
  cloud?: boolean
}

export function ChatComposer({
  value,
  onChange,
  onSubmit,
  onStop,
  onFiles,
  onRemoveAttachment,
  attachments,
  generating,
  disabled,
  cloud,
}: Props) {
  const textarea = useRef<HTMLTextAreaElement>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!textarea.current) return
    textarea.current.style.height = '0px'
    textarea.current.style.height = `${Math.min(textarea.current.scrollHeight, 180)}px`
  }, [value])

  const uploadInProgress = attachments.some((item) => item.uploading)

  const send = () => {
    if (!value.trim() || disabled || generating || uploadInProgress) return
    onSubmit()
  }

  return (
    <form
      className="mx-auto w-full max-w-3xl px-4 pb-4 sm:px-5 sm:pb-6"
      onSubmit={(event) => {
        event.preventDefault()
        send()
      }}
    >
      <div className="theme-composer rounded-2xl border p-2 shadow-2xl backdrop-blur-xl transition duration-200 focus-within:border-cyan-400 focus-within:shadow-[0_0_24px_rgba(34,211,238,0.14)]">
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 px-1 pb-2">
            {attachments.map((attachment) => (
              <AttachmentPreview key={attachment.id} attachment={attachment} onRemove={onRemoveAttachment} />
            ))}
          </div>
        )}
        <textarea
          ref={textarea}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === 'Enter'
              && !event.shiftKey
              && !event.repeat
              && !event.nativeEvent.isComposing
            ) {
              event.preventDefault()
              send()
            }
          }}
          placeholder="Ask Sovereign AI anything, or analyze documents…"
          rows={1}
          disabled={disabled}
          className="block max-h-44 min-h-11 w-full resize-none bg-transparent px-3 py-2.5 text-[15px] leading-6 text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)] disabled:opacity-60"
        />
        <div className="flex items-center justify-between px-1 pb-1">
          <div>
            <input
              ref={fileInput}
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md,.csv,.json,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp"
              className="hidden"
              onChange={(event) => {
                onFiles(Array.from(event.target.files || []))
                event.target.value = ''
              }}
            />
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              disabled={disabled || generating}
              className="grid h-9 w-9 place-items-center rounded-xl text-[var(--text-muted)] transition hover:bg-[var(--card-hover)] hover:text-[var(--text-primary)] disabled:opacity-40"
              aria-label="Attach files"
            >
              <Paperclip className="h-[18px] w-[18px]" />
            </button>
          </div>

          {generating ? (
            <button
              type="button"
              onClick={onStop}
              className="relative grid h-9 w-9 place-items-center rounded-xl bg-rose-500 text-white shadow-lg transition hover:bg-rose-600 active:scale-95"
              aria-label="Stop generation"
              title="Stop generation"
            >
              <span className="absolute inset-0 animate-ping rounded-xl bg-rose-400 opacity-60" />
              <Square className="relative z-10 h-3.5 w-3.5 fill-current" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!value.trim() || disabled || uploadInProgress}
              className="grid h-9 w-9 place-items-center rounded-xl bg-cyan-400 text-slate-950 shadow-sm transition hover:bg-cyan-300 hover:shadow-[0_0_15px_rgba(34,211,238,0.3)] disabled:bg-[var(--card-hover)] disabled:text-[var(--text-muted)] disabled:shadow-none"
              aria-label="Send message"
            >
              <ArrowUp className="h-[18px] w-[18px]" />
            </button>
          )}
        </div>
      </div>
      <p className="mt-2 text-center text-[11px] text-[var(--text-muted)]">
        {uploadInProgress
          ? 'Extracting document text before send…'
          : cloud
            ? 'Cloud inference enabled: Prompts and extracted text leave this device.'
            : 'AI runs 100% locally: All conversations and attachments stay on your hardware.'}
      </p>
    </form>
  )
}
