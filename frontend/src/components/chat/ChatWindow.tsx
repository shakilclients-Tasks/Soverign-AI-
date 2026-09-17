import { useEffect, useRef } from 'react'
import type { Message } from '../../types/api'
import { ChatMessage } from './ChatMessage'
import { EmptyState } from './EmptyState'

interface Props {
  messages: Message[]
  onSuggestion: (prompt: string) => void
}

export function ChatWindow({ messages, onSuggestion }: Props) {
  const scroller = useRef<HTMLDivElement>(null)
  const followOutput = useRef(true)

  useEffect(() => {
    const element = scroller.current
    if (!element || !followOutput.current) return
    const frame = window.requestAnimationFrame(() => {
      element.scrollTo({ top: element.scrollHeight, behavior: 'auto' })
    })
    return () => window.cancelAnimationFrame(frame)
  }, [messages])

  if (!messages.length) return <EmptyState onSuggestion={onSuggestion} />
  return (
    <div
      ref={scroller}
      onScroll={(event) => {
        const element = event.currentTarget
        followOutput.current = element.scrollHeight - element.scrollTop - element.clientHeight < 160
      }}
      className="min-h-0 flex-1 overflow-y-auto overscroll-contain pb-4 pt-8"
    >
      {messages.map((message) => <ChatMessage key={message.id} message={message} />)}
    </div>
  )
}
