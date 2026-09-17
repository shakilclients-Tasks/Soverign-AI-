import type {
  Attachment,
  Conversation,
  ConversationDetail,
  Health,
  KnowledgeCollection,
  ModelInventory,
  RuntimeSettings,
} from '../types/api'

export class ApiError extends Error {
  status: number
  code?: string

  constructor(message: string, status = 0, code?: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

class ApiClient {
  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers)
    if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
    let response: Response
    try {
      response = await fetch(path, { ...options, headers })
    } catch {
      throw new ApiError('Cannot connect to the Sovereign AI backend.')
    }
    if (response.status === 204) return undefined as T
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new ApiError(data.detail || 'The local request failed.', response.status, data.code)
    }
    return data as T
  }

  health = () => this.request<Health>('/api/health')
  models = (refresh = false) => this.request<ModelInventory>(`/api/models?refresh=${refresh}`)
  conversations = (search = '') =>
    this.request<Conversation[]>(`/api/conversations${search ? `?search=${encodeURIComponent(search)}` : ''}`)
  conversation = (id: string) => this.request<ConversationDetail>(`/api/conversations/${id}`)
  deleteConversation = (id: string) => this.request<void>(`/api/conversations/${id}`, { method: 'DELETE' })

  async uploadAttachment(file: File): Promise<Attachment> {
    const form = new FormData()
    form.append('file', file)
    return this.request<Attachment>('/api/attachments', { method: 'POST', body: form })
  }

  deleteAttachment = (id: string) => this.request<void>(`/api/attachments/${id}`, { method: 'DELETE' })

  modelSettings = () => this.request<RuntimeSettings>('/api/settings/models')
  saveModelSettings = (settings: RuntimeSettings) =>
    this.request<RuntimeSettings>('/api/settings/models', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })

  systemSettings = () => this.request<Record<string, unknown>>('/api/settings/system')
  auditLogs = () => this.request<Array<Record<string, unknown>>>('/api/settings/audit')

  knowledge = () => this.request<KnowledgeCollection[]>('/api/knowledge')
  createKnowledge = (name: string, description: string, embeddingModel?: string | null) =>
    this.request<KnowledgeCollection>('/api/knowledge', {
      method: 'POST',
      body: JSON.stringify({ name, description, embedding_model: embeddingModel || null }),
    })

  async uploadKnowledgeDocument(collectionId: string, file: File): Promise<void> {
    const form = new FormData()
    form.append('file', file)
    await this.request(`/api/knowledge/${collectionId}/documents`, { method: 'POST', body: form })
  }

  deleteKnowledge = (id: string) => this.request<void>(`/api/knowledge/${id}`, { method: 'DELETE' })
  deleteKnowledgeDocument = (collectionId: string, documentId: string) =>
    this.request<void>(`/api/knowledge/${collectionId}/documents/${documentId}`, { method: 'DELETE' })
}

export const api = new ApiClient()
