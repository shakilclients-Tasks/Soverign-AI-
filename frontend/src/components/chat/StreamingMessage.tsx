import { useEffect, useState } from 'react'

const WAITING_MESSAGES = [
  'Synthesizing document context…',
  'Grounding in local knowledge…',
  'Analyzing parameters & citations…',
  'Composing structured response…',
]

export function StreamingMessage({ waiting = false }: { waiting?: boolean }) {
  const [phaseIndex, setPhaseIndex] = useState(0)

  useEffect(() => {
    if (!waiting) return
    const interval = window.setInterval(() => {
      setPhaseIndex((prev) => (prev + 1) % WAITING_MESSAGES.length)
    }, 2200)
    return () => window.clearInterval(interval)
  }, [waiting])

  if (waiting) {
    return (
      <div className="my-2 inline-flex items-center gap-3 rounded-2xl border border-cyan-400/25 bg-cyan-400/[0.08] px-4 py-2.5 text-xs font-medium text-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.12)] backdrop-blur-md transition-all duration-300">
        {/* Animated 4-bar equalizer */}
        <div className="flex items-center gap-1" aria-hidden="true">
          <span className="w-1 rounded-full bg-cyan-400 animate-wave-1 shadow-[0_0_8px_#22d3ee]" />
          <span className="w-1 rounded-full bg-cyan-300 animate-wave-2 shadow-[0_0_8px_#22d3ee]" />
          <span className="w-1 rounded-full bg-cyan-400 animate-wave-3 shadow-[0_0_8px_#22d3ee]" />
          <span className="w-1 rounded-full bg-cyan-200 animate-wave-4 shadow-[0_0_8px_#22d3ee]" />
        </div>

        {/* Dynamic status text */}
        <span className="tracking-wide">
          {WAITING_MESSAGES[phaseIndex]}
        </span>

        {/* Pulsing micro live indicator */}
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-400" />
        </span>
      </div>
    )
  }

  return (
    <span
      className="ml-1 inline-block h-5 w-1.5 animate-luminous-beam rounded-full bg-cyan-400 align-middle shadow-[0_0_12px_#22d3ee]"
      aria-label="Generating response"
      title="Generating"
    />
  )
}
