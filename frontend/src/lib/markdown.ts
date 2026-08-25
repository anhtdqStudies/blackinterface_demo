import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

/** LLM prose → sanitized HTML for `v-html`. */
export function renderMarkdown(source: string): string {
  const trimmed = source.trim()
  if (!trimmed) return ''
  const html = marked.parse(trimmed, { async: false }) as string
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
}
