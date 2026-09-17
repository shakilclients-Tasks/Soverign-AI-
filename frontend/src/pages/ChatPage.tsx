import { Cloud, LockKeyhole, Moon, Settings, Sun } from 'lucide-react'
import { useState } from 'react'
import { ChatComposer } from '../components/chat/ChatComposer'
import { ChatWindow } from '../components/chat/ChatWindow'
import { useTheme } from '../hooks/useTheme'
import { api, ApiError } from '../services/api'
import type { Attachment, Health } from '../types/api'
import type { useChat } from '../hooks/useChat'
import { getSovereignModelDisplayName } from '../utils/modelNames'

type ChatController = ReturnType<typeof useChat>

interface Props {
  chat: ChatController
  health: Health | null
  onOpenSettings: () => void
}

export function ChatPage({ chat, health, onOpenSettings }: Props) {
  const [input, setInput] = useState('')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [uploadError, setUploadError] = useState<string | null>(null)
  const { isBright, toggleTheme } = useTheme()
  const cloudModel = health?.chat_deployment === 'cloud'

  const addFiles = async (files: File[]) => {
    setUploadError(null)
    for (const file of files) {
      const temporary: Attachment = {
        id: `upload-${crypto.randomUUID()}`,
        filename: file.name,
        content_type: file.type || 'application/octet-stream',
        size_bytes: file.size,
        extraction_status: 'processing',
        created_at: new Date().toISOString(),
        uploading: true,
      }
      setAttachments((current) => [...current, temporary])
      try {
        const uploaded = await api.uploadAttachment(file)
        setAttachments((current) => current.map((item) => item.id === temporary.id ? uploaded : item))
      } catch (error) {
        setAttachments((current) => current.filter((item) => item.id !== temporary.id))
        setUploadError(error instanceof ApiError ? error.message : `Could not process ${file.name}.`)
      }
    }
  }

  const removeAttachment = async (attachment: Attachment) => {
    setAttachments((current) => current.filter((item) => item.id !== attachment.id))
    try {
      await api.deleteAttachment(attachment.id)
    } catch {
      // The server will retain any attachment that is already bound to a message.
    }
  }

  const submit = () => {
    const prompt = input.trim()
    if (!prompt) return
    if (attachments.some((attachment) => attachment.uploading)) {
      setUploadError('Wait for local OCR to finish before sending this message.')
      return
    }
    const readyAttachments = attachments.filter((attachment) => !attachment.uploading)
    setUploadError(null)
    setInput('')
    setAttachments([])
    void chat.send(prompt, readyAttachments)
  }

  const statusLabel = !health
    ? 'Checking local services'
    : health.chat_ready
      ? `${getSovereignModelDisplayName(health.chat_model)} · ${cloudModel ? 'Cloud' : 'Private'}`
      : health.ollama === 'offline'
        ? 'Local AI service offline'
        : 'Chat model required'

  return (
    <section className="theme-app flex h-screen min-w-0 flex-1 flex-col">
      <header className="theme-header flex h-16 shrink-0 items-center justify-between border-b px-5 max-sm:pl-16 sm:px-7">
        <div>
          <h1 className="text-sm font-semibold tracking-wide text-[var(--text-primary)]">Sovereign AI</h1>
          <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-[var(--text-muted)]">
            <span className={`h-1.5 w-1.5 rounded-full ${health?.chat_ready ? cloudModel ? 'bg-amber-400' : 'bg-emerald-400' : health?.ollama === 'offline' ? 'bg-rose-400' : 'bg-amber-400'}`} />
            {statusLabel}
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Theme switcher button */}
          <button
            type="button"
            onClick={toggleTheme}
            className="flex items-center gap-1.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--card-bg)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] shadow-sm transition hover:border-cyan-400/40 hover:text-[var(--text-primary)] hover:shadow-md"
            aria-label={isBright ? 'Switch to Dark-Bright mode' : 'Switch to Bright mode'}
            title={isBright ? 'Switch to Dark-Bright mode' : 'Switch to Bright mode'}
          >
            {isBright ? (
              <>
                <Moon className="h-4 w-4 text-cyan-500" />
                <span className="hidden sm:inline">Dark-Bright</span>
              </>
            ) : (
              <>
                <Sun className="h-4 w-4 text-amber-400" />
                <span className="hidden sm:inline">Bright Mode</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={onOpenSettings}
            className="rounded-xl p-2.5 text-[var(--text-muted)] transition hover:bg-[var(--card-hover)] hover:text-[var(--text-primary)]"
            aria-label="Open settings"
            title="Settings"
          >
            <Settings className="h-[18px] w-[18px]" />
          </button>
        </div>
      </header>

      <ChatWindow messages={chat.messages} onSuggestion={setInput} />

      {cloudModel && (
        <div className="mx-auto mb-2 flex w-full max-w-3xl items-start gap-2 px-5 text-xs text-amber-400">
          <Cloud className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>Cloud mode: prompts and extracted attachment text are sent through Ollama Cloud.</span>
        </div>
      )}

      {(chat.notice || uploadError) && (
        <div className="mx-auto mb-2 flex w-full max-w-3xl items-start gap-2 px-5 text-xs text-amber-400">
          <LockKeyhole className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{uploadError || chat.notice}</span>
        </div>
      )}

      <ChatComposer
        value={input}
        onChange={setInput}
        onSubmit={submit}
        onStop={chat.stop}
        onFiles={(files) => void addFiles(files)}
        onRemoveAttachment={(attachment) => void removeAttachment(attachment)}
        attachments={attachments}
        generating={chat.isGenerating}
        disabled={!health?.chat_ready}
        cloud={cloudModel}
      />
    </section>
  )
}
