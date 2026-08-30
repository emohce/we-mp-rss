<template>
  <a-tooltip content="在浮窗中阅读、筛选与查看日报">
    <button ref="launcher" class="intelligence-fab" type="button" aria-label="打开公众号智能聚合工作区" :aria-expanded="state.visible" @click="open">智能聚合</button>
  </a-tooltip>
  <Teleport to="body"><div id="intelligence-overlay-root" class="intelligence-overlay-root" /></Teleport>
  <a-drawer :visible="state.visible" popup-container="#intelligence-overlay-root" placement="right" :width="viewport < 720 ? '100%' : state.width"
    :mask="false" :mask-closable="false" :esc-to-close="false" :closable="false" :footer="false"
    :unmount-on-close="true" body-class="intelligence-drawer-body" @cancel="closeHub" @open="focusPanel">
    <template #title>
      <div class="hub-heading">
        <div><strong>公众号智能聚合</strong><small>{{ workspace?.name || '正在核验当前工作区' }}</small></div>
        <a-button size="small" aria-label="关闭智能聚合工作区" @click="closeHub">关闭</a-button>
      </div>
    </template>
    <div ref="panel" class="intelligence-workspace" role="region" aria-label="公众号智能聚合工作区" tabindex="-1" @keydown="onKey">
      <div v-if="viewport >= 720" class="hub-resizer" role="separator" tabindex="0" aria-label="调整浮窗宽度"
        aria-orientation="vertical" :aria-valuenow="state.width" :aria-valuemin="560" :aria-valuemax="Math.min(1440, viewport - 16)"
        @pointerdown="startResize" @pointermove="moveResize" @pointerup="endResize" @pointercancel="endResize"
        @keydown.left.prevent.stop="resizeBy(40)" @keydown.right.prevent.stop="resizeBy(-40)" />
      <a-alert v-if="error" type="warning" closable @close="error = ''">{{ error }}</a-alert>
      <p v-if="notice" class="hub-notice" role="status">{{ notice }}</p>
      <nav class="hub-mode" aria-label="聚合工作区视图">
        <button v-for="item in modes" :key="item.value" type="button" :aria-current="state.mode === item.value ? 'page' : undefined"
          :disabled="!ready" @click="setMode(item.value)">{{ item.label }}</button>
      </nav>
      <p v-if="!ready" role="status">{{ loading.bootstrap ? '正在准备工作区…' : '工作区未就绪，可关闭后重试。' }}</p>
      <template v-else>
        <div v-if="state.mode === 'inbox' || state.mode === 'digest'" class="workspace-body" :class="{ 'has-reader': state.articleId, compact: state.width < 900 || viewport < 900 }">
          <main class="master-pane">
            <WorkspaceFilters v-model="state.filters" :sources="sources" :topics="topics" :saved-filters="savedFilters"
              :digest="state.mode === 'digest'" :busy="Boolean(loading['filter-write'])" @apply="applyFilters"
              @save="saveFilter" @select="applyFilter" @remove="removeFilter" />
            <section v-if="state.mode === 'inbox'" aria-label="筛选结果" :aria-busy="Boolean(loading.articles)">
              <div class="section-heading"><h2>收件箱 <small>{{ total }} 篇</small></h2><a-button size="small" :loading="loading.articles" @click="loadArticles()">刷新</a-button></div>
              <p class="field-help">手动相关度优先于学习规则；↑ ↓ 移动标题焦点，Enter 阅读。不会因打开文章自动标记已读。</p>
              <p v-if="loading.articles && !articles.length" role="status">正在筛选本地文章…</p>
              <a-empty v-else-if="!articles.length" description="当前条件下暂无文章，可重置筛选或在运行状态中订阅来源。" />
              <article v-for="article in articles" :key="article.id" class="article-card" :class="{ selected: article.id === state.articleId }">
                <div class="article-meta"><span>{{ sourceName(article.mp_id) }}</span><time>{{ publishTime(article.publish_time) }}</time><span>{{ score(article) }}%</span></div>
                <button class="article-title" type="button" :data-article-id="article.id" @click="read(article)">{{ article.title || '未命名文章' }}</button>
                <details v-if="article.display_collapsed" class="collapsed-summary"><summary>根据已批准偏好折叠摘要（仍可阅读）</summary><p>{{ article.ai_summary || article.description || '暂无摘要' }}</p></details>
                <p v-else>{{ article.ai_summary || article.description || '尚未整理，可在阅读面板发起整理。' }}</p>
                <div class="article-topics"><button v-for="topic in article.topics" :key="topic.slug" class="topic-button" type="button" @click="selectTopic(topic.slug)">{{ topic.name }}</button></div>
                <div class="article-actions">
                  <a-button size="mini" :disabled="loading['feedback-write']" :type="article.feedback_sentiment === 'like' ? 'primary' : 'secondary'" @click="sendFeedback(article, 'like')">有用</a-button>
                  <a-button size="mini" :disabled="loading['feedback-write']" @click="sendFeedback(article, article.is_favorite ? 'unfavorite' : 'favorite')">{{ article.is_favorite ? '已收藏' : '收藏' }}</a-button>
                  <a-dropdown trigger="click"><a-button size="mini" :disabled="loading['feedback-write']">更多 ▾</a-button>
                    <template #content>
                      <a-doption @click="download(article, 'md')">下载 Markdown</a-doption>
                      <a-doption @click="sendFeedback(article, 'dislike')">不感兴趣</a-doption>
                      <a-doption @click="sendFeedback(article, article.is_read ? 'unread' : 'read')">标记{{ article.is_read ? '未读' : '已读' }}</a-doption>
                      <a-doption @click="hideAndRestoreFocus(article)">{{ article.is_hidden ? '恢复展示' : '隐藏此文' }}</a-doption>
                    </template>
                  </a-dropdown>
                  <span v-if="article.is_read" class="field-help">已读</span>
                </div>
              </article>
              <a-button v-if="nextCursor" long :loading="loading.articles" @click="loadArticles(true)">继续加载</a-button>
            </section>
            <section v-else aria-label="按日期划分的日报" :aria-busy="Boolean(loading.digest)">
              <div class="date-toolbar">
                <label>日报日期（上海时间）<input type="date" :value="state.selectedDate" @change="selectDate(($event.target as HTMLInputElement).value)" /></label>
                <a-button size="small" :loading="loading['digest-write']" @click="createDigest">生成 / 检查修订</a-button>
                <a-button size="small" :disabled="!digest || loading['share-write']" @click="shareConfirm = !shareConfirm">分享设置</a-button>
              </div>
              <div v-if="shareConfirm" class="share-panel">
                <p>持有链接的人可查看当前日报及其后续修订（不含正文、反馈或账号信息）。链接 7 天后过期，可随时撤销。</p>
                <a-button v-if="!share" size="small" :loading="loading['share-write']" @click="createShareLink">确认生成只读链接</a-button>
                <template v-else><label>分享链接<input :value="share.url" readonly @focus="($event.target as HTMLInputElement).select()" /></label>
                  <div class="article-actions"><a-button size="small" @click="copyShare">复制链接</a-button><a-button size="small" :loading="loading['share-write']" @click="revokeShare">撤销此链接</a-button></div>
                </template>
              </div>
              <nav v-if="archives.length" class="archive-rail" aria-label="日报日期归档">
                <button v-for="archive in archives" :key="archive.id" type="button" :aria-current="archive.date === state.selectedDate ? 'date' : undefined" @click="selectDate(archive.date)">{{ archive.date }} · {{ archive.item_count }} 篇 · r{{ archive.revision }}</button>
              </nav>
              <p v-if="loading.digest" role="status">正在读取日报修订…</p>
              <template v-else-if="digest">
                <div class="section-heading"><h2>{{ digest.title }}</h2><span>修订 {{ digest.revision }}</span></div>
                <p>{{ digest.summary }}</p>
                <div v-if="digest.coverage" class="coverage-panel" :class="{ incomplete: !digest.coverage.complete }">
                  <strong>{{ digest.coverage.complete ? '来源覆盖完成' : '尚非完整日报' }}</strong>
                  <p>来源 {{ digest.coverage.expected }} · 完成 {{ digest.coverage.completed }} · 等待 {{ digest.coverage.pending }} · 部分 {{ digest.coverage.partial }} · 失败 {{ digest.coverage.failed }} · 跳过 {{ digest.coverage.skipped }}</p>
                  <p>分析待处理 {{ digest.coverage.analysis_pending }} · 分析失败 {{ digest.coverage.analysis_failed }}</p>
                  <details><summary>查看来源明细与原因</summary><p v-for="source in digest.coverage.sources" :key="source.provider + source.source_id">{{ sourceName(source.source_id) }} · {{ source.state }} {{ source.reason ? '· ' + source.reason : '' }}</p></details>
                </div>
                <p class="field-help">当前显示 {{ digestItems.length }} / {{ digest.items.length }} 篇。迟到内容会产生新修订，不改写旧修订记录。</p>
                <article v-for="item in digestItems" :key="item.article.id" class="article-card">
                  <div class="article-meta"><span>#{{ item.rank }} · {{ sourceName(item.article.mp_id) }}</span><span v-if="item.is_late">迟到补录</span><span>{{ Math.round(item.relevance_score * 100) }}%</span></div>
                  <button class="article-title" type="button" :data-article-id="item.article.id" @click="read(item.article)">{{ item.article.title }}</button>
                  <p>{{ item.article.ai_summary || item.article.description }}</p><small>{{ item.reason }}</small>
                </article>
              </template>
              <a-empty v-else description="该日期尚无日报。选择其他日期，或在发布时点后生成。" />
            </section>
          </main>
          <ArticleReader v-if="state.articleId" :article="reader" :source-name="sourceName(reader?.mp_id)" :loading="Boolean(loading.reader)"
            :busy="Boolean(loading['feedback-write'] || loading['analysis-write'] || loading.download)"
            @back="backToList" @feedback="sendFeedback" @download="download" @analyze="analyze" />
        </div>
        <main v-else-if="state.mode === 'learning'" class="hub-scroll" aria-label="偏好学习">
          <div class="section-heading"><h2>你的反馈，你来决定</h2><a-button size="small" :disabled="!learning?.eligible" :loading="loading['rule-write']" @click="propose">检查学习建议</a-button></div>
          <p v-if="learning">累计 {{ learning.events }} 条记录，{{ learning.distinct_articles }} 篇文章，跨度 {{ learning.span_days }} 天。</p>
          <p class="field-help">扫描全部历史；至少 20 篇且跨 7 天才提出建议。主题 / 来源需重复证据，规则批准后生效，可撤销。自由文本只保留为证据。</p>
          <h3>待批准建议 · {{ proposals.length }}</h3>
          <article v-for="proposal in proposals" :key="proposal.id" class="rule-card">
            <strong>{{ ruleLabel(proposal.rule_type) }} · 置信度 {{ Math.round(proposal.confidence * 100) }}%</strong>
            <p>{{ describeRule(proposal) }}</p><small>证据记录 {{ proposal.evidence.length }} 条</small>
            <div class="article-actions"><a-button size="small" type="primary" :disabled="loading['rule-write']" @click="review(proposal.id, true)">批准</a-button><a-button size="small" :disabled="loading['rule-write']" @click="review(proposal.id, false)">拒绝</a-button></div>
          </article>
          <a-empty v-if="!proposals.length" description="暂无待批准建议，继续对文章反馈即可。" />
          <h3>规则与历史版本</h3>
          <article v-for="rule in rules" :key="rule.id" class="rule-card"><strong>{{ ruleLabel(rule.rule_type) }} · v{{ rule.version }} · {{ rule.is_active ? '生效中' : '已停用' }}</strong><p>{{ describeRule(rule) }}</p><a-button v-if="rule.is_active" size="small" :disabled="loading['rule-write']" @click="revokeRule(rule.id)">撤销此规则</a-button></article>
          <details><summary>最近反馈记录（{{ feedback.items.length }} / {{ feedback.total }}）</summary><ol class="feedback-history"><li v-for="event in feedback.items" :key="event.id"><time>{{ event.created_at }}</time> · {{ feedbackLabel(event.event_type) }}<p>{{ feedbackValue(event.value) }}</p></li></ol><p class="field-help">此处显示最近 30 条，学习使用全部记录。</p></details>
        </main>
        <main v-else class="hub-scroll" aria-label="运行状态与订阅管理">
          <div class="section-heading"><h2>运行状态</h2><a-button size="small" @click="loadMode">刷新</a-button></div>
          <p class="field-help">配置存在不代表连接已验证。不会在此页面自动探测微信、付费服务或基础设施。</p>
          <dl v-if="infrastructure" class="infrastructure-grid">
            <dt>存储模式</dt><dd>{{ infrastructure.profile }} · {{ infrastructure.database }}</dd>
            <dt>Redis</dt><dd>{{ infrastructure.redis_enabled ? '已配置，连接未验证' : '未配置' }}</dd>
            <dt>MQTT</dt><dd>{{ infrastructure.mqtt_enabled ? '已配置，投递未验证' : '未配置' }}</dd>
            <dt>正文存储</dt><dd>{{ infrastructure.content_backend }} · 实际读写另行验收</dd>
            <dt>每日时点</dt><dd>{{ infrastructure.schedule?.collect_at }} 采集 / {{ infrastructure.schedule?.cutoff_at }} 截止 / {{ infrastructure.schedule?.digest_at }} 汇总（{{ infrastructure.schedule?.timezone }}）</dd>
          </dl>
          <p v-for="issue in infrastructure?.issues || []" :key="issue" class="reader-warning">{{ issue }}</p>
          <h3>公众号订阅</h3>
          <form class="subscription-form" @submit.prevent="subscribe(selectedSource)">
            <label>选择本地已解析来源<select v-model="selectedSource"><option value="">请选择公众号</option><option v-for="source in sources" :key="source.id" :value="source.id">{{ source.name }}</option></select></label>
            <a-button html-type="submit" size="small" :disabled="!selectedSource" :loading="loading['subscription-write']">订阅并排队</a-button>
          </form>
          <p class="field-help">仅显示本地已解析的前 100 个来源；没有找到时先在原公众号管理中解析。这里不接受猜测的来源 ID。</p>
          <article v-for="subscription in subscriptions" :key="subscription.id" class="rule-card">
            <strong>{{ sourceName(subscription.source_id) }}</strong><p>{{ subscription.provider }} · {{ subscription.status === 'active' ? '订阅中' : '已暂停' }}</p>
            <div class="article-actions"><a-button size="small" :disabled="loading['subscription-write']" @click="toggleSubscription(subscription)">{{ subscription.status === 'active' ? '暂停后续采集' : '恢复订阅' }}</a-button><a-button size="small" :disabled="subscription.status !== 'active' || loading['subscription-write']" @click="backfill(subscription.id)">请求最多 3 页历史</a-button></div>
          </article>
          <p class="field-help">暂停仅影响后续每日计划，不取消当日冻结来源或在途请求。限频与会话失效会延后任务，不代表系统已绕过平台限制。</p>
          <section v-if="workspace?.can_import_legacy" class="legacy-import">
            <h3>历史文章关联（管理员）</h3><p>每次最多把 200 篇现有文章关联到当前工作区，不请求微信，不会自动继续下一批。</p>
            <label class="checkbox-label"><input v-model="importConfirmed" type="checkbox" />我确认将本地历史文章关联到这个工作区</label>
            <a-button size="small" :disabled="!importConfirmed || loading['legacy-write']" @click="confirmImport">执行一批</a-button>
          </section>
        </main>
      </template>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { IntelligenceArticle, PreferenceProposal, PreferenceRule } from '@/api/intelligence'
