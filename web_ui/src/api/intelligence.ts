import axios, { type AxiosRequestConfig } from 'axios'
import { getToken } from '@/utils/auth'

const configuredBase = String(import.meta.env.VITE_API_BASE_URL || '').replace(/\/?$/, '/')
const client = axios.create({
  baseURL: `${configuredBase}api/v2/intelligence/`,
  timeout: 100000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json'
  }
})

client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  try {
    const response = await client.request(config)
    if (response.data?.code === 0) return response.data.data as T
    const detail = response.data?.detail || response.data
    throw new Error(detail?.message || '智能聚合请求失败')
  } catch (error: any) {
    const detail = error?.response?.data?.detail || error?.response?.data
    const message = typeof detail === 'string' ? detail : detail?.message
    throw new Error(message || (Array.isArray(detail) ? '请求参数不符合要求，请检查输入。' : error?.message) || '智能聚合请求失败')
  }
}

export interface WorkspaceBootstrap {
  id: string
  name: string
  slug: string
  user_id: string
  can_import_legacy: boolean
  legacy_backfill: { attached: number; has_more: boolean; skipped?: string }
}

export interface TopicSummary {
  slug: string
  name: string
  article_count: number
  average_confidence?: number
}

export interface IntelligenceArticle {
  id: string
  mp_id?: string
  title?: string
  description?: string
  content?: string
  content_html?: string
  url?: string
  pic_url?: string
  publish_time?: number
  is_read: boolean
  is_favorite: boolean
  is_hidden: boolean
  feedback_sentiment: string
  ai_summary: string
  ai_relevance: number
  effective_relevance: number
  ai_reason: string
  rank_reason?: string
  display_collapsed?: boolean
  content_status?: 'stored' | 'legacy' | 'metadata_only' | 'unavailable'
  content_warning?: string
  summary_style?: string
  topics: Array<{ slug: string; name: string; confidence: number }>
}

export interface ArticlePage {
  items: IntelligenceArticle[]
  next_cursor: string
  has_more: boolean
  total: number
}

export interface DigestItem {
  rank: number
  relevance_score: number
  reason: string
  is_late: boolean
  article: IntelligenceArticle
}

export interface DigestDetail {
  id: string
  date: string
  title: string
  summary: string
  status: string
  generated_at?: string
  items: DigestItem[]
  revision: number
  coverage: DigestCoverage
}

export interface DigestArchive {
  id: string
  date: string
  title: string
  summary: string
  status: string
  generated_at?: string
  item_count: number
  revision: number
  coverage: DigestCoverage
}

export interface DigestCoverage {
  expected: number
  completed: number
  pending: number
  partial: number
  failed: number
  skipped: number
  complete: boolean
  analysis_pending: number
  analysis_failed: number
  sources: Array<{ provider: string; source_id: string; state: string; reason: string }>
}
export interface SavedFilter { id: string; name: string; filters: Record<string, unknown> }
export interface PreferenceRule {
  id: string; rule_type: string; condition: Record<string, unknown>; action: Record<string, unknown>
  version: number; is_active: boolean; revoked_at?: string
}
export interface SourceOption { id: string; name: string; provider: string }
export interface FeedbackRecord { id: string; article_id: string; event_type: string; value: Record<string, unknown>; created_at: string }
export interface LearningStatus { events: number; distinct_articles: number; span_days: number; eligible: boolean; history_scope: string }

export interface PreferenceProposal {
  id: string
  status: string
  rule_type: string
  condition: Record<string, unknown>
  action: Record<string, unknown>
  confidence: number
  evidence: string[]
  created_at: string
}

export const bootstrapWorkspace = () =>
  request<WorkspaceBootstrap>({ method: 'POST', url: 'workspaces/bootstrap' })

export const listIntelligenceArticles = (params: Record<string, unknown>) =>
  request<ArticlePage>({ method: 'GET', url: 'articles', params })

export const getIntelligenceArticle = (workspaceId: string, articleId: string) =>
  request<IntelligenceArticle>({
    method: 'GET',
    url: `articles/${encodeURIComponent(articleId)}`,
    params: { workspace_id: workspaceId }
  })

export const analyzeIntelligenceArticle = (workspaceId: string, articleId: string) =>
  request<Record<string, unknown>>({
    method: 'POST',
    url: `articles/${encodeURIComponent(articleId)}/analyze`,
    params: { workspace_id: workspaceId }
  })

export const recordIntelligenceFeedback = (
  workspaceId: string,
  articleId: string,
  eventType: string,
  value: Record<string, unknown> = {}
) =>
  request<Record<string, unknown>>({
    method: 'POST',
    url: `articles/${encodeURIComponent(articleId)}/feedback`,
    params: { workspace_id: workspaceId },
    data: { event_type: eventType, value }
  })

export async function downloadIntelligenceArticle(
  workspaceId: string,
  articleId: string,
  format: string
): Promise<{ blob: Blob; filename: string }> {
  const response = await client.get(`articles/${encodeURIComponent(articleId)}/download`, {
    params: { workspace_id: workspaceId, format },
    responseType: 'blob'
  })
  const disposition = String(response.headers['content-disposition'] || '')
  const encodedName = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  return {
    blob: response.data,
    filename: encodedName ? decodeURIComponent(encodedName) : `article.${format}`
  }
}

