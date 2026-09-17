import { Braces, FileSearch, Landmark, MessageSquareText } from 'lucide-react'

const suggestions = [
  { label: 'Analyze a document', prompt: 'Summarize the attached document and highlight the key findings and risks.', icon: FileSearch },
  { label: 'Write or debug code', prompt: 'Help me write clear, production-ready Python code for this task:', icon: Braces },
  { label: 'Search organizational knowledge', prompt: 'Search our organizational knowledge for the relevant standards and summarize them.', icon: Landmark },
  { label: 'Ask an analytical question', prompt: 'Explain zero-trust architecture and air-gap isolation in enterprise environments.', icon: MessageSquareText },
]

export function EmptyState({ onSuggestion }: { onSuggestion: (prompt: string) => void }) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center px-5 pb-8 pt-20 text-center">
      <div className="mb-6 grid h-14 w-14 place-items-center rounded-2xl border border-cyan-400/30 bg-gradient-to-br from-cyan-400/20 to-blue-500/10 shadow-[0_0_30px_rgba(34,211,238,0.2)]">
        <div className="h-5 w-5 rounded-md border border-cyan-300 bg-cyan-400/20 shadow-[0_0_8px_#22d3ee]" />
      </div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-cyan-400">Sovereign AI</p>
      <h1 className="max-w-xl text-balance text-3xl font-semibold tracking-tight text-[var(--text-primary)] sm:text-4xl">
        Private Intelligence. Your Infrastructure.
      </h1>
      <p className="mt-4 text-base text-[var(--text-secondary)]">How can I assist you with your documents and data today?</p>
      <div className="mt-9 grid w-full grid-cols-1 gap-2.5 sm:grid-cols-2">
        {suggestions.map(({ label, prompt, icon: Icon }) => (
          <button
            key={label}
            type="button"
            onClick={() => onSuggestion(prompt)}
            className="group flex items-center gap-3 rounded-2xl border border-[var(--border-subtle)] bg-[var(--card-bg)] px-4 py-3.5 text-left text-sm text-[var(--text-primary)] shadow-sm transition hover:border-cyan-400/35 hover:bg-[var(--card-hover)] hover:shadow-md"
          >
            <Icon className="h-4 w-4 text-cyan-400 transition group-hover:scale-110" />
            <span className="truncate">{label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