import WorkspaceFilters from './WorkspaceFilters.vue'
import ArticleReader from './ArticleReader.vue'
import { clampWidth, focusAfterRemoval, type HubMode } from './workspaceState'
import { useIntelligenceWorkspace } from './useIntelligenceWorkspace'
let storage: Storage | undefined
try { storage = window.localStorage } catch { /* Private mode can disable storage. */ }
const hub = useIntelligenceWorkspace(undefined, storage)
const { state, workspace, ready, loading, error, notice, articles, total, nextCursor, reader, topics, sources, savedFilters, digest, archives, proposals, rules, learning, feedback, infrastructure, subscriptions, share, digestItems, sourceName,
  open, setMode, loadMode, loadArticles, openArticle, sendFeedback, analyze, download, saveFilter, removeFilter, applyFilter, createDigest, createShareLink, revokeShare, propose, review, revokeRule, subscribe, toggleSubscription, backfill } = hub
const launcher = ref<HTMLButtonElement | null>(null), panel = ref<HTMLElement | null>(null)
const viewport = ref(window.innerWidth), selectedSource = ref(''), importConfirmed = ref(false), shareConfirm = ref(false)
const modes: Array<{ value: HubMode; label: string }> = [{ value: 'inbox', label: '收件箱' }, { value: 'digest', label: '日期汇总' }, { value: 'learning', label: '偏好学习' }, { value: 'system', label: '运行状态' }]
const score = (article: IntelligenceArticle) => Math.round((article.effective_relevance ?? article.ai_relevance ?? 0.5) * 100)
const publishTime = (timestamp?: number) => timestamp ? new Date(timestamp * 1000).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }) : '日期未知'
const focusPanel = () => { panel.value?.focus() }
async function closeHub() { hub.close(); await nextTick(); launcher.value?.focus() }
async function read(article: IntelligenceArticle) { const pending = openArticle(article); await nextTick(); panel.value?.querySelector<HTMLButtonElement>('[data-reader-back]')?.focus(); await pending }
async function backToList() { const id = state.focusedId; hub.closeReader(); await nextTick(); focusArticle(id) }
function focusArticle(id: string | null) {
  const targets = Array.from(panel.value?.querySelectorAll<HTMLButtonElement>('[data-article-id]') || [])
  ;(targets.find(target => target.dataset.articleId === id) || targets[0] || panel.value)?.focus()
}
async function hideAndRestoreFocus(article: IntelligenceArticle) {
  const next = focusAfterRemoval(articles.value.map(item => item.id), article.id)
  await sendFeedback(article, article.is_hidden ? 'unhide' : 'hide')
  await nextTick(); focusArticle(next)
}
function applyFilters() { if (state.mode === 'inbox') void loadArticles() }
function selectTopic(topic: string) { state.filters.topic = topic; applyFilters() }
async function selectDate(value: string) { if (!value) return; shareConfirm.value = false; hub.closeReader(); await hub.selectDate(value) }
async function confirmImport() { if (!importConfirmed.value) return; importConfirmed.value = false; await hub.importBatch() }
async function copyShare() {
  if (!share.value) return
  try { await navigator.clipboard.writeText(share.value.url); notice.value = '链接已复制。' }
  catch { notice.value = '浏览器无法自动复制；请选中上面的链接手动复制。' }
}
const ruleLabel = (type: string) => ({ source_preference: '来源偏好', topic_preference: '主题偏好', reading_preference: '摘要偏好' }[type] || type)
function describeRule(rule: PreferenceRule | PreferenceProposal) {
  const condition = rule.condition, action = rule.action
  if (rule.rule_type === 'reading_preference') return action.summary_style === 'brief' ? '优先显示简短摘要' : '优先显示完整摘要'
  const values = (condition.source_ids || condition.topic_slugs || []) as string[]
  const names = values.map(value => condition.source_ids ? sourceName(value) : topics.value.find(topic => topic.slug === value)?.name || value)
  return names.join('、') + ' · 排名调整 ' + Math.round(Number(action.rank_boost || 0) * 100) + '%' + (action.collapse ? ' · 折叠摘要' : '')
}
const feedbackLabel = (event: string) => ({ like: '有用', dislike: '不感兴趣', favorite: '收藏', unfavorite: '取消收藏', read: '已读', unread: '未读', hide: '隐藏', unhide: '恢复', neutral: '清除相关度覆盖', topic_correction: '主题纠正', summary_preference: '摘要偏好', free_text: '文字反馈' }[event] || event)
const feedbackValue = (value: Record<string, unknown>) => String(value.text || value.style || (Array.isArray(value.topics) ? value.topics.join('、') : '') || '')
function onKey(event: KeyboardEvent) {
  if (!state.visible || event.isComposing || event.defaultPrevented) return
  const target = event.target as HTMLElement
  if (event.key === 'Escape') {
    if (target.closest('input,textarea,select,[contenteditable="true"],[aria-expanded="true"],[role="listbox"],[role="menu"]')) return
    event.preventDefault(); state.articleId ? void backToList() : void closeHub(); return
  }
  if (target.closest('input,textarea,select,[contenteditable="true"],[role="combobox"],[role="menu"]')) return
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'f') {
    const search = panel.value?.querySelector<HTMLInputElement>('[data-hub-search]')
    if (search) { event.preventDefault(); search.focus() }
    return
  }
  if (!['ArrowUp', 'ArrowDown'].includes(event.key) || !target.matches('[data-article-id]') || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return
  const targets = Array.from(panel.value?.querySelectorAll<HTMLButtonElement>('[data-article-id]') || [])
  const index = targets.indexOf(target as HTMLButtonElement), next = index + (event.key === 'ArrowDown' ? 1 : -1)
  if (targets[next]) { event.preventDefault(); targets[next].focus(); state.focusedId = targets[next].dataset.articleId || null }
}
let resize: { x: number; width: number } | null = null
function startResize(event: PointerEvent) { if (event.button !== 0) return; resize = { x: event.clientX, width: state.width }; (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId); event.preventDefault() }
function moveResize(event: PointerEvent) { if (resize) state.width = clampWidth(resize.width + resize.x - event.clientX, viewport.value) }
function endResize() { resize = null }
function resizeBy(delta: number) { state.width = clampWidth(state.width + delta, viewport.value) }
function updateViewport() { viewport.value = window.innerWidth; state.width = clampWidth(state.width, viewport.value) }
watch(() => workspace.value?.id, () => { selectedSource.value = ''; importConfirmed.value = false; shareConfirm.value = false })
watch(ready, value => { if (value) updateViewport() })
onMounted(() => window.addEventListener('resize', updateViewport))
onBeforeUnmount(() => window.removeEventListener('resize', updateViewport))
</script>

