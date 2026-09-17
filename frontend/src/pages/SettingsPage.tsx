import { Check, CircleAlert, Cloud, Cpu, Database, HardDrive, Moon, Palette, RefreshCw, Save, ShieldCheck, Sun, Wrench } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { useTheme } from '../hooks/useTheme'
import { api, ApiError } from '../services/api'
import type { RuntimeSettings } from '../types/api'
import { getSovereignModelDisplayName } from '../utils/modelNames'

type Tab = 'models' | 'appearance' | 'privacy' | 'system' | 'advanced'

const tabs: Array<{ id: Tab; label: string; icon: typeof Cpu }> = [
  { id: 'models', label: 'AI models', icon: Cpu },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'privacy', label: 'Privacy', icon: ShieldCheck },
  { id: 'system', label: 'System', icon: HardDrive },
  { id: 'advanced', label: 'Advanced', icon: Wrench },
]

export function SettingsPage() {
  const [tab, setTab] = useState<Tab>('models')
  const [settings, setSettings] = useState<RuntimeSettings | null>(null)
  const [system, setSystem] = useState<Record<string, unknown> | null>(null)
  const [audit, setAudit] = useState<Array<Record<string, unknown>>>([])
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { theme, setTheme } = useTheme()

  const load = async (refresh = false) => {
    setBusy(true)
    setError(null)
    try {
      if (refresh) await api.models(true)
      const [modelSettings, systemSettings, logs] = await Promise.all([
        api.modelSettings(), api.systemSettings(), api.auditLogs(),
      ])
      setSettings(modelSettings)
      setSystem(systemSettings)
      setAudit(logs)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not load local settings.')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { void load() }, [])

  const selectedChatModel = settings?.available_chat_models.find(
    (model) => model.name === settings.chat_model,
  )
  const cloudSelected = selectedChatModel?.deployment === 'cloud'

  const save = async () => {
    if (!settings) return
    setBusy(true)
    setSaved(false)
    setError(null)
    try {
      setSettings(await api.saveModelSettings(settings))
      setSaved(true)
      window.setTimeout(() => setSaved(false), 2500)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not save model settings.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="theme-app h-screen min-w-0 flex-1 overflow-y-auto">
      <header className="theme-header sticky top-0 z-10 flex h-16 items-center justify-between border-b px-6 max-sm:pl-16 backdrop-blur sm:px-8">
        <div>
          <h1 className="text-sm font-semibold text-[var(--text-primary)]">Settings</h1>
          <p className="mt-0.5 text-[11px] text-[var(--text-muted)]">Local runtime configuration, themes, and diagnostics</p>
        </div>
        <button
          type="button"
          onClick={() => void load(true)}
          disabled={busy}
          className="rounded-xl p-2.5 text-[var(--text-muted)] transition hover:bg-[var(--card-hover)] hover:text-[var(--text-primary)] disabled:opacity-50"
          aria-label="Refresh models"
        >
          <RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} />
        </button>
      </header>

      <div className="mx-auto max-w-5xl p-5 sm:p-8">
        {error && (
          <div className="mb-5 flex items-center gap-2 rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-xs text-rose-300">
            <CircleAlert className="h-4 w-4" />
            {error}
          </div>
        )}
        <div className="grid gap-7 md:grid-cols-[180px_minmax(0,1fr)]">
          <nav className="space-y-1">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                  tab === id
                    ? 'border border-[var(--border-subtle)] bg-[var(--card-hover)] font-medium text-[var(--text-primary)] shadow-sm'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--card-hover)] hover:text-[var(--text-primary)]'
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </nav>

          <div className="min-w-0">
            {tab === 'models' && (
              <div className="space-y-5">
                <SettingsCard title="Model routing" description="Chat generation and vector embeddings use separate compatible models.">
                  {!settings ? <p className="text-sm text-[var(--text-muted)]">Loading discovered models…</p> : (
                    <div className="space-y-5">
                      <label className="block">
                        <FieldLabel>Chat model</FieldLabel>
                        <select className="field" value={settings.chat_model || ''} onChange={(event) => setSettings({ ...settings, chat_model: event.target.value || null })}>
                          <option value="">Select a chat-capable model</option>
                          {settings.available_chat_models.map((model) => (
                            <option key={model.name} value={model.name}>
                              {model.display_name || getSovereignModelDisplayName(model.name)} · {model.deployment === 'cloud' ? 'Cloud' : model.size_formatted}
                            </option>
                          ))}
                        </select>
                      </label>
                      {cloudSelected && (
                        <div className="flex gap-3 rounded-xl border border-amber-400/20 bg-amber-400/10 p-4 text-xs leading-5 text-amber-300">
                          <Cloud className="mt-0.5 h-4 w-4 shrink-0" />
                          <div>
                            <p className="font-medium text-amber-200">Ollama Cloud model</p>
                            <p className="mt-1">Prompts and extracted attachment text leave this device. GLM-5.3-Flash requires an eligible subscription or extra usage on the signed-in Ollama account.</p>
                            <a href="https://ollama.com/upgrade" target="_blank" rel="noreferrer" className="mt-2 inline-block text-cyan-400 underline underline-offset-4">Manage Ollama cloud access</a>
                          </div>
                        </div>
                      )}
                      <label className="block">
                        <FieldLabel>Embedding model</FieldLabel>
                        <select className="field" value={settings.embedding_model || ''} onChange={(event) => setSettings({ ...settings, embedding_model: event.target.value || null })}>
                          <option value="">Select an embedding model</option>
                          {settings.available_embedding_models.map((model) => (
                            <option key={model.name} value={model.name}>
                              {model.display_name || getSovereignModelDisplayName(model.name)} · {model.size_formatted}
                            </option>
                          ))}
                        </select>
                      </label>
                      <div className="grid gap-4 sm:grid-cols-2">
                        <label>
                          <FieldLabel>Temperature · {settings.temperature.toFixed(1)}</FieldLabel>
                          <input type="range" min="0" max="2" step="0.1" value={settings.temperature} onChange={(event) => setSettings({ ...settings, temperature: Number(event.target.value) })} className="w-full accent-cyan-400" />
                        </label>
                        <label>
                          <FieldLabel>Context window</FieldLabel>
                          <input type="number" min="2048" max="262144" step="1024" value={settings.context_window} onChange={(event) => setSettings({ ...settings, context_window: Number(event.target.value) })} className="field" />
                        </label>
                      </div>
                    </div>
                  )}
                </SettingsCard>
                <button type="button" onClick={() => void save()} disabled={busy || !settings} className="flex items-center gap-2 rounded-xl bg-cyan-400 px-5 py-2.5 text-sm font-semibold text-slate-950 shadow transition hover:bg-cyan-300 disabled:opacity-50">
                  {saved ? <Check className="h-4 w-4" /> : <Save className="h-4 w-4" />}{saved ? 'Saved' : 'Save settings'}
                </button>
              </div>
            )}

            {tab === 'appearance' && (
              <SettingsCard title="Theme & Appearance" description="Switch between luminous Dark-Bright mode and clean Bright daylight mode.">
                <div className="grid gap-4 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => setTheme('dark')}
                    className={`flex flex-col items-start rounded-2xl border p-5 text-left transition ${
                      theme === 'dark'
                        ? 'border-cyan-400 bg-cyan-400/[0.08] shadow-[0_0_20px_rgba(34,211,238,0.15)] ring-2 ring-cyan-400/40'
                        : 'border-[var(--border-subtle)] bg-[var(--card-bg)] hover:bg-[var(--card-hover)]'
                    }`}
                  >
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 border border-cyan-400/30 text-cyan-400">
                      <Moon className="h-5 w-5" />
                    </div>
                    <h3 className="text-sm font-semibold text-[var(--text-primary)]">Dark-Bright Mode</h3>
                    <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">
                      Deep obsidian background with glowing neon cyan accents, cyberpunk aesthetics, and reduced eye strain.
                    </p>
                    {theme === 'dark' && (
                      <span className="mt-3 inline-flex items-center gap-1 text-[11px] font-semibold text-cyan-400">
                        <Check className="h-3.5 w-3.5" /> Active Theme
                      </span>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={() => setTheme('bright')}
                    className={`flex flex-col items-start rounded-2xl border p-5 text-left transition ${
                      theme === 'bright'
                        ? 'border-cyan-500 bg-cyan-500/[0.08] shadow-[0_0_20px_rgba(2,132,199,0.15)] ring-2 ring-cyan-500/40'
                        : 'border-[var(--border-subtle)] bg-[var(--card-bg)] hover:bg-[var(--card-hover)]'
                    }`}
                  >
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 border border-amber-300 text-amber-600">
                      <Sun className="h-5 w-5" />
                    </div>
                    <h3 className="text-sm font-semibold text-[var(--text-primary)]">Bright Mode</h3>
                    <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">
                      Crisp daylight light mode with high-contrast text, polished borders, and readable document presentation.
                    </p>
                    {theme === 'bright' && (
                      <span className="mt-3 inline-flex items-center gap-1 text-[11px] font-semibold text-cyan-600">
                        <Check className="h-3.5 w-3.5" /> Active Theme
                      </span>
                    )}
                  </button>
                </div>
              </SettingsCard>
            )}

            {tab === 'privacy' && (
              <SettingsCard
                title={cloudSelected ? 'Cloud-enabled deployment' : 'Private by architecture'}
                description={cloudSelected ? 'Review what leaves this device before using the selected model.' : 'Operational boundaries enforced by this deployment.'}
              >
                <div className="space-y-3">
                  {[
                    [
                      'Inference route',
                      cloudSelected
                        ? 'The selected chat model runs in Ollama Cloud; prompts and extracted attachment text leave this device.'
                        : 'The selected chat model and embeddings run locally through the loopback Ollama service.',
                    ],
                    ['Local persistence', 'Conversations, attachments, and audit events remain in the local data directory.'],
                    ['Isolated tools', system?.docker_sandbox_available ? 'Python execution uses an isolated, network-disabled Docker sandbox.' : 'Code execution stays disabled until a Docker sandbox is available.'],
                    ['Explicit retrieval', 'Uploaded content is retrieved from local vector collections and surfaced with sources.'],
                  ].map(([title, detail]) => (
                    <div key={String(title)} className="flex gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--card-bg)] p-4 shadow-sm">
                      <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">{title}</p>
                        <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </SettingsCard>
            )}

            {tab === 'system' && (
              <SettingsCard title="System health" description="Read-only diagnostics from the local host.">
                <div className="grid gap-3 sm:grid-cols-2">
                  {system && Object.entries(system).map(([key, value]) => (
                    <div key={key} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--card-bg)] p-4 shadow-sm">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">{key.replaceAll('_', ' ')}</p>
                      <p className="mt-2 break-words text-sm font-mono text-[var(--text-primary)]">{String(value)}</p>
                    </div>
                  ))}
                </div>
              </SettingsCard>
            )}

            {tab === 'advanced' && (
              <div className="space-y-5">
                <SettingsCard title="Ollama endpoint" description="The app connects to loopback Ollama; :cloud models can relay inference through the signed-in Ollama account.">
                  <label>
                    <FieldLabel>Base URL</FieldLabel>
                    <input className="field" value={settings?.ollama_url || ''} disabled={!settings} onChange={(event) => settings && setSettings({ ...settings, ollama_url: event.target.value })} />
                  </label>
                  <button type="button" onClick={() => void save()} disabled={busy || !settings} className="mt-4 flex items-center gap-2 rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 text-xs font-medium text-cyan-400 shadow-sm hover:bg-cyan-400/20 disabled:opacity-50">
                    <Save className="h-3.5 w-3.5" />
                    Save endpoint
                  </button>
                </SettingsCard>
                <SettingsCard title="Recent audit events" description="Latest local security and application events.">
                  <div className="max-h-80 space-y-1 overflow-auto font-mono text-[11px] text-[var(--text-muted)]">
                    {audit.length === 0 ? <p>No audit events recorded.</p> : audit.map((entry, index) => <div key={`${String(entry.id || '')}-${index}`} className="rounded-lg border border-[var(--border-subtle)] bg-[var(--card-bg)] px-3 py-2 text-[var(--text-secondary)]">{JSON.stringify(entry)}</div>)}
                  </div>
                </SettingsCard>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

function FieldLabel({ children }: { children: ReactNode }) {
  return <span className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">{children}</span>
}

function SettingsCard({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <section className="theme-card rounded-2xl border p-5 shadow-sm sm:p-6">
      <div className="mb-5 flex items-start gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-cyan-400/10 text-cyan-400"><Database className="h-4 w-4" /></span>
        <div>
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h2>
          <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{description}</p>
        </div>
      </div>
      {children}
    </section>
  )
}
