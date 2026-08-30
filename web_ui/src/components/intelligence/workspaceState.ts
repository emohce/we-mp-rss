export type HubMode = 'inbox' | 'digest' | 'learning' | 'system'
export interface HubFilters {
  search: string
  source_id: string
  topic: string
  state_filter: '' | 'favorite' | 'unread' | 'hidden'
  min_relevance: number
  order: 'relevance' | 'newest'
  date_from?: number
  date_to?: number
}
export interface HubState {
  visible: boolean
  mode: HubMode
  articleId: string | null
  focusedId: string | null
  width: number
  selectedDate: string
  filters: HubFilters
}
export const defaultFilters = (): HubFilters => ({
  search: '', source_id: '', topic: '', state_filter: '', min_relevance: 0, order: 'relevance'
})
export function shanghaiDate(now = new Date()): string {
  const parts = new Intl.DateTimeFormat('en', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now)
  const get = (type: string) => parts.find(part => part.type === type)?.value || ''
  return `${get('year')}-${get('month')}-${get('day')}`
}
export const initialState = (): HubState => ({
  visible: false, mode: 'inbox', articleId: null, focusedId: null,
  width: 980, selectedDate: shanghaiDate(), filters: defaultFilters()
})
export function clampWidth(value: number, viewport = 1600): number {
  return Math.max(Math.min(560, viewport), Math.min(1440, viewport - 16, Number.isFinite(value) ? value : 980))
}
export function restoreState(raw: string | null): Partial<HubState> {
  try {
    const parsed = JSON.parse(raw || '{}')
    if (parsed.version !== 3) return {}
    const filters = defaultFilters()
    for (const key of ['search', 'source_id', 'topic'] as const) {
      if (typeof parsed.filters?.[key] === 'string') filters[key] = parsed.filters[key].slice(0, key === 'source_id' ? 255 : 120)
    }
    if (['', 'favorite', 'unread', 'hidden'].includes(parsed.filters?.state_filter)) filters.state_filter = parsed.filters.state_filter
    if (parsed.filters?.order === 'newest') filters.order = 'newest'
    const score = Number(parsed.filters?.min_relevance)
    filters.min_relevance = Number.isFinite(score) ? Math.max(0, Math.min(1, score)) : 0
    for (const key of ['date_from', 'date_to'] as const) {
      if (Number.isInteger(parsed.filters?.[key]) && parsed.filters[key] >= 0) filters[key] = parsed.filters[key]
    }
    return {
      mode: ['inbox', 'digest', 'learning', 'system'].includes(parsed.mode) ? parsed.mode : 'inbox',
      width: clampWidth(Number(parsed.width)), filters,
      selectedDate: /^\d{4}-\d{2}-\d{2}$/.test(parsed.selectedDate || '') ? parsed.selectedDate : shanghaiDate()
    }
  } catch { return {} }
}
export function preferenceKey(userId: string, workspaceId: string): string {
  return `intelligence:v3:${encodeURIComponent(userId)}:${encodeURIComponent(workspaceId)}`
}
export function serializeState(state: HubState): string {
  return JSON.stringify({ version: 3, mode: state.mode, width: state.width, selectedDate: state.selectedDate, filters: state.filters })
}
export function escapeSurface(state: HubState): 'reader' | 'workspace' {
  if (state.articleId) { state.articleId = null; return 'reader' }
  state.visible = false
  return 'workspace'
}
export function focusAfterRemoval(ids: string[], removed: string): string | null {
  const index = ids.indexOf(removed)
  return ids[index + 1] || ids[index - 1] || null
}
export class RequestFence {
  private epoch = 0
  private counters = new Map<string, number>()
  begin(key: string) {
    const sequence = (this.counters.get(key) || 0) + 1
    this.counters.set(key, sequence)
    return { key, sequence, epoch: this.epoch }
  }
  current(ticket: { key: string; sequence: number; epoch: number }) {
    return ticket.epoch === this.epoch && ticket.sequence === this.counters.get(ticket.key)
  }
  invalidate(key?: string) {
    if (key) this.begin(key)
    else { this.epoch += 1; this.counters.clear() }
  }
}
export function readerDocument(body: string): string {
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; media-src 'none'; style-src 'unsafe-inline'; font-src data:; base-uri 'none'; form-action 'none'"><style>body{margin:0;padding:18px;font:16px/1.8 system-ui,-apple-system,'PingFang SC',sans-serif;color:#252a32;overflow-wrap:anywhere}img{max-width:100%;height:auto}pre{white-space:pre-wrap}table{max-width:100%}a{color:#315f3b}</style></head><body>${sanitizeReaderFragment(body) || '<p>正文尚未保存。可下载现有元数据，或主动打开原文。</p>'}</body></html>`
}
export function sanitizeReaderFragment(body: string): string {
  // Template contents are inert: parsing does not attach remote resources to
  // the live page. Strip navigation too; CSP default-src does not stop refresh.
  if (typeof document === 'undefined') return body.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const template = document.createElement('template')
  template.innerHTML = body
  template.content.querySelectorAll('script,meta,base,link,iframe,object,embed,form,input,button,textarea,select,video,audio,source,svg,math,template').forEach(node => node.remove())
  template.content.querySelectorAll('*').forEach(node => {
    for (const attribute of Array.from(node.attributes)) {
      const name = attribute.name.toLowerCase()
      if (name.startsWith('on') || ['href', 'xlink:href', 'srcset', 'ping', 'action', 'formaction', 'background', 'poster', 'srcdoc'].includes(name)
        || (name === 'src' && !(node.tagName === 'IMG' && /^data:image\/(png|jpeg|gif|webp);base64,/i.test(attribute.value)))) node.removeAttribute(attribute.name)
    }
  })
  return template.innerHTML
}
