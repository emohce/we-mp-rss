<template>
  <button
    class="intelligence-fab"
    type="button"
    aria-label="打开智能聚合浮窗"
    title="智能聚合"
    @click="openHub"
  >
    <span class="fab-mark">AI</span>
    <span class="fab-label">聚合</span>
  </button>

  <a-drawer
    v-model:visible="visible"
    class="intelligence-drawer"
    placement="right"
    :width="isMobile ? '100%' : '720px'"
    :footer="false"
    :unmount-on-close="false"
  >
    <template #title>
      <div class="hub-title">
        <div>
          <strong>公众号智能聚合</strong>
          <small>{{ workspace?.name || '正在准备个人工作区' }}</small>
        </div>
        <a-tag v-if="infrastructure?.profile" color="green">{{ profileLabel }}</a-tag>
      </div>
    </template>

    <div class="hub-shell">
      <a-alert v-if="errorMessage" type="warning" closable @close="errorMessage = ''">
        {{ errorMessage }}
      </a-alert>
      <a-alert
        v-if="workspace?.legacy_backfill?.has_more"
        type="info"
        closable
      >
        历史文章正按批次关联；下次打开浮窗会继续，不阻塞本次浏览。
      </a-alert>

      <a-radio-group v-model="mode" type="button" class="hub-mode" @change="handleModeChange">
        <a-radio value="inbox">今日收件箱</a-radio>
        <a-radio value="digest">日期汇总</a-radio>
        <a-radio value="learning">偏好学习</a-radio>
        <a-radio value="system">运行状态</a-radio>
      </a-radio-group>

      <a-spin :loading="loading" class="hub-loading" tip="正在整理内容…">
        <section v-if="mode === 'inbox'" class="hub-view">
          <div class="filter-panel">
            <a-input-search
              v-model="filters.search"
              allow-clear
              placeholder="搜索标题或摘要"
              @search="reloadArticles"
              @press-enter="reloadArticles"
            />
            <div class="filter-row">
              <a-select
                v-model="filters.topic"
                allow-clear
                placeholder="全部主题"
                @change="reloadArticles"
              >
                <a-option v-for="topic in topics" :key="topic.slug" :value="topic.slug">
                  {{ topic.name }} · {{ topic.article_count }}
                </a-option>
              </a-select>
              <a-select
                v-model="filters.state"
                placeholder="全部文章"
                @change="reloadArticles"
              >
                <a-option value="">全部文章</a-option>
                <a-option value="unread">未读</a-option>
                <a-option value="favorite">收藏</a-option>
                <a-option value="hidden">已隐藏</a-option>
              </a-select>
            </div>
            <div class="relevance-filter">
              <span>最低相关度</span>
              <a-slider
                v-model="filters.minRelevance"
                :min="0"
                :max="1"
                :step="0.1"
                :style="{ flex: 1 }"
                @change="reloadArticles"
              />
              <b>{{ Math.round(filters.minRelevance * 100) }}%</b>
            </div>
          </div>

          <div class="view-heading">
            <div>
              <span class="eyebrow">INBOX</span>
              <h3>按兴趣而非按页面浏览</h3>
            </div>
            <a-button size="small" @click="reloadArticles">
              <template #icon><icon-refresh /></template>
              刷新
            </a-button>
          </div>

          <a-empty v-if="!articles.length && !loading" description="当前条件下暂无文章" />
          <div v-else class="article-stack">
            <article v-for="article in articles" :key="article.id" class="article-card">
              <div class="article-meta">
                <span>{{ article.mp_id || '未知公众号' }}</span>
                <time>{{ formatPublishTime(article.publish_time) }}</time>
                <span class="relevance">{{ Math.round((article.effective_relevance ?? article.ai_relevance ?? 0.5) * 100) }}%</span>
              </div>
              <button class="article-title" type="button" @click="openArticle(article)">
                {{ article.title || '未命名文章' }}
              </button>
              <p>{{ article.ai_summary || article.description || '尚未生成摘要' }}</p>
              <div class="topic-row">
                <a-tag
                  v-for="topic in article.topics || []"
                  :key="topic.slug"
                  size="small"
                  color="arcoblue"
                  @click="selectTopic(topic.slug)"
                >
                  {{ topic.name }}
                </a-tag>
              </div>
              <div class="article-actions">
                <a-button
                  size="mini"
                  :type="article.feedback_sentiment === 'like' ? 'primary' : 'secondary'"
                  @click="sendFeedback(article, 'like')"
                >有用</a-button>
                <a-button
                  size="mini"
                  :status="article.feedback_sentiment === 'dislike' ? 'danger' : 'normal'"
                  @click="sendFeedback(article, 'dislike')"
                >不感兴趣</a-button>
                <a-button size="mini" @click="toggleFavorite(article)">
                  {{ article.is_favorite ? '★ 已收藏' : '☆ 收藏' }}
                </a-button>
                <a-button size="mini" @click="analyzeArticle(article)">智能整理</a-button>
                <a-dropdown trigger="click">
                  <a-button size="mini">
                    <template #icon><icon-download /></template>
                    下载
                  </a-button>
                  <template #content>
                    <a-doption
                      v-for="format in downloadFormats"
                      :key="format"
                      @click="downloadArticle(article, format)"
                    >
                      {{ format.toUpperCase() }}
                    </a-doption>
                  </template>
                </a-dropdown>
                <a-button size="mini" status="danger" @click="hideArticle(article)">隐藏</a-button>
              </div>
            </article>
          </div>
          <a-button
            v-if="nextCursor"
            class="load-more"
            long
            :loading="loadingMore"
            @click="loadMore"
          >继续加载</a-button>
        </section>

        <section v-else-if="mode === 'digest'" class="hub-view digest-view">
          <div class="date-toolbar">
            <label>
              <span>汇总日期</span>
              <input v-model="selectedDate" type="date" @change="loadSelectedDigest" />
            </label>
            <a-space>
              <a-button type="primary" @click="createDigest">生成 / 重新生成</a-button>
              <a-button :disabled="!digest" @click="createShareLink">
                <template #icon><icon-share-external /></template>
                分享链接
              </a-button>
            </a-space>
          </div>

          <div class="digest-layout">
            <aside class="archive-rail">
              <span class="eyebrow">ARCHIVE</span>
              <button
                v-for="archive in archives"
                :key="archive.id"
                type="button"
                :class="{ active: archive.date === selectedDate }"
                @click="selectArchive(archive.date)"
              >
                <b>{{ archive.date }}</b>
                <small>{{ archive.item_count }} 篇</small>
              </button>
              <a-empty v-if="!archives.length" description="暂无历史日报" />
            </aside>
            <main class="digest-paper">
              <template v-if="digest">
                <span class="eyebrow">{{ digest.date }}</span>
                <h2>{{ digest.title }}</h2>
                <p class="digest-summary">{{ digest.summary }}</p>
                <article
                  v-for="item in digest.items"
                  :key="item.article.id"
                  class="digest-item"
                  @click="openArticle(item.article)"
                >
                  <span>{{ String(item.rank).padStart(2, '0') }}</span>
                  <div>
                    <h4>{{ item.article.title }}</h4>
                    <p>{{ item.article.ai_summary || item.article.description }}</p>
                    <small>{{ item.reason }}</small>
                  </div>
                </article>
              </template>
              <a-empty v-else description="选择日期后生成日报" />
            </main>
          </div>
        </section>

        <section v-else-if="mode === 'learning'" class="hub-view">
          <div class="learning-hero">
            <span class="eyebrow">FEEDBACK → RULE</span>
            <h3>系统只提出规则，你决定是否采用</h3>
            <p>至少 20 篇不同文章、跨 7 天形成稳定信号后，才会提出来源偏好；不会静默改变排序。</p>
            <a-button type="primary" @click="refreshPreferenceProposals">从现有反馈提取规则</a-button>
          </div>
          <a-empty v-if="!proposals.length" description="暂无待确认的偏好建议" />
          <article v-for="proposal in proposals" :key="proposal.id" class="proposal-card">
            <div>
              <a-tag color="orangered">置信度 {{ Math.round(proposal.confidence * 100) }}%</a-tag>
              <h4>{{ proposalTitle(proposal) }}</h4>
              <p>{{ proposalDescription(proposal) }}</p>
              <small>证据记录 {{ proposal.evidence?.length || 0 }} 条</small>
            </div>
            <a-space direction="vertical">
              <a-button type="primary" size="small" @click="reviewProposal(proposal, true)">
                <template #icon><icon-check /></template>
                采用
              </a-button>
              <a-button size="small" @click="reviewProposal(proposal, false)">
                <template #icon><icon-close /></template>
                拒绝
              </a-button>
            </a-space>
          </article>
        </section>

        <section v-else class="hub-view">
          <div class="system-grid">
            <article class="status-card">
              <span>存储档位</span>
              <strong>{{ profileLabel }}</strong>
              <small>{{ infrastructure?.database || 'unknown' }} · {{ infrastructure?.content_backend || 'local' }}</small>
            </article>
            <article class="status-card">
              <span>Redis 协调</span>
              <strong>{{ infrastructure?.redis_enabled ? '已配置' : '未配置' }}</strong>
              <small>仅用于缓存、锁、令牌桶和唤醒</small>
            </article>
            <article class="status-card">
              <span>MQTT 事件</span>
              <strong>{{ infrastructure?.mqtt_enabled ? '已配置' : '未配置' }}</strong>
              <small>只传紧凑事件，正文仍在持久存储</small>
            </article>
            <article class="status-card">
              <span>每日节奏</span>
              <strong>06:30 → 08:00</strong>
              <small>07:50 截止，Asia/Shanghai</small>
            </article>
          </div>
          <a-alert v-if="infrastructure && !infrastructure.valid" type="warning">
            当前档位尚未就绪：{{ (infrastructure.issues || []).join('；') }}
          </a-alert>
          <div class="subscription-box">
            <div class="view-heading">
              <div>
                <span class="eyebrow">SOURCES</span>
                <h3>智能聚合订阅</h3>
              </div>
            </div>
            <div class="subscribe-row">
              <a-input v-model="newSourceId" allow-clear placeholder="公众号稳定 ID" />
              <a-button type="primary" :disabled="!newSourceId.trim()" @click="subscribeSource">订阅</a-button>
            </div>
            <div class="subscription-list">
              <div v-for="subscription in subscriptions" :key="subscription.id">
                <div>
                  <b>{{ subscription.source_id }}</b>
                  <small>{{ subscription.provider }} · {{ subscription.discovery_mode }}</small>
                </div>
                <a-tag :color="subscription.status === 'active' ? 'green' : 'gray'">
                  {{ subscription.status }}
                </a-tag>
              </div>
            </div>
          </div>
        </section>
      </a-spin>
    </div>
  </a-drawer>

  <a-modal
    v-model:visible="readerVisible"
    class="intelligence-reader"
    :width="isMobile ? '96%' : '860px'"
    :footer="false"
    unmount-on-close
  >
    <template #title>{{ currentArticle?.title || '文章详情' }}</template>
    <div v-if="currentArticle" class="reader-shell">
      <div class="reader-toolbar">
        <a-space wrap>
          <a-tag v-for="topic in currentArticle.topics || []" :key="topic.slug" color="arcoblue">
            {{ topic.name }}
          </a-tag>
        </a-space>
        <a-link v-if="safeCurrentArticleUrl" :href="safeCurrentArticleUrl" target="_blank">查看原文</a-link>
      </div>
      <div v-if="currentArticle.ai_summary" class="reader-summary">
        <b>智能摘要</b>
        <p>{{ currentArticle.ai_summary }}</p>
      </div>
      <iframe
        class="reader-frame"
        sandbox=""
        referrerpolicy="no-referrer"
        :srcdoc="readerDocument"
        title="文章正文"
      />
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  IconCheck,
  IconClose,
  IconDownload,
  IconRefresh,
  IconShareExternal
} from '@arco-design/web-vue/es/icon'
import {
  analyzeIntelligenceArticle,
  bootstrapWorkspace,
  createIntelligenceSubscription,
  downloadIntelligenceArticle,
  generateDigest,
  generatePreferenceProposals,
  getDigest,
  getIntelligenceArticle,
  getIntelligenceInfrastructure,
  listDigests,
  listIntelligenceArticles,
  listIntelligenceSubscriptions,
  listIntelligenceTopics,
  listPreferenceProposals,
  recordIntelligenceFeedback,
  reviewPreferenceProposal,
  shareDigest,
  type DigestArchive,
  type DigestDetail,
  type IntelligenceArticle,
  type PreferenceProposal,
  type TopicSummary,
  type WorkspaceBootstrap
} from '@/api/intelligence'

