import { ApiError } from './api'
import type { StreamEvent } from '../types/api'

export interface StreamPayload {
  conversation_id?: string | null
  message: string
  attachment_ids: string[]
  knowledge_base_id?: string | null
  model?: string | null
}

export async function streamChat(
  payload: StreamPayload,
  signal: AbortSignal,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  let response: Response
  try {
    response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (error) {
    if (signal.aborted) throw error
    throw new ApiError('Cannot connect to the Sovereign AI backend.')
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(data.detail || 'The chat request failed.', response.status, data.code)
  }
  if (!response.body) throw new ApiError('The backend did not provide a response stream.')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let terminalEventReceived = false

  const consumeBlock = (block: string) => {
    const data = block
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trim())
      .join('\n')
    if (!data) return
    try {
      const event = JSON.parse(data) as StreamEvent
      if (event.type === 'done' || event.type === 'error') terminalEventReceived = true
      onEvent(event)
    } catch {
      // A partial frame remains buffered; malformed complete frames are ignored.
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) {
      buffer += decoder.decode()
      break
    }
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() || ''
    blocks.forEach(consumeBlock)
  }
  if (buffer.trim()) consumeBlock(buffer)
  if (!terminalEventReceived) {
    throw new ApiError('The response stream ended before the answer completed. Please retry.')
  }
}
