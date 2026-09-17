import { MessageSquare, Trash2 } from 'lucide-react'
import type { Conversation } from '../../types/api'

interface Props {
  conversation: Conversation
  active: boolean
  collapsed: boolean
  onSelect: () => void
  onDelete: () => void
}

export function ConversationItem({ conversation, active, collapsed, onSelect, onDelete }: Props) {
  return (
    <div
      className={`group relative flex items-center rounded-xl transition ${
        active
          ? 'border border-[var(--border-subtle)] bg-[var(--card-hover)] font-medium text-[var(--text-primary)] shadow-sm'
          : 'text-[var(--text-secondary)] hover:bg-[var(--card-hover)] hover:text-[var(--text-primary)]'
      }`}
    >
      <button
        type="button"
        onClick={onSelect}
        title={conversation.title}
        className={`flex min-w-0 flex-1 items-center gap-3 py-2.5 text-left text-sm ${collapsed ? 'justify-center px-2.5' : 'px-3 pr-8'}`}
      >
        <MessageSquare className="h-4 w-4 shrink-0 text-cyan-400" />
        {!collapsed && <span className="truncate">{conversation.title}</span>}
      </button>
      {!collapsed && (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation()
            onDelete()
          }}
          className="absolute right-1.5 grid h-7 w-7 place-items-center rounded-lg text-[var(--text-muted)] opacity-0 transition hover:bg-rose-400/10 hover:text-rose-400 group-hover:opacity-100"
          aria-label={`Delete ${conversation.title}`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  )
}
