export type ViewName = 'chat' | 'knowledge' | 'settings'

export interface User {
  id: string
  username: string
  full_name: string
  role: string
  clearance_level: string
}

export interface Source {
  id?: string | null
  title: string
  page?: number | null
  type: string
  snippet?: string | null
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  model?: string | null
  sources: Source[]
  metadata: Record<string, unknown>
  created_at: string
  streaming?: boolean
  error?: boolean
}

export interface Conversation {
  id: string
  title: string
  model?: string | null
  created_at: string
  updated_at: string
  message_count: number
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export interface Attachment {
  id: string
  filename: string
  content_type: string
  size_bytes: number
  extraction_status: string
  document_id?: string | null
  created_at: string
  uploading?: boolean
}

export interface Health {
  backend: string
  ollama: string
  database: string
  vector_database: string
  chat_model?: string | null
  chat_deployment: 'local' | 'cloud'
  embedding_model?: string | null
  chat_ready: boolean
  knowledge_ready: boolean
  warning?: string | null
  version: string
}

export interface ModelInfo {
  name: string
  display_name?: string
  size_bytes: number
  size_formatted: string
  family?: string | null
  parameter_size?: string | null
  quantization_level?: string | null
  capabilities: string[]
  kind: 'chat' | 'embedding'
  deployment: 'local' | 'cloud'
}

export interface ModelInventory {
  ollama_connected: boolean
  chat_models: ModelInfo[]
  embedding_models: ModelInfo[]
  active_chat_model?: string | null
  active_embedding_model?: string | null
  warning?: string | null
}

export interface RuntimeSettings {
  chat_model?: string | null
  embedding_model?: string | null
  temperature: number
  context_window: number
  ollama_url: string
  available_chat_models: ModelInfo[]
  available_embedding_models: ModelInfo[]
}

export interface KnowledgeDocument {
  id: string
  filename: string
  status: string
  indexed_chunks: number
  created_at: string
}

export interface KnowledgeCollection {
  id: string
  name: string
  slug: string
  description: string
  embedding_model: string
  document_count: number
  total_chunks: number
  created_at: string
  updated_at: string
  documents: KnowledgeDocument[]
}

export type StreamEvent =
  | { type: 'conversation'; conversation_id: string; title: string }
  | { type: 'start'; conversation_id: string; model: string; route: string[] }
  | { type: 'token'; content: string }
  | { type: 'sources'; sources: Source[] }
  | { type: 'warning'; message: string }
  | { type: 'tool'; tool: string; status: string; result: Record<string, unknown> }
  | { type: 'done'; conversation_id: string; message_id: string; model: string }
  | { type: 'error'; code: string; message: string }
