import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  failed: boolean
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Sovereign AI render failure', error, info.componentStack)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <main className="grid h-full place-items-center bg-graphite-950 px-5 text-center">
        <div>
          <p className="text-sm font-medium text-slate-200">The interface could not render this response.</p>
          <p className="mt-2 text-xs text-slate-500">Your conversation is saved locally.</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-5 rounded-xl bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950"
          >
            Reload interface
          </button>
        </div>
      </main>
    )
  }
}
