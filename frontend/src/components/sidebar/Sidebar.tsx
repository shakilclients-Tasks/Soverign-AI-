import {
  Database,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Settings,
  SquarePen,
  Sun,
} from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'
import type { Conversation, User, ViewName } from '../../types/api'
import { ConversationItem } from './ConversationItem'

interface Props {
  collapsed: boolean
  onToggle: () => void
  conversations: Conversation[]
  activeConversationId: string | null
  activeView: ViewName
  user: User
  onView: (view: ViewName) => void
  onNewChat: () => void
  onSelectConversation: (id: string) => void
  onDeleteConversation: (id: string) => void
  search: string
  onSearch: (value: string) => void
}

export function Sidebar({
  collapsed,
  onToggle,
  conversations,
  activeConversationId,
  activeView,
  user,
  onView,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  search,
  onSearch,
}: Props) {
  const { isBright, toggleTheme } = useTheme()

  return (
    <aside className={`theme-sidebar relative z-30 flex h-screen shrink-0 flex-col border-r transition-all duration-200 max-sm:absolute max-sm:left-0 max-sm:top-0 ${collapsed ? 'w-[72px] max-sm:w-[272px] max-sm:-translate-x-full' : 'w-[272px]'}`}>
      <div className={`flex h-16 items-center border-b border-[var(--border-subtle)] ${collapsed ? 'justify-center px-2' : 'justify-between px-4'}`}>
        <button type="button" onClick={() => { onView('chat'); onNewChat() }} className="flex min-w-0 items-center gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-cyan-400/30 bg-cyan-400/10 shadow-[0_0_15px_rgba(34,211,238,0.2)]">
            <span className="h-3 w-3 rounded-sm border border-cyan-400" />
          </span>
          {!collapsed && (
            <span className="truncate text-sm font-semibold tracking-[0.12em] text-[var(--text-primary)]">SOVEREIGN AI</span>
          )}
        </button>
        {!collapsed && (
          <button type="button" onClick={onToggle} className="rounded-lg p-2 text-[var(--text-muted)] transition hover:bg-[var(--card-hover)] hover:text-[var(--text-primary)]" aria-label="Collapse sidebar">
            <PanelLeftClose className="h-4 w-4" />
          </button>
        )}
      </div>

      {collapsed && (
        <button type="button" onClick={onToggle} className="mx-auto mt-3 rounded-lg p-2 text-[var(--text-muted)] transition hover:bg-[var(--card-hover)] hover:text-[var(--text-primary)]" aria-label="Expand sidebar">
          <PanelLeftOpen className="h-4 w-4" />
        </button>
      )}

      <div className={`space-y-2 ${collapsed ? 'px-2 pt-2' : 'px-3 pt-4'}`}>
        <button
          type="button"
          onClick={() => { onView('chat'); onNewChat() }}
          title="New chat"
          className={`flex w-full items-center gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--card-bg)] py-2.5 text-sm font-medium text-[var(--text-primary)] shadow-sm transition hover:border-cyan-400/40 hover:bg-[var(--card-hover)] hover:shadow-md ${collapsed ? 'justify-center px-2' : 'px-3'}`}
        >
          <SquarePen className="h-4 w-4 text-cyan-400" />
          {!collapsed && 'New chat'}
        </button>
        {!collapsed && (
          <label className="flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--card-bg)] px-3 py-2 text-[var(--text-muted)] focus-within:border-cyan-400/40 focus-within:text-[var(--text-primary)]">
            <Search className="h-4 w-4" />
            <input
              value={search}
              onChange={(event) => onSearch(event.target.value)}
              placeholder="Search chats"
              className="min-w-0 flex-1 bg-transparent text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]"
            />
          </label>
        )}
      </div>

      <div className={`mt-5 min-h-0 flex-1 overflow-y-auto ${collapsed ? 'px-2' : 'px-3'}`}>
        {!collapsed && <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Recent</p>}
        <div className="space-y-0.5">
          {conversations.map((conversation) => (
            <ConversationItem
              key={conversation.id}
              conversation={conversation}
              active={activeView === 'chat' && activeConversationId === conversation.id}
              collapsed={collapsed}
              onSelect={() => { onView('chat'); onSelectConversation(conversation.id) }}
              onDelete={() => onDeleteConversation(conversation.id)}
            />
          ))}
        </div>
      </div>

      {/* Theme Quick Toggle & Navigation */}
      <div className={`space-y-1 border-t border-[var(--border-subtle)] py-3 ${collapsed ? 'px-2' : 'px-3'}`}>
        <button
          type="button"
          onClick={toggleTheme}
          title={isBright ? 'Switch to Dark-Bright mode' : 'Switch to Bright mode'}
          className={`flex w-full items-center gap-3 rounded-xl py-2.5 text-sm transition ${collapsed ? 'justify-center px-2' : 'px-3'} text-[var(--text-secondary)] hover:bg-[var(--card-hover)] hover:text-[var(--text-primary)]`}
        >
          {isBright ? <Moon className="h-4 w-4 text-cyan-500" /> : <Sun className="h-4 w-4 text-amber-400" />}
          {!collapsed && (isBright ? 'Dark-Bright mode' : 'Bright mode')}
        </button>

        {[
          { view: 'knowledge' as const, label: 'Knowledge', icon: Database },
          { view: 'settings' as const, label: 'Settings', icon: Settings },
        ].map(({ view, label, icon: Icon }) => (
          <button
            key={view}
            type="button"
            onClick={() => onView(view)}
            title={label}
            className={`flex w-full items-center gap-3 rounded-xl py-2.5 text-sm transition ${collapsed ? 'justify-center px-2' : 'px-3'} ${activeView === view ? 'border border-[var(--border-subtle)] bg-[var(--card-hover)] font-medium text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-secondary)] hover:bg-[var(--card-hover)] hover:text-[var(--text-primary)]'}`}
          >
            <Icon className="h-4 w-4" />
            {!collapsed && label}
          </button>
        ))}
      </div>

      <div className={`flex items-center border-t border-[var(--border-subtle)] py-3 ${collapsed ? 'justify-center px-2' : 'gap-3 px-4'}`}>
        <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 text-xs font-semibold text-white shadow-sm">
          {user.full_name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase()}
        </div>
        {!collapsed && (
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-medium text-[var(--text-primary)]">{user.full_name}</div>
            <div className="truncate text-[10px] text-[var(--text-muted)]">{user.role}</div>
          </div>
        )}
      </div>
    </aside>
  )
}