<style>
.intelligence-fab{position:fixed;right:24px;bottom:24px;z-index:1000;border:1px solid var(--color-border-3);border-radius:24px;padding:12px 20px;color:var(--color-white,#fff);background:rgb(var(--primary-6));box-shadow:0 4px 16px #0002;font:600 14px/1.4 inherit;cursor:pointer}
.intelligence-drawer-body{padding:0!important;overflow:hidden!important}
.intelligence-overlay-root{position:fixed;inset:0;z-index:1001;pointer-events:none}.intelligence-overlay-root .arco-drawer-container{pointer-events:none}.intelligence-overlay-root .arco-drawer{pointer-events:auto;border-left:1px solid var(--color-border-2);box-shadow:-8px 0 28px #0002}
.hub-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;width:100%}.hub-heading small{display:block;font-size:12px;font-weight:400;color:var(--color-text-3);margin-top:4px}
.intelligence-workspace{height:100%;display:flex;flex-direction:column;gap:12px;padding:16px;box-sizing:border-box;position:relative;overflow:hidden;color:var(--color-text-1);background:var(--color-bg-1)}
.intelligence-workspace :focus-visible,.intelligence-fab:focus-visible{outline:3px solid rgb(var(--primary-6));outline-offset:3px}
.hub-resizer{position:absolute;left:0;top:0;width:8px;height:100%;cursor:ew-resize;touch-action:none;z-index:2}
.hub-resizer:hover,.hub-resizer:focus-visible{background:rgba(var(--primary-6),.15)}
.hub-notice{margin:0;padding:10px 12px;border-radius:6px;background:var(--color-fill-2);font-size:13px}
.hub-mode{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;background:var(--color-fill-2);border-radius:8px;padding:4px;flex-shrink:0}
.hub-mode button{padding:10px 4px;border:0;border-radius:6px;background:transparent;color:var(--color-text-2);cursor:pointer;font:inherit;white-space:nowrap}
.hub-mode button[aria-current]{background:var(--color-bg-1);color:rgb(var(--primary-6));font-weight:600;box-shadow:0 1px 3px #0001}
.workspace-body{display:grid;grid-template-columns:minmax(0,1fr);gap:16px;flex:1;min-height:0}
.workspace-body.has-reader{grid-template-columns:minmax(260px,.9fr) minmax(300px,1.1fr)}
.workspace-body.has-reader.compact{grid-template-columns:minmax(0,1fr)}.workspace-body.has-reader.compact .master-pane{display:none}.workspace-body.compact .inline-reader{border-left:0;padding-left:0}
.master-pane,.hub-scroll,.inline-reader{min-width:0;overflow:auto;overscroll-behavior:contain;scrollbar-gutter:stable;padding:2px 8px 12px 2px}
.hub-scroll{flex:1;min-height:0}.inline-reader{border-left:1px solid var(--color-border-2);padding-left:16px}
.intelligence-workspace h2{font-size:19px;line-height:1.5;margin:12px 0}.intelligence-workspace h3{font-size:16px;margin:24px 0 12px}.intelligence-workspace p{line-height:1.7;overflow-wrap:anywhere}
.workspace-filters{padding:14px;background:var(--color-fill-1);border:1px solid var(--color-border-2);border-radius:8px;margin-bottom:18px}
.intelligence-workspace label{display:flex;flex-direction:column;gap:6px;font-size:12px;color:var(--color-text-2);min-width:0}
.intelligence-workspace input:not([type=range]):not([type=checkbox]),.intelligence-workspace select,.intelligence-workspace textarea{box-sizing:border-box;width:100%;min-width:0;border:1px solid var(--color-border-3);border-radius:5px;padding:8px;background:var(--color-bg-2);color:var(--color-text-1);font:inherit;font-size:13px}
.intelligence-workspace input[type=range]{width:100%;accent-color:rgb(var(--primary-6))}
.filter-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:12px 0}.score-field{grid-column:1/-1}
.filter-actions,.reader-actions,.article-actions,.date-toolbar,.subscription-form{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:12px}
.field-help{font-size:12px;color:var(--color-text-2);line-height:1.7}.filter-actions .field-help{flex-basis:100%}
.saved-filter-panel{border-top:1px solid var(--color-border-2);padding-top:12px;margin-top:12px}.saved-filter-row{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:8px}
.intelligence-workspace summary{cursor:pointer;font-size:13px;line-height:1.8}.text-action,.topic-button{border:0;cursor:pointer;background:transparent;color:rgb(var(--primary-6));font:inherit}
.section-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.section-heading small{font-weight:400;font-size:12px;color:var(--color-text-2)}
.article-card,.rule-card{border:1px solid var(--color-border-2);border-radius:8px;padding:14px;margin-bottom:12px;background:var(--color-bg-2)}.article-card.selected{border-color:rgb(var(--primary-6))}
.article-meta,.reader-meta{display:flex;align-items:center;flex-wrap:wrap;gap:8px;font-size:12px;color:var(--color-text-2)}
.article-title{display:block;border:0;background:transparent;text-align:left;cursor:pointer;color:var(--color-text-1);font-size:16px;font-weight:600;line-height:1.6;padding:0;margin:10px 0;overflow-wrap:anywhere}
.article-card>p{font-size:13px;margin:8px 0;color:var(--color-text-2)}.article-topics{display:flex;flex-wrap:wrap;gap:6px}
.topic-button{background:var(--color-fill-2);padding:4px 7px;border-radius:5px;font-size:12px}.collapsed-summary{margin:8px 0;color:var(--color-text-2)}
.reader-heading{display:flex;align-items:center;gap:10px;flex-wrap:wrap;position:sticky;top:-2px;background:var(--color-bg-1);padding:8px 0;z-index:1}.reader-meta{margin-top:14px}
.reader-actions a{font-size:13px;color:rgb(var(--primary-6))}.reader-feedback{border:1px solid var(--color-border-2);border-radius:6px;padding:12px;margin-top:16px}.reader-feedback label{margin:12px 0}
.reader-warning{padding:10px;background:rgba(var(--warning-6),.12);border-left:3px solid rgb(var(--warning-6));font-size:13px}
.reader-frame{border:1px solid var(--color-border-2);border-radius:6px;width:100%;height:65vh;min-height:320px;box-sizing:border-box;background:#fff}
.archive-rail{display:flex;gap:8px;overflow:auto;padding:12px 2px}.archive-rail button{flex-shrink:0;border:1px solid var(--color-border-2);border-radius:6px;background:var(--color-bg-2);padding:8px;color:var(--color-text-2);font:inherit;font-size:12px;cursor:pointer}.archive-rail button[aria-current]{border-color:rgb(var(--primary-6));color:rgb(var(--primary-6))}
.coverage-panel,.share-panel,.legacy-import{background:var(--color-fill-1);border:1px solid var(--color-border-2);border-radius:8px;padding:14px;margin:14px 0}.coverage-panel p{font-size:12px;margin:6px 0}.coverage-panel.incomplete{border-left:3px solid rgb(var(--warning-6))}
.infrastructure-grid{display:grid;grid-template-columns:90px minmax(0,1fr);gap:12px;font-size:13px;line-height:1.7}.infrastructure-grid dt{color:var(--color-text-2)}.infrastructure-grid dd{margin:0;overflow-wrap:anywhere}
.subscription-form label{flex:1;min-width:160px}.intelligence-workspace .checkbox-label{flex-direction:row;align-items:flex-start;margin-bottom:12px;line-height:1.6}.checkbox-label input{margin-top:3px}
.feedback-history{padding-left:20px;font-size:12px}.feedback-history p{white-space:pre-wrap}
@media(max-width:900px){.workspace-body.has-reader{grid-template-columns:minmax(0,1fr)}.workspace-body.has-reader .master-pane{display:none}.inline-reader{border-left:0;padding-left:0}}
@media(max-width:480px){.intelligence-workspace{padding:12px}.hub-mode button{font-size:12px}.intelligence-fab{right:16px;bottom:16px}.filter-grid{gap:8px}.date-toolbar>*{flex:1 1 45%}}
@media(prefers-reduced-motion:reduce){.intelligence-workspace *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
</style>
