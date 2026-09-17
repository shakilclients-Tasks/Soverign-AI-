import { Check, Copy, Sparkles, TriangleAlert } from 'lucide-react'
import { isValidElement, useState, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import remarkGfm from 'remark-gfm'
import type { Message } from '../../types/api'
import { StreamingMessage } from './StreamingMessage'
import { getSovereignModelDisplayName } from '../../utils/modelNames'

function cleanCitations(content: string): string {
  if (!content) return ''
  return content
    .replace(/\s*\[Document:\s*(?:<[^>]+>|general\s+knowledge|n\/?a|unknown|none)[^\]]*\]\s*([.,;])?/gi, '$1')
    .replace(/\s+([.,;])/g, '$1')
}

export function ChatMessage({ message }: { message: Message }) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'
  const displayContent = isUser ? message.content : cleanCitations(message.content)

  const copy = async () => {
    await navigator.clipboard.writeText(displayContent)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  return (
    <article className={`group mx-auto flex w-full max-w-3xl gap-4 px-5 py-5 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={isUser ? 'max-w-[85%]' : 'w-full'}>
        {!isUser && (
          <div className="mb-2.5 flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
            <div className="flex items-center gap-2">
              <span className={`grid h-6 w-6 place-items-center rounded-lg border border-cyan-300/25 bg-cyan-300/[0.08] ${message.streaming ? 'animate-avatar-halo ring-2 ring-cyan-400/40' : ''}`}>
                <span className="h-2 w-2 rounded-sm bg-cyan-400" />
              </span>
              <span className="text-[var(--text-primary)]">Sovereign AI</span>
              {message.model && <span className="font-normal text-[var(--text-muted)]">· {getSovereignModelDisplayName(message.model)}</span>}
            </div>

            {message.streaming && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-2.5 py-0.5 text-[10px] font-semibold text-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.15)] animate-pulse">
                <Sparkles className="h-3 w-3" />
                Live streaming
              </span>
            )}
          </div>
        )}

        <div className={isUser
          ? 'rounded-2xl rounded-br-md border px-4 py-3 text-sm leading-6 shadow-sm transition-colors duration-200'
          : `markdown-body relative rounded-2xl p-4 text-[15px] leading-7 transition-all duration-300 ${
              message.streaming
                ? 'border border-cyan-400/30 bg-cyan-400/[0.02] shadow-[0_0_24px_rgba(34,211,238,0.08)]'
                : 'border border-transparent'
            } ${message.error ? 'text-rose-400' : ''}`
        }
        style={isUser ? {
          backgroundColor: 'var(--user-bubble-bg)',
          borderColor: 'var(--user-bubble-border)',
          color: 'var(--user-bubble-text)'
        } : undefined}
        >
          {message.error && <TriangleAlert className="mr-2 inline h-4 w-4 text-rose-400" />}
          {isUser ? message.content : message.streaming && !message.content ? (
            <StreamingMessage waiting />
          ) : (
            <>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{ pre: ({ children }) => <CodeBlock>{children}</CodeBlock> }}
              >
                {displayContent}
              </ReactMarkdown>
              {message.streaming && <StreamingMessage />}
            </>
          )}
        </div>

        {!isUser && message.sources.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {message.sources.map((source, index) => (
              <div
                key={`${source.id || source.title}-${index}`}
                title={source.snippet || undefined}
                className="rounded-lg border border-[var(--border-subtle)] bg-[var(--card-bg)] px-2.5 py-1.5 text-[11px] text-[var(--text-secondary)] shadow-sm transition hover:border-cyan-400/30"
              >
                {source.title}{source.page ? ` · p. ${source.page}` : ''}
              </div>
            ))}
          </div>
        )}

        {!message.streaming && message.content && (
          <button
            type="button"
            onClick={copy}
            className={`mt-2 inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-[var(--text-muted)] transition hover:bg-[var(--card-hover)] hover:text-[var(--text-primary)] ${isUser ? 'float-right' : ''}`}
          >
            {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        )}
      </div>
    </article>
  )
}

function textContent(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textContent).join('')
  if (isValidElement<{ children?: ReactNode }>(node)) return textContent(node.props.children)
  return ''
}

function CodeBlock({ children }: { children: ReactNode }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(textContent(children).replace(/\n$/, ''))
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div className="code-block group/code relative my-4 overflow-hidden rounded-xl">
      <pre className="m-0 border border-[var(--code-border)] bg-[var(--code-bg)] p-4 text-[13px] leading-6 text-[var(--code-text)]">
        {children}
      </pre>
      <button
        type="button"
        onClick={copy}
        className="absolute right-2 top-2 flex items-center gap-1 rounded-md border border-[var(--border-subtle)] bg-[var(--card-bg)] px-2 py-1 text-[10px] text-[var(--text-muted)] opacity-0 shadow-sm transition hover:text-[var(--text-primary)] group-hover/code:opacity-100"
      >
        {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
        {copied ? 'Copied' : 'Copy code'}
      </button>
    </div>
  )
}