type HubMode = 'inbox' | 'digest' | 'learning' | 'system'

const visible = ref(false)
const readerVisible = ref(false)
const loading = ref(false)
const loadingMore = ref(false)
const errorMessage = ref('')
const workspace = ref<WorkspaceBootstrap | null>(null)
const infrastructure = ref<Record<string, any> | null>(null)
const mode = ref<HubMode>((localStorage.getItem('intelligenceHubMode') as HubMode) || 'inbox')
const articles = ref<IntelligenceArticle[]>([])
const currentArticle = ref<IntelligenceArticle | null>(null)
const topics = ref<TopicSummary[]>([])
const nextCursor = ref('')
const archives = ref<DigestArchive[]>([])
const digest = ref<DigestDetail | null>(null)
const proposals = ref<PreferenceProposal[]>([])
const subscriptions = ref<Array<Record<string, any>>>([])
const newSourceId = ref('')
const downloadFormats = ['md', 'html', 'json', 'pdf', 'docx']
const selectedDate = ref(localDateString())
const isMobile = ref(window.innerWidth < 768)
const filters = ref({ search: '', topic: '', state: '', minRelevance: 0 })

function localDateString(): string {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10)
}

const resizeHandler = () => { isMobile.value = window.innerWidth < 768 }
window.addEventListener('resize', resizeHandler)
onBeforeUnmount(() => window.removeEventListener('resize', resizeHandler))