export const listIntelligenceTopics = (workspaceId: string) =>
  request<TopicSummary[]>({
    method: 'GET',
    url: 'topics',
    params: { workspace_id: workspaceId }
  })

export const generateDigest = (workspaceId: string, digestDate: string) =>
  request<DigestDetail>({
    method: 'POST',
    url: `digests/${digestDate}/generate`,
    params: { workspace_id: workspaceId }
  })

export const getDigest = (workspaceId: string, digestDate: string) =>
  request<DigestDetail>({
    method: 'GET',
    url: `digests/${digestDate}`,
    params: { workspace_id: workspaceId }
  })

export const listDigests = (workspaceId: string) =>
  request<DigestArchive[]>({
    method: 'GET',
    url: 'digests',
    params: { workspace_id: workspaceId, limit: 90 }
  })

export const shareDigest = (workspaceId: string, digestDate: string) =>
  request<{ id: string; url: string; expires_at: string }>({
    method: 'POST',
    url: `digests/${digestDate}/share`,
    params: { workspace_id: workspaceId },
    data: { expires_in_hours: 168 }
  })

export const listPreferenceProposals = (workspaceId: string) =>
  request<PreferenceProposal[]>({
    method: 'GET',
    url: 'preference-proposals',
    params: { workspace_id: workspaceId, status: 'pending' }
  })

export const generatePreferenceProposals = (workspaceId: string) =>
  request<PreferenceProposal[]>({
    method: 'POST',
    url: 'preference-proposals/generate',
    params: { workspace_id: workspaceId }
  })

export const reviewPreferenceProposal = (
  workspaceId: string,
  proposalId: string,
  approve: boolean
) =>
  request<PreferenceProposal>({
    method: 'POST',
    url: `preference-proposals/${encodeURIComponent(proposalId)}/review`,
    params: { workspace_id: workspaceId },
    data: { approve }
  })

export const getIntelligenceInfrastructure = () =>
  request<Record<string, any>>({ method: 'GET', url: 'infrastructure' })

export const listIntelligenceSubscriptions = (workspaceId: string) =>
  request<Array<Record<string, any>>>({
    method: 'GET',
    url: 'subscriptions',
    params: { workspace_id: workspaceId }
  })

export const createIntelligenceSubscription = (workspaceId: string, sourceId: string) =>
  request<Record<string, any>>({
    method: 'POST',
    url: 'subscriptions',
    params: { workspace_id: workspaceId },
    data: { source_id: sourceId, provider: 'we-mp-rss' }
  })

export const listSavedFilters = (workspaceId: string) => request<SavedFilter[]>({ method: 'GET', url: 'saved-filters', params: { workspace_id: workspaceId } })
export const saveWorkspaceFilter = (workspaceId: string, name: string, filters: Record<string, unknown>) => request<SavedFilter>({ method: 'POST', url: 'saved-filters', params: { workspace_id: workspaceId }, data: { name, filters } })
export const deleteWorkspaceFilter = (workspaceId: string, id: string) => request({ method: 'DELETE', url: `saved-filters/${encodeURIComponent(id)}`, params: { workspace_id: workspaceId } })
export const listPreferenceRules = (workspaceId: string) => request<PreferenceRule[]>({ method: 'GET', url: 'preference-rules', params: { workspace_id: workspaceId } })
export const revokePreferenceRule = (workspaceId: string, id: string) => request({ method: 'POST', url: `preference-rules/${encodeURIComponent(id)}/revoke`, params: { workspace_id: workspaceId } })
export const getLearningStatus = (workspaceId: string) => request<LearningStatus>({ method: 'GET', url: 'learning-status', params: { workspace_id: workspaceId } })
export const listFeedback = (workspaceId: string, articleId = '') => request<{ total: number; items: FeedbackRecord[] }>({ method: 'GET', url: 'feedback', params: { workspace_id: workspaceId, article_id: articleId, limit: 30 } })
export const listAvailableSources = (workspaceId: string, search = '') => request<SourceOption[]>({ method: 'GET', url: 'sources/available', params: { workspace_id: workspaceId, search } })
export const updateSubscription = (workspaceId: string, id: string, status: string) => request({ method: 'PATCH', url: `subscriptions/${encodeURIComponent(id)}`, params: { workspace_id: workspaceId }, data: { status } })
export const enqueueBackfill = (workspaceId: string, id: string, requestId: string) => request({ method: 'POST', url: `subscriptions/${encodeURIComponent(id)}/backfill`, params: { workspace_id: workspaceId }, data: { request_id: requestId, page_budget: 3 } })
export const importLegacyBatch = (workspaceId: string) => request<{ attached: number; has_more: boolean }>({ method: 'POST', url: `workspaces/${encodeURIComponent(workspaceId)}/legacy-import`, data: { confirm: true, batch_size: 200 } })
export const revokeDigestShare = (workspaceId: string, id: string) => request({ method: 'POST', url: `shares/${encodeURIComponent(id)}/revoke`, params: { workspace_id: workspaceId } })
