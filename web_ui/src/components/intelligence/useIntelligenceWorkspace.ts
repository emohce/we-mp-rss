import { computed, onScopeDispose, reactive, ref, watch } from 'vue'
import * as defaultApi from '@/api/intelligence'
import type { DigestArchive, DigestDetail, FeedbackRecord, IntelligenceArticle, LearningStatus, PreferenceProposal, PreferenceRule, SavedFilter, SourceOption, TopicSummary, WorkspaceBootstrap } from '@/api/intelligence'
import { defaultFilters, initialState, preferenceKey, RequestFence, restoreState, serializeState, type HubMode } from './workspaceState'

// A single owner for the floating surface. Responses may update only the scope
// and request generation that issued them; closing is not server-side cancel.
export function useIntelligenceWorkspace(api = defaultApi, storage?: Pick<Storage, 'getItem' | 'setItem'>) {
  const state = reactive(initialState())
  const workspace = ref<WorkspaceBootstrap | null>(null)
  const ready = ref(false)
  const loading = reactive<Record<string, boolean>>({})
  const error = ref('')
  const notice = ref('')
  const articles = ref<IntelligenceArticle[]>([])
  const total = ref(0)
  const nextCursor = ref('')
  const reader = ref<IntelligenceArticle | null>(null)
  const topics = ref<TopicSummary[]>([])
  const sources = ref<SourceOption[]>([])
  const savedFilters = ref<SavedFilter[]>([])
  const digest = ref<DigestDetail | null>(null)
  const archives = ref<DigestArchive[]>([])
  const proposals = ref<PreferenceProposal[]>([])
  const rules = ref<PreferenceRule[]>([])
  const learning = ref<LearningStatus | null>(null)
  const feedback = ref<{ total: number; items: FeedbackRecord[] }>({ total: 0, items: [] })
  const infrastructure = ref<Record<string, any> | null>(null)
  const subscriptions = ref<Array<Record<string, any>>>([])
  const share = ref<{ id: string; url: string; expires_at: string } | null>(null)
  const fence = new RequestFence()
  const sourceName = (id = '') => sources.value.find(source => source.id === id)?.name || id || '未知来源'
  const scope = () => workspace.value?.id || ''

  async function run<T>(key: string, work: () => Promise<T>, apply: (value: T) => void | Promise<void>) {
    const ticket = fence.begin(key)
    loading[key] = true
    try {
      const result = await work()
      if (fence.current(ticket)) await apply(result)
    } catch (cause) {
      if (fence.current(ticket)) error.value = cause instanceof Error ? cause.message : '请求失败，请重试'
    } finally {
      if (fence.current(ticket)) loading[key] = false
    }
  }
  function invalidate() {
    fence.invalidate()
    Object.keys(loading).forEach(key => { loading[key] = false })
  }
  function closeReader() {
    fence.invalidate('reader')
    loading.reader = false
    state.articleId = null
    reader.value = null
  }
  function close() {
    state.visible = false
    ready.value = false
    closeReader()
    invalidate()
  }
  async function open() {
    invalidate()
    ready.value = false
    workspace.value = null
    reader.value = null
    state.articleId = null
    articles.value = []; digest.value = null; share.value = null
    topics.value = []; sources.value = []; savedFilters.value = []
    archives.value = []; proposals.value = []; rules.value = []; subscriptions.value = []
    learning.value = null; infrastructure.value = null; feedback.value = { total: 0, items: [] }
    total.value = 0; nextCursor.value = ''; error.value = ''; notice.value = ''
    state.visible = true
    await run('bootstrap', api.bootstrapWorkspace, async value => {
      workspace.value = value
      let restored = {}
      try { restored = restoreState(storage?.getItem(preferenceKey(value.user_id, value.id)) || null) } catch { /* Storage can be blocked. */ }
      Object.assign(state, initialState(), restored, { visible: true, articleId: null, focusedId: null })
      ready.value = true
      await Promise.all([loadCommon(), loadMode()])
    })
  }
  async function loadCommon() {
    const id = scope()
    if (!id || !ready.value) return
    await Promise.all([
      run('topics', () => api.listIntelligenceTopics(id), value => { topics.value = value }),
      run('sources', () => api.listAvailableSources(id), value => { sources.value = value }),
      run('saved', () => api.listSavedFilters(id), value => { savedFilters.value = value })
    ])
  }
  async function loadArticles(append = false) {
    const id = scope()
    if (!id || !ready.value || (append && (loading.articles || !nextCursor.value))) return
    const params = { ...state.filters, workspace_id: id, cursor: append ? nextCursor.value : '', limit: 30 }
    if (!append) { articles.value = []; nextCursor.value = '' }
    await run('articles', () => api.listIntelligenceArticles(params), page => {
      const existing = append ? articles.value : []
      const ids = new Set(existing.map(item => item.id))
      articles.value = [...existing, ...page.items.filter(item => !ids.has(item.id))]
      total.value = page.total
      nextCursor.value = page.next_cursor
    })
  }
  async function loadDigest() {
    const id = scope(), selected = state.selectedDate
    if (!id || !ready.value) return
    digest.value = null
    share.value = null
    await Promise.all([
      run('archives', () => api.listDigests(id), value => { archives.value = value }),
      run('digest', () => api.getDigest(id, selected), value => { digest.value = value })
    ])
  }
  async function selectDate(value: string) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return
    state.selectedDate = value
    fence.invalidate('share-write')
    loading['share-write'] = false
    await loadDigest()
  }
  async function loadLearning() {
    const id = scope()
    if (!id || !ready.value) return
    await Promise.all([
      run('proposals', () => api.listPreferenceProposals(id), value => { proposals.value = value }),
      run('rules', () => api.listPreferenceRules(id), value => { rules.value = value }),
      run('learning', () => api.getLearningStatus(id), value => { learning.value = value }),
      run('feedback', () => api.listFeedback(id), value => { feedback.value = value })
    ])
  }
  async function loadSystem() {
    const id = scope()
    if (!id || !ready.value) return
    await Promise.all([
      run('infrastructure', api.getIntelligenceInfrastructure, value => { infrastructure.value = value }),
      run('subscriptions', () => api.listIntelligenceSubscriptions(id), value => { subscriptions.value = value })
    ])
  }
  async function loadMode() {
    if (state.mode === 'inbox') await loadArticles()
    else if (state.mode === 'digest') await loadDigest()
    else if (state.mode === 'learning') await loadLearning()
    else await loadSystem()
  }
  async function setMode(mode: HubMode) {
    if (!ready.value || mode === state.mode) return
    closeReader()
    // Read views have distinct keys. Switching also invalidates writes' UI
    // continuations; an already accepted server action may still finish.
    invalidate()
    error.value = ''; notice.value = ''; state.mode = mode
    await Promise.all([loadCommon(), loadMode()])
  }
  async function openArticle(article: IntelligenceArticle) {
    const id = scope()
    if (!id || !ready.value) return
    state.articleId = article.id; state.focusedId = article.id
    if (reader.value?.id !== article.id) reader.value = null
    await run('reader', () => api.getIntelligenceArticle(id, article.id), value => { reader.value = value })
  }
  async function mutate(key: string, work: () => Promise<unknown>, after: () => Promise<void>, message: string) {
    if (!ready.value || loading[key]) return
    error.value = ''; notice.value = ''
    await run(key, work, async () => { notice.value = message; await after() })
  }
  async function sendFeedback(article: IntelligenceArticle, event: string, value: Record<string, unknown> = {}) {
    const id = scope()
    await mutate('feedback-write', () => api.recordIntelligenceFeedback(id, article.id, event, value), async () => {
      if (state.articleId === article.id) await openArticle(article)
      // A digest is an immutable revision snapshot; do not mix fresh mutable
      // article state into it or claim a queued revision has been published.
      if (state.mode === 'inbox') await loadArticles()
      await loadCommon()
    }, '反馈已保存；如影响已有日报，修订将由后台排队处理。')
  }
  async function analyze(article: IntelligenceArticle) {
    const id = scope()
    await mutate('analysis-write', () => api.analyzeIntelligenceArticle(id, article.id), async () => {
      if (state.articleId === article.id) await openArticle(article)
      await Promise.all([loadCommon(), state.mode === 'inbox' ? loadArticles() : Promise.resolve()])
    }, '整理结果已更新。')
  }
  async function download(article: IntelligenceArticle, format: string) {
    const id = scope()
    await run('download', () => api.downloadIntelligenceArticle(id, article.id, format), ({ blob, filename }) => {
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url; link.download = filename; link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      notice.value = '已准备下载；正文缺失时文件会说明仅含元数据。'
    })
  }
  async function saveFilter(name: string) {
    const id = scope(), filters = { ...state.filters }
    await mutate('filter-write', () => api.saveWorkspaceFilter(id, name, filters), loadCommon, '筛选已保存到当前用户的工作区。')
  }
  async function removeFilter(id: string) {
    const workspaceId = scope()
    await mutate('filter-write', () => api.deleteWorkspaceFilter(workspaceId, id), loadCommon, '已删除保存的筛选。')
  }
  function applyFilter(saved: SavedFilter) {
    const restored = restoreState(JSON.stringify({ version: 3, filters: saved.filters }))
    state.filters = { ...defaultFilters(), ...restored.filters }
    if (state.mode === 'inbox') void loadArticles()
  }
  async function createDigest() {
    const id = scope(), selected = state.selectedDate
    await mutate('digest-write', () => api.generateDigest(id, selected), loadDigest, '日报已生成或确认未变化；覆盖与修订号以返回结果为准。')
  }
  // Keep the capability URL available for manual copying even if the browser
  // clipboard API is unavailable. It is never written to localStorage.
  async function createShareLink() {
    const id = scope(), selected = state.selectedDate
    if (!ready.value || loading['share-write']) return
    await run('share-write', () => api.shareDigest(id, selected), value => { share.value = value; notice.value = '链接有效期 7 天，可在此撤销。持有链接的人可查看此日报。' })
  }
  async function revokeShare() {
    if (!share.value) return
    const id = scope(), shareId = share.value.id
    await mutate('share-write', () => api.revokeDigestShare(id, shareId), async () => { share.value = null }, '分享链接已撤销。')
  }
  async function propose() {
    const id = scope()
    await mutate('rule-write', () => api.generatePreferenceProposals(id), loadLearning, '已检查全部反馈历史；建议需逐条批准才会生效。')
  }
  async function review(id: string, approve: boolean) {
    const workspaceId = scope()
    await mutate('rule-write', () => api.reviewPreferenceProposal(workspaceId, id, approve), loadLearning, approve ? '规则已批准，后续排序应用此规则。' : '建议已拒绝。')
  }
  async function revokeRule(id: string) {
    const workspaceId = scope()
    await mutate('rule-write', () => api.revokePreferenceRule(workspaceId, id), loadLearning, '规则已撤销；历史反馈与版本记录保留。')
  }
  async function subscribe(sourceId: string) {
    const id = scope()
    await mutate('subscription-write', () => api.createIntelligenceSubscription(id, sourceId), loadSystem, '订阅已保存并排队；不会在当前页面直接请求微信。')
  }
  async function toggleSubscription(subscription: Record<string, any>) {
    const id = scope()
    await mutate('subscription-write', () => api.updateSubscription(id, subscription.id, subscription.status === 'active' ? 'paused' : 'active'), loadSystem,
      '订阅状态已更新，仅影响后续每日计划；当日已冻结的来源与在途任务保留。')
  }
  const backfillRequests = new Map<string, string>()
  async function backfill(subscriptionId: string) {
    const id = scope(), key = `${id}:${subscriptionId}`
    const requestId = backfillRequests.get(key) || globalThis.crypto.randomUUID()
    backfillRequests.set(key, requestId)
    await mutate('subscription-write', () => api.enqueueBackfill(id, subscriptionId, requestId), async () => { await loadSystem() },
      '已请求最多 3 页回填；重复点击复用本次请求，不重复创建任务。关闭并重开浮窗后可发起下一批。')
  }
  async function importBatch() {
    if (!ready.value || !workspace.value?.can_import_legacy || loading['legacy-write']) return
    const id = scope()
    await run('legacy-write', () => api.importLegacyBatch(id), async result => {
      notice.value = `本批关联 ${result.attached} 篇；${result.has_more ? '仍有历史文章，确认后可再执行一批' : '当前批次已处理完毕'}。不会自动继续。`
      await loadCommon()
    })
  }
  const digestItems = computed(() => {
    const filter = state.filters
    return (digest.value?.items || []).filter(({ article }) =>
      (!filter.source_id || article.mp_id === filter.source_id) &&
      (!filter.topic || article.topics?.some(topic => topic.slug === filter.topic || topic.name === filter.topic)) &&
      (!filter.search || `${article.title || ''} ${article.ai_summary || ''} ${article.description || ''}`.toLowerCase().includes(filter.search.toLowerCase())) &&
      (article.effective_relevance ?? article.ai_relevance ?? 0.5) >= filter.min_relevance
    )
  })
  watch(() => serializeState(state), value => {
    if (!ready.value || !workspace.value) return
    try { storage?.setItem(preferenceKey(workspace.value.user_id, workspace.value.id), value) } catch { /* Persistence is optional. */ }
  })
  watch(() => state.visible, visible => { if (!visible) backfillRequests.clear() })
  onScopeDispose(() => { invalidate() })
  return { state, workspace, ready, loading, error, notice, articles, total, nextCursor, reader, topics, sources, savedFilters, digest, archives, proposals, rules, learning, feedback, infrastructure, subscriptions, share, digestItems, sourceName,
    open, close, closeReader, setMode, loadMode, loadArticles, loadDigest, selectDate, openArticle, sendFeedback, analyze, download, saveFilter, removeFilter, applyFilter, createDigest, createShareLink, revokeShare, propose, review, revokeRule, subscribe, toggleSubscription, backfill, importBatch }
}