const profileLabel = computed(() => {
  const profile = infrastructure.value?.profile
  if (profile === 'distributed') return '分布式 · PostgreSQL / Redis / MQTT'
  if (profile === 'standard') return '标准 · PostgreSQL / Redis'
  return '轻量 · SQLite / 本地存储'
})

const safeCurrentArticleUrl = computed(() => {
  const url = String(currentArticle.value?.url || '')
  return /^https?:\/\//i.test(url) ? url : ''
})

const readerDocument = computed(() => {
  const body = String(currentArticle.value?.content_html || currentArticle.value?.content || '')
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src https: data:; media-src https:; style-src 'unsafe-inline'; font-src data:; base-uri 'none'; form-action 'none'"><style>body{max-width:760px;margin:0 auto;padding:24px;font:16px/1.8 system-ui,-apple-system,'PingFang SC',sans-serif;color:#20251f}img,video{max-width:100%;height:auto}a{color:#315f3b}</style></head><body>${body}</body></html>`
})

async function openHub() {
  visible.value = true
  if (workspace.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    workspace.value = await bootstrapWorkspace()
    infrastructure.value = await getIntelligenceInfrastructure()
    await loadModeData()
  } catch (error: any) {
    errorMessage.value = error.message || String(error)
  } finally {
    loading.value = false
  }
}

