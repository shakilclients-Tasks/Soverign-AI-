import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../services/api'
import { useStreamingChat } from './useStreamingChat'
import type { Attachment, Conversation, Message, Source, StreamEvent } from '../types/api'

const localMessage = (role: 'user' | 'assistant', content: string): Message => ({
  id: `local-${crypto.randomUUID()}`,
  conversation_id: '',
  role,
  content,
  sources: [],
  metadata: {},
  created_at: new Date().toISOString(),
})

export function useChat(enabled: boolean) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isGenerating, setGenerating] = useState(false)
  const generatingRef = useRef(false)
  const [notice, setNotice] = useState<string | null>(null)
  const { start, stop: stopStream } = useStreamingChat()

  const reloadConversations = useCallback(async () => {
    if (!enabled) return
    setConversations(await api.conversations())
  }, [enabled])

  useEffect(() => {
    void reloadConversations()
  }, [reloadConversations])

  const selectConversation = useCallback(async (id: string) => {
    stopStream()
    const detail = await api.conversation(id)
    setActiveConversationId(id)
    setMessages(detail.messages)
    setNotice(null)
  }, [stopStream])

  const newChat = useCallback(() => {
    stopStream()
    setActiveConversationId(null)
    setMessages([])
    setNotice(null)
  }, [stopStream])

  const deleteConversation = useCallback(async (id: string) => {
    await api.deleteConversation(id)
    if (activeConversationId === id) newChat()
    await reloadConversations()
  }, [activeConversationId, newChat, reloadConversations])

  const send = useCallback(async (text: string, attachments: Attachment[] = []) => {
    if (!text.trim() || generatingRef.current) return
    generatingRef.current = true
    setNotice(null)
    const user = localMessage('user', text.trim())
    const assistant = { ...localMessage('assistant', ''), streaming: true }
    setMessages((current) => [...current, user, assistant])
    setGenerating(true)
    let terminalError = false
    const handleEvent = (event: StreamEvent) => {
      if (event.type === 'conversation') {
        setActiveConversationId(event.conversation_id)
      } else if (event.type === 'token') {
        setMessages((current) => current.map((message) =>
          message.id === assistant.id ? { ...message, content: message.content + event.content } : message
        ))
      } else if (event.type === 'sources') {
        setMessages((current) => current.map((message) =>
          message.id === assistant.id ? { ...message, sources: event.sources } : message
        ))
      } else if (event.type === 'warning') {
        setNotice(event.message)
      } else if (event.type === 'start') {
        setMessages((current) => current.map((message) =>
          message.id === assistant.id ? { ...message, model: event.model } : message
        ))
      } else if (event.type === 'done') {
        setMessages((current) => current.map((message) =>
          message.id === assistant.id ? { ...message, id: event.message_id, streaming: false } : message
        ))
      } else if (event.type === 'error') {
        terminalError = true
        setMessages((current) => current.map((message) =>
          message.id === assistant.id
            ? {
                ...message,
                content: message.content
                  ? `${message.content}\n\n> Response interrupted: ${event.message}`
                  : event.message,
                streaming: false,
                error: true,
              }
            : message
        ))
      }
    }

    try {
      await start({
        conversation_id: activeConversationId,
        message: text.trim(),
        attachment_ids: attachments.map((attachment) => attachment.id),
      }, handleEvent)
      if (!terminalError) {
        setMessages((current) => current.map((message) =>
          message.id === assistant.id ? { ...message, streaming: false } : message
        ))
      }
      await reloadConversations()
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        setMessages((current) => current.map((message) =>
          message.id === assistant.id
            ? { ...message, content: `${message.content}\n\n_Generation stopped._`, streaming: false }
            : message
        ))
      } else {
        const message = error instanceof ApiError ? error.message : 'Sovereign AI could not complete this request.'
        setMessages((current) => current.map((item) =>
          item.id === assistant.id
            ? {
                ...item,
                content: item.content
                  ? `${item.content}\n\n> Response interrupted: ${message}`
                  : message,
                streaming: false,
                error: true,
              }
            : item
        ))
      }
    } finally {
      generatingRef.current = false
      setGenerating(false)
    }
  }, [activeConversationId, reloadConversations, start])

  const stop = useCallback(() => stopStream(), [stopStream])

  return {
    conversations,
    activeConversationId,
    messages,
    isGenerating,
    notice,
    send,
    stop,
    newChat,
    selectConversation,
    deleteConversation,
    reloadConversations,
  }
}
