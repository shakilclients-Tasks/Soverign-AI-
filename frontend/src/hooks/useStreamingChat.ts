import { useCallback, useRef } from 'react'
import { streamChat, type StreamPayload } from '../services/chat'
import type { StreamEvent } from '../types/api'

export function useStreamingChat() {
  const controller = useRef<AbortController | null>(null)

  const start = useCallback(async (payload: StreamPayload, onEvent: (event: StreamEvent) => void) => {
    controller.current?.abort()
    const nextController = new AbortController()
    controller.current = nextController
    try {
      await streamChat(payload, nextController.signal, onEvent)
    } finally {
      if (controller.current === nextController) controller.current = null
    }
  }, [])

  const stop = useCallback(() => controller.current?.abort(), [])
  return { start, stop }
}