async function handleModeChange(value: string | number | boolean) {
  mode.value = String(value) as HubMode
  localStorage.setItem('intelligenceHubMode', mode.value)
  await loadModeData()
}

async function loadModeData() {
  if (!workspace.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    if (mode.value === 'inbox') {
      await Promise.all([reloadArticles(), loadTopics()])
    } else if (mode.value === 'digest') {
      await Promise.all([loadArchives(), loadSelectedDigest(false)])
    } else if (mode.value === 'learning') {
      proposals.value = await listPreferenceProposals(workspace.value.id)
    } else {
      [infrastructure.value, subscriptions.value] = await Promise.all([
        getIntelligenceInfrastructure(),
        listIntelligenceSubscriptions(workspace.value.id)
      ])
    }
  } catch (error: any) {
    errorMessage.value = error.message || String(error)
  } finally {
    loading.value = false
  }
}

async function reloadArticles() {
  if (!workspace.value) return
  nextCursor.value = ''
  const page = await listIntelligenceArticles({
    workspace_id: workspace.value.id,
    limit: 30,
    search: filters.value.search || undefined,
    topic: filters.value.topic || undefined,
    state_filter: filters.value.state || undefined,
    min_relevance: filters.value.minRelevance > 0 ? filters.value.minRelevance : undefined
  })
  articles.value = page.items
  nextCursor.value = page.next_cursor
}

