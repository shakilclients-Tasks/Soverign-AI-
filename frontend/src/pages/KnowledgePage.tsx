import { Database, FileText, LoaderCircle, Plus, Trash2, Upload, X } from 'lucide-react'
import { FormEvent, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../services/api'
import type { KnowledgeCollection } from '../types/api'

export function KnowledgePage() {
  const [collections, setCollections] = useState<KnowledgeCollection[]>([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [creating, setCreating] = useState(false)
  const [uploadingTo, setUploadingTo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const uploadTarget = useRef<string | null>(null)

  const load = async () => {
    try {
      setCollections(await api.knowledge())
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not load local knowledge collections.')
    }
  }

  useEffect(() => { void load() }, [])

  const create = async (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim()) return
    setCreating(true)
    setError(null)
    try {
      await api.createKnowledge(name.trim(), description.trim())
      setName('')
      setDescription('')
      await load()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not create the collection.')
    } finally {
      setCreating(false)
    }
  }

  const chooseFile = (collectionId: string) => {
    uploadTarget.current = collectionId
    fileInput.current?.click()
  }

  const upload = async (file: File | undefined) => {
    const collectionId = uploadTarget.current
    if (!file || !collectionId) return
    setUploadingTo(collectionId)
    setError(null)
    try {
      await api.uploadKnowledgeDocument(collectionId, file)
      await load()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : `Could not index ${file.name}.`)
    } finally {
      setUploadingTo(null)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  const deleteCollection = async (collection: KnowledgeCollection) => {
    if (!window.confirm(`Delete “${collection.name}” and its indexed data?`)) return
    try {
      await api.deleteKnowledge(collection.id)
      await load()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not delete the collection.')
    }
  }

  const deleteDocument = async (collectionId: string, documentId: string) => {
    try {
      await api.deleteKnowledgeDocument(collectionId, documentId)
      await load()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not delete the document.')
    }
  }

  return (
    <section className="theme-app h-screen min-w-0 flex-1 overflow-y-auto">
      <header className="theme-header sticky top-0 z-10 flex h-16 items-center border-b px-6 max-sm:pl-16 backdrop-blur sm:px-8">
        <div>
          <h1 className="text-sm font-semibold text-[var(--text-primary)]">Knowledge Collections</h1>
          <p className="mt-0.5 text-[11px] text-[var(--text-muted)]">Private retrieval collections stored locally on this machine</p>
        </div>
      </header>

      <div className="mx-auto max-w-5xl space-y-8 p-5 sm:p-8">
        {error && (
          <div className="flex items-start justify-between rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-xs text-rose-300">
            {error}
            <button type="button" onClick={() => setError(null)}><X className="h-4 w-4" /></button>
          </div>
        )}

        <form onSubmit={create} className="theme-card rounded-2xl border p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-cyan-400/15 text-cyan-400"><Plus className="h-4 w-4" /></span>
            <div>
              <h2 className="text-sm font-medium text-[var(--text-primary)]">New collection</h2>
              <p className="text-xs text-[var(--text-muted)]">Group related documents for grounded retrieval and citations.</p>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)_auto]">
            <input className="field" value={name} onChange={(event) => setName(event.target.value)} placeholder="Collection name" required minLength={2} />
            <input className="field" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Description or topic (optional)" />
            <button disabled={creating} className="rounded-xl bg-cyan-400 px-5 py-2 text-sm font-semibold text-slate-950 shadow transition hover:bg-cyan-300 disabled:opacity-50">
              {creating ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>

        <input ref={fileInput} type="file" className="hidden" accept=".pdf,.docx,.txt,.md,.csv,.json,.png,.jpg,.jpeg,.webp" onChange={(event) => void upload(event.target.files?.[0])} />

        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Collections</h2>
            <span className="text-xs text-[var(--text-muted)]">{collections.length} total</span>
          </div>
          {collections.length === 0 ? (
            <div className="grid min-h-56 place-items-center rounded-2xl border border-dashed border-[var(--border-subtle)] bg-[var(--card-bg)] text-center">
              <div>
                <Database className="mx-auto mb-3 h-6 w-6 text-[var(--text-muted)]" />
                <p className="text-sm text-[var(--text-secondary)]">No knowledge collections yet</p>
                <p className="mt-1 text-xs text-[var(--text-muted)]">Create one above, then upload source documents.</p>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {collections.map((collection) => (
                <article key={collection.id} className="theme-card rounded-2xl border p-5 shadow-sm">
                  <div className="flex items-start gap-3">
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-cyan-400/10 text-cyan-400"><Database className="h-4 w-4" /></div>
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate text-sm font-medium text-[var(--text-primary)]">{collection.name}</h3>
                      <p className="mt-1 line-clamp-2 text-xs leading-5 text-[var(--text-muted)]">{collection.description || 'No description provided'}</p>
                    </div>
                    <button type="button" onClick={() => void deleteCollection(collection)} className="rounded-lg p-2 text-[var(--text-muted)] hover:bg-rose-400/10 hover:text-rose-400" aria-label="Delete collection"><Trash2 className="h-4 w-4" /></button>
                  </div>
                  <div className="mt-4 flex items-center gap-4 border-y border-[var(--border-subtle)] py-3 text-[11px] text-[var(--text-muted)]">
                    <span>{collection.document_count} documents</span>
                    <span>{collection.total_chunks} chunks</span>
                    <span className="min-w-0 truncate">{collection.embedding_model}</span>
                  </div>
                  <div className="mt-3 max-h-40 space-y-1 overflow-y-auto">
                    {collection.documents.map((document) => (
                      <div key={document.id} className="group flex items-center gap-2 rounded-lg px-2 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--card-hover)]">
                        <FileText className="h-3.5 w-3.5 shrink-0 text-cyan-400" />
                        <span className="min-w-0 flex-1 truncate">{document.filename}</span>
                        <span className={document.status === 'ready' ? 'text-emerald-500' : 'text-amber-500'}>{document.status}</span>
                        <button type="button" onClick={() => void deleteDocument(collection.id, document.id)} className="p-1 text-[var(--text-muted)] opacity-0 hover:text-rose-400 group-hover:opacity-100" aria-label="Delete document"><Trash2 className="h-3 w-3" /></button>
                      </div>
                    ))}
                  </div>
                  <button type="button" disabled={uploadingTo === collection.id} onClick={() => chooseFile(collection.id)} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--card-bg)] py-2.5 text-xs font-medium text-[var(--text-secondary)] shadow-sm transition hover:border-cyan-400/30 hover:bg-[var(--card-hover)] hover:text-[var(--text-primary)] disabled:opacity-50">
                    {uploadingTo === collection.id ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5 text-cyan-400" />}
                    {uploadingTo === collection.id ? 'Extracting and indexing…' : 'Add document'}
                  </button>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
