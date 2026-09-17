import { useEffect, useMemo, useState } from 'react'
import { Menu } from 'lucide-react'
import { Sidebar } from './components/sidebar/Sidebar'
import { useChat } from './hooks/useChat'
import { useTheme } from './hooks/useTheme'
import { ChatPage } from './pages/ChatPage'
import { KnowledgePage } from './pages/KnowledgePage'
import { SettingsPage } from './pages/SettingsPage'
import { api } from './services/api'
import type { Health, User, ViewName } from './types/api'

const LOCAL_USER: User = {
  id: 'local-user',
  username: 'local',
  full_name: 'Local User',
  role: 'local operator',
  clearance_level: 'LOCAL',
}

export default function App() {
  useTheme() // Initializes theme on root element
  const [loading, setLoading] = useState(true)
  const [startupError, setStartupError] = useState<string | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [view, setView] = useState<ViewName>('chat')
  const [collapsed, setCollapsed] = useState(() => window.innerWidth < 900)
  const [search, setSearch] = useState('')
  const chat = useChat(true)

  useEffect(() => {
    let active = true
    const initialize = async () => {
      try {
        const currentHealth = await api.health()
        if (!active) return
        setHealth(currentHealth)
      } catch {
        if (active) setStartupError('Cannot connect to the Sovereign AI backend.')
      } finally {
        if (active) setLoading(false)
      }
    }
    void initialize()
    return () => { active = false }
  }, [])

  useEffect(() => {
    const poll = window.setInterval(() => {
      void api.health().then(setHealth).catch(() => setHealth(null))
    }, 15000)
    return () => window.clearInterval(poll)
  }, [])

  const visibleConversations = useMemo(() => {
    const query = search.trim().toLocaleLowerCase()
    return query
      ? chat.conversations.filter((conversation) => conversation.title.toLocaleLowerCase().includes(query))
      : chat.conversations
  }, [chat.conversations, search])

  if (loading) {
    return (
      <main className="theme-app grid min-h-screen place-items-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-cyan-400" />
      </main>
    )
  }

  if (startupError) {
    return (
      <main className="theme-app grid min-h-screen place-items-center px-5 text-center">
        <div>
          <p className="text-sm font-medium text-[var(--text-primary)]">{startupError}</p>
          <p className="mt-2 text-xs text-[var(--text-muted)]">Start the local FastAPI service, then try again.</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-5 rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 shadow transition hover:bg-cyan-300"
          >
            Retry
          </button>
        </div>
      </main>
    )
  }

  return (
    <main className="theme-app flex h-screen overflow-hidden">
      {!collapsed && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={() => setCollapsed(true)}
          className="fixed inset-0 z-20 hidden bg-black/50 backdrop-blur-sm max-sm:block"
        />
      )}
      {collapsed && (
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          className="fixed left-3 top-3 z-40 hidden h-10 w-10 place-items-center rounded-xl border border-[var(--border-subtle)] bg-[var(--card-bg)] text-[var(--text-secondary)] shadow-xl max-sm:grid"
          aria-label="Open navigation"
        >
          <Menu className="h-4 w-4" />
        </button>
      )}
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((value) => !value)}
        conversations={visibleConversations}
        activeConversationId={chat.activeConversationId}
        activeView={view}
        user={LOCAL_USER}
        onView={setView}
        onNewChat={chat.newChat}
        onSelectConversation={(id) => void chat.selectConversation(id)}
        onDeleteConversation={(id) => void chat.deleteConversation(id)}
        search={search}
        onSearch={setSearch}
      />
      {view === 'chat' && <ChatPage chat={chat} health={health} onOpenSettings={() => setView('settings')} />}
      {view === 'knowledge' && <KnowledgePage />}
      {view === 'settings' && <SettingsPage />}
    </main>
  )
}