async function loadMore() {
  if (!workspace.value || !nextCursor.value) return
  loadingMore.value = true
  try {
    const page = await listIntelligenceArticles({
      workspace_id: workspace.value.id,
      limit: 30,
      cursor: nextCursor.value,
      search: filters.value.search || undefined,
      topic: filters.value.topic || undefined,
      state_filter: filters.value.state || undefined,
      min_relevance: filters.value.minRelevance > 0 ? filters.value.minRelevance : undefined
    })
    const known = new Set(articles.value.map((item) => item.id))
    articles.value.push(...page.items.filter((item) => !known.has(item.id)))
    nextCursor.value = page.next_cursor
  } catch (error: any) {
    Message.error(error.message || String(error))
  } finally {
    loadingMore.value = false
  }
}

async function loadTopics() {
  if (!workspace.value) return
  topics.value = await listIntelligenceTopics(workspace.value.id)
}

function selectTopic(slug: string) {
  filters.value.topic = slug
  reloadArticles()
}

async function openArticle(article: IntelligenceArticle) {
  if (!workspace.value) return
  readerVisible.value = true
  currentArticle.value = article
  try {
    currentArticle.value = await getIntelligenceArticle(workspace.value.id, article.id)
  } catch (error: any) {
    Message.error(error.message || String(error))
  }
}

async function sendFeedback(article: IntelligenceArticle, eventType: string) {
  if (!workspace.value) return
  try {
    await recordIntelligenceFeedback(workspace.value.id, article.id, eventType)
    article.feedback_sentiment = eventType === 'like' || eventType === 'dislike' ? eventType : article.feedback_sentiment
    Message.success('反馈已记录，将用于后续规则建议')
  } catch (error: any) {
    Message.error(error.message || String(error))
  }
}

async function toggleFavorite(article: IntelligenceArticle) {
  if (!workspace.value) return
  const eventType = article.is_favorite ? 'unfavorite' : 'favorite'
  try {
    await recordIntelligenceFeedback(workspace.value.id, article.id, eventType)
    article.is_favorite = !article.is_favorite
  } catch (error: any) {
    Message.error(error.message || String(error))
  }
}

async function hideArticle(article: IntelligenceArticle) {
  if (!workspace.value) return
  try {
    await recordIntelligenceFeedback(workspace.value.id, article.id, 'hide')
    if (filters.value.state !== 'hidden') articles.value = articles.value.filter((item) => item.id !== article.id)
    Message.success('文章已隐藏')
  } catch (error: any) {
    Message.error(error.message || String(error))
  }
}

async function analyzeArticle(article: IntelligenceArticle) {
  if (!workspace.value) return
  try {
    await analyzeIntelligenceArticle(workspace.value.id, article.id)
    const refreshed = await getIntelligenceArticle(workspace.value.id, article.id)
    Object.assign(article, refreshed)
    await loadTopics()
    Message.success('主题与摘要已更新')
  } catch (error: any) {
    Message.error(error.message || String(error))
  }
}

async function downloadArticle(article: IntelligenceArticle, format: string) {
  if (!workspace.value) return
  try {
    const result = await downloadIntelligenceArticle(workspace.value.id, article.id, format)
    const url = URL.createObjectURL(result.blob)
    const link = document.createElement('a')
    link.href = url
    link.download = result.filename
    link.click()
    URL.revokeObjectURL(url)
  } catch (error: any) {
    Message.error(error.message || String(error))
  }
}

async function loadArchives() {
  if (!workspace.value) return
  archives.value = await listDigests(workspace.value.id)
}

async function loadSelectedDigest(showError = true) {
  if (!workspace.value) return
  try {
    digest.value = await getDigest(workspace.value.id, selectedDate.value)
  } catch (error: any) {
    digest.value = null
    if (showError) Message.info('该日期尚未生成日报')
  }
}

async function createDigest() {
  if (!workspace.value) return
  loading.value = true
  try {
    digest.value = await generateDigest(workspace.value.id, selectedDate.value)
    await loadArchives()
    Message.success('日报已生成')
  } catch (error: any) {
    Message.error(error.message || String(error))
  } finally {
    loading.value = false
  }
}

async function copyText(value: string) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(value)
    return
  }
  const field = document.createElement('textarea')
  field.value = value
  field.setAttribute('readonly', '')
  field.style.position = 'fixed'
  field.style.opacity = '0'
  document.body.appendChild(field)
  field.select()
  const copied = document.execCommand('copy')
  field.remove()
  if (!copied) throw new Error('浏览器未允许复制，请在 HTTPS 环境打开或手动复制链接')
}

async function createShareLink() {
  if (!workspace.value || !digest.value) return
  try {
    const result = await shareDigest(workspace.value.id, selectedDate.value)
    const absoluteUrl = new URL(result.url, window.location.origin).toString()
    await copyText(absoluteUrl)
    Message.success('可过期的日报链接已复制')
  } catch (error: any) {
    Message.error(error.message || String(error))
  }
}

async function selectArchive(value: string) {
  selectedDate.value = value
  await loadSelectedDigest()
}

async function refreshPreferenceProposals() {
  if (!workspace.value) return
  loading.value = true
  try {
    await generatePreferenceProposals(workspace.value.id)
    proposals.value = await listPreferenceProposals(workspace.value.id)
    if (!proposals.value.length) Message.info('反馈样本尚未达到稳定规则门槛')
  } catch (error: any) {
    Message.error(error.message || String(error))
  } finally {
    loading.value = false
  }
}

async function reviewProposal(proposal: PreferenceProposal, approve: boolean) {
  if (!workspace.value) return
  try {
    await reviewPreferenceProposal(workspace.value.id, proposal.id, approve)
    proposals.value = proposals.value.filter((item) => item.id !== proposal.id)
    Message.success(approve ? '偏好规则已启用' : '建议已拒绝')
  } catch (error: any) {
    Message.error(error.message || String(error))
  }
}

async function subscribeSource() {
  if (!workspace.value || !newSourceId.value.trim()) return
  try {
    await createIntelligenceSubscription(workspace.value.id, newSourceId.value.trim())
    newSourceId.value = ''
    subscriptions.value = await listIntelligenceSubscriptions(workspace.value.id)
    Message.success('已建立订阅；初次发现任务限制为单页')
  } catch (error: any) {
    Message.error(error.message || String(error))
  }
}

function proposalTitle(proposal: PreferenceProposal): string {
  if (proposal.rule_type === 'source_preference') return '调整公众号来源权重'
  return '新的展示偏好建议'
}

function proposalDescription(proposal: PreferenceProposal): string {
  const sourceIds = (proposal.condition?.source_ids as string[] | undefined) || []
  const boost = Number(proposal.action?.rank_boost || 0)
  if (sourceIds.length) return `${sourceIds.join('、')}：${boost >= 0 ? '提高' : '降低'}排序权重`
  return '基于近期反馈形成的候选规则'
}

function formatPublishTime(timestamp?: number): string {
  if (!timestamp) return '时间未知'
  return new Date(timestamp * 1000).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.intelligence-fab {
  position: fixed;
  right: 28px;
  bottom: 32px;
  z-index: 900;
  width: 66px;
  height: 66px;
  border: 0;
  border-radius: 22px;
  color: #f7fff8;
  background: linear-gradient(145deg, #1d3322, #3d7048);
  box-shadow: 0 14px 34px rgba(30, 63, 38, .28);
  cursor: pointer;
  transition: transform .2s ease, box-shadow .2s ease;
}
.intelligence-fab:hover { transform: translateY(-3px); box-shadow: 0 18px 42px rgba(30, 63, 38, .34); }
.fab-mark { display: block; font: 800 20px/1 ui-monospace, monospace; letter-spacing: -.06em; }
.fab-label { display: block; margin-top: 5px; font-size: 11px; letter-spacing: .18em; }
.hub-title { display: flex; align-items: center; justify-content: space-between; gap: 16px; width: 100%; }
.hub-title strong, .hub-title small { display: block; }
.hub-title strong { font-size: 18px; }
.hub-title small { margin-top: 3px; color: var(--color-text-3); font-weight: 400; }
.hub-shell { min-height: 70vh; }
.hub-shell > .arco-alert { margin-bottom: 12px; }
.hub-mode { width: 100%; margin-bottom: 18px; }
.hub-mode :deep(.arco-radio-button) { flex: 1; text-align: center; }
.hub-loading { display: block; min-height: 360px; }
.hub-view { animation: hub-in .2s ease; }
@keyframes hub-in { from { opacity: 0; transform: translateX(8px); } }
.filter-panel { padding: 14px; border: 1px solid #dfe7df; border-radius: 16px; background: #f7faf7; }
.filter-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
.relevance-filter { display: flex; align-items: center; gap: 12px; margin-top: 10px; color: #687169; font-size: 13px; }
.relevance-filter b { min-width: 38px; color: #31563a; }
.view-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin: 24px 2px 12px; }
.view-heading h3 { margin: 4px 0 0; font-size: 21px; }
.eyebrow { color: #568061; font: 700 11px/1.2 ui-monospace, monospace; letter-spacing: .14em; }
.article-stack { display: grid; gap: 12px; }
.article-card { padding: 18px; border: 1px solid #e0e7e0; border-radius: 18px; background: #fff; box-shadow: 0 6px 22px rgba(30, 48, 34, .05); }
.article-meta { display: flex; align-items: center; gap: 10px; color: #7a837b; font-size: 12px; }
.article-meta .relevance { margin-left: auto; padding: 3px 8px; border-radius: 99px; color: #31563a; background: #edf5ee; font-weight: 700; }
.article-title { display: block; margin: 9px 0 6px; padding: 0; border: 0; background: transparent; color: #172018; font: 700 19px/1.4 inherit; text-align: left; cursor: pointer; }
.article-title:hover { color: #2f6a3d; }
.article-card > p { margin: 0; color: #5b655d; line-height: 1.65; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.topic-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.topic-row .arco-tag { cursor: pointer; }
.article-actions { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 15px; padding-top: 13px; border-top: 1px solid #eff2ef; }
.load-more { margin-top: 16px; }
.date-toolbar { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; padding: 14px; border-radius: 16px; background: #f4f8f4; }
.date-toolbar label span { display: block; margin-bottom: 5px; color: #687169; font-size: 12px; }
.date-toolbar input { height: 34px; padding: 0 10px; border: 1px solid #ccd7ce; border-radius: 8px; background: #fff; }
.digest-layout { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 18px; margin-top: 18px; }
.archive-rail { max-height: 65vh; overflow: auto; }
.archive-rail > button { display: flex; justify-content: space-between; width: 100%; margin-top: 8px; padding: 10px; border: 1px solid transparent; border-radius: 10px; background: transparent; color: #59635b; cursor: pointer; text-align: left; }
.archive-rail > button b, .archive-rail > button small { display: block; }
.archive-rail > button.active { border-color: #b9ccb9; background: #ebf3ec; color: #244c2d; }
.digest-paper { min-height: 420px; padding: 26px; border: 1px solid #e2e6df; border-radius: 18px; background: #fffefa; box-shadow: 0 10px 30px rgba(42, 52, 40, .06); }
.digest-paper h2 { margin: 7px 0 6px; font-size: 28px; }
.digest-summary { color: #687169; }
.digest-item { display: grid; grid-template-columns: 32px 1fr; gap: 12px; padding: 16px 0; border-top: 1px solid #e8ece6; cursor: pointer; }
.digest-item > span { color: #78917d; font: 700 15px/1.4 ui-monospace, monospace; }
.digest-item h4 { margin: 0 0 5px; font-size: 17px; }
.digest-item p { margin: 0 0 5px; color: #626b63; line-height: 1.5; }
.digest-item small { color: #899089; }
.learning-hero { margin-bottom: 18px; padding: 24px; border-radius: 20px; color: #edf8ef; background: linear-gradient(145deg, #1e3323, #3d6747); }
.learning-hero .eyebrow { color: #a9d3b1; }
.learning-hero h3 { margin: 8px 0; font-size: 24px; }
.learning-hero p { margin: 0 0 16px; color: #d4e4d6; line-height: 1.65; }
.proposal-card { display: flex; justify-content: space-between; gap: 18px; margin: 12px 0; padding: 18px; border: 1px solid #e1e7e1; border-radius: 16px; }
.proposal-card h4 { margin: 10px 0 5px; font-size: 18px; }
.proposal-card p { margin: 0 0 5px; color: #5f695f; }
.proposal-card small { color: #8a928a; }
.system-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.status-card { padding: 18px; border-radius: 16px; background: #f5f8f5; border: 1px solid #e0e7e0; }
.status-card span, .status-card strong, .status-card small { display: block; }
.status-card span { color: #7b847c; font-size: 12px; }
.status-card strong { margin: 8px 0 5px; font-size: 17px; }
.status-card small { color: #687169; line-height: 1.5; }
.subscription-box { margin-top: 20px; }
.subscribe-row { display: grid; grid-template-columns: 1fr auto; gap: 10px; }
.subscription-list > div { display: flex; justify-content: space-between; align-items: center; padding: 12px 2px; border-bottom: 1px solid #edf0ed; }
.subscription-list b, .subscription-list small { display: block; }
.subscription-list small { margin-top: 3px; color: #899089; }
.reader-shell { min-height: 420px; }
.reader-toolbar { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.reader-summary { padding: 14px 16px; border-left: 3px solid #4f7c59; border-radius: 0 10px 10px 0; background: #f0f6f1; }
.reader-summary p { margin: 5px 0 0; line-height: 1.65; }
.reader-frame { width: 100%; min-height: 58vh; margin-top: 14px; border: 1px solid #e6e9e5; border-radius: 12px; background: #fff; }
@media (max-width: 767px) {
  .intelligence-fab { right: 16px; bottom: 20px; width: 58px; height: 58px; border-radius: 18px; }
  .hub-mode { display: grid; grid-template-columns: 1fr 1fr; }
  .filter-row, .system-grid { grid-template-columns: 1fr; }
  .date-toolbar { align-items: stretch; flex-direction: column; }
  .digest-layout { grid-template-columns: 1fr; }
  .archive-rail { display: flex; gap: 6px; overflow-x: auto; }
  .archive-rail .eyebrow { display: none; }
  .archive-rail > button { min-width: 120px; }
  .digest-paper { padding: 18px; }
  .article-actions .arco-btn { flex: 1; }
  .proposal-card { flex-direction: column; }
}
</style>
