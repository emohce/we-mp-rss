<template>
  <section aria-label="队列与连接器状态">
    <template v-if="snapshot">
      <h3>本地队列事实</h3>
      <p class="field-help">此处读取数据库记录，不探测网络。计划{{ snapshot.configured.jobs ? '已配置启用' : '未配置启用' }}，采集器{{ snapshot.configured.collector ? '已配置启用' : '未配置启用' }}；不等于进程已启动。</p>
      <div class="queue-summary">
        <div><strong>采集</strong><p>{{ counts(snapshot.collection_counts) }}</p></div>
        <div><strong>我的工作流</strong><p>{{ counts(snapshot.workflow_counts) }}</p></div>
        <div><strong>事件箱</strong><p>{{ counts(snapshot.outbox_counts) }}</p></div>
      </div>
      <p class="field-help">{{ snapshot.delivery_mode === 'local-retained-no-transport' ? '当前无外部传输：新事件保留在本地。历史“已送达”标记不等于真实送达凭证。' : 'MQTT 已配置，连接与真实送达仍未验收。' }}</p>
      <details><summary>最近任务、账号退避与检查点</summary>
        <article v-for="job in snapshot.recent_jobs" :key="job.id" class="rule-card"><strong>{{ job.source_id }} · {{ job.mode }}</strong><p>{{ stateName(job.state) }} · 已尝试 {{ job.attempts }} 次 · 下一时点 {{ job.due_at }} UTC</p><p v-if="job.error_code">错误类别：{{ job.error_code }}</p></article>
        <p v-for="(account, index) in snapshot.accounts" :key="index">{{ account.provider }} · {{ stateName(account.state) }} · 连续失败 {{ account.failure_count }} · {{ account.cooldown_until ? '退避至 ' + account.cooldown_until + ' UTC' : '无已记录退避时点' }}</p>
        <p v-for="checkpoint in snapshot.checkpoints" :key="checkpoint.source_id + checkpoint.mode">{{ checkpoint.source_id }} · {{ checkpoint.mode }} v{{ checkpoint.version }} · 最近成功 {{ checkpoint.last_success_at || '尚无' }}</p>
      </details>
      <details><summary>最近七期日报覆盖</summary>
        <p v-if="!snapshot.recent_digests.length">暂无已生成日报。</p>
        <article v-for="digest in snapshot.recent_digests" :key="digest.date" class="rule-card">
          <strong>{{ digest.date }} · 修订 {{ digest.revision }}</strong>
          <p>{{ digest.status === 'partial' ? '部分完成' : '已生成' }} · 来源 {{ digest.coverage.completed ?? '未知' }}/{{ digest.coverage.expected ?? '未知' }} · 待分析 {{ digest.coverage.analysis_pending ?? '未知' }} · 分析失败 {{ digest.coverage.analysis_failed ?? '未知' }}</p>
        </article>
      </details>
      <h3>连接器能力与验收边界</h3>
      <article v-for="connector in snapshot.connectors" :key="connector.provider" class="rule-card">
        <strong>{{ connector.label }}</strong><p>{{ connector.capabilities.join(' / ') }}</p>
        <p class="field-help">供应商状态 {{ connector.supplier_state }} · 离线契约 {{ connector.offline_contract }} · 真实连接未验证</p><p>{{ connector.limits }}</p>
      </article>
      <details><summary>已记录用量（不是供应商余额）</summary><p v-if="!snapshot.usage.length">暂无用量记录</p><p v-for="(usage, index) in snapshot.usage" :key="index">{{ usage.provider }} · {{ usage.status }} · {{ usage.requests }} 次 / {{ usage.units }} 单位 · {{ usage.billable ? '标记为计费' : '非计费记录' }}</p><p class="field-help">预留或结果不明的用量不会自动返还；系统不会因限频自动切换付费通道。</p></details>
    </template>
    <details class="connector-import">
      <summary>离线 Feed / OPML 文件核验</summary>
      <p>只读取你选择的文件，不请求文件里的 URL。OPML 仅预览；Wechat2RSS 仅参照预览。</p>
      <label>文件来源<select v-model="provider" :disabled="busy"><option value="local-feed">通用本地 Feed</option><option value="supsub">SupSub 导出文件（非在线连接）</option><option value="wechat2rss">Wechat2RSS 参照文件（禁止导入）</option></select></label>
      <label>选择文件（1 MiB / 100 篇上限）<input type="file" :disabled="busy" accept=".xml,.rss,.atom,.json,.opml" @change="readFile" /></label>
      <p v-if="fileName" class="field-help">已选择：{{ fileName }}</p>
      <a-button size="small" :disabled="!content || busy" @click="previewFile">只读预览</a-button>
      <p v-if="message" role="status">{{ message }}</p>
      <template v-if="preview">
        <p>{{ preview.format }} · {{ preview.count }} 项。{{ preview.warning }}</p>
        <ol class="import-preview"><li v-for="(entry, index) in preview.entries" :key="index">{{ entry.title || entry.name || entry.external_id }}<small v-if="entry.groups?.length"> · {{ entry.groups.join(' / ') }}</small><span v-if="entry.requires_secret_ref"> · 地址已隐藏，需另行凭据管理</span></li></ol>
        <template v-if="preview.can_import && canImport">
          <label>稳定来源别名（相同文件来源下次复用）<input v-model="sourceKey" :disabled="busy" maxlength="120" placeholder="例如：reading-ai" /></label>
          <p class="reader-warning">旧 v1 仍使用全局文章库。只可导入你有权存储且可公开的内容，不要导入私密订阅或含凭据的正文。</p>
          <label class="checkbox-label"><input v-model="confirmed" type="checkbox" />确认以上公开内容，并关联到当前工作区</label>
          <a-button size="small" :disabled="!confirmed || !validSource || busy" @click="commitFile">确认导入这一批</a-button>
        </template>
        <p v-else-if="preview.can_import" class="field-help">只读预览完成；向全局文章存储导入需要管理员身份。</p>
      </template>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { importConnectorFile, previewConnectorFile, type ConnectorPreview, type OperationsSnapshot } from '@/api/intelligence'
import { RequestFence } from './workspaceState'
const props = defineProps<{ workspaceId: string; canImport: boolean; snapshot: OperationsSnapshot | null }>()
const emit = defineEmits<{ (event: 'imported'): void }>()
const provider = ref('local-feed'), sourceKey = ref(''), content = ref(''), fileName = ref(''), confirmed = ref(false), busy = ref(false), message = ref('')
const preview = ref<ConnectorPreview | null>(null)
const validSource = computed(() => /^[A-Za-z0-9_.:-]{1,120}$/.test(sourceKey.value))
const fence = new RequestFence()
let requestId = ''
function reset() { fence.invalidate(); busy.value = false; confirmed.value = false; preview.value = null; message.value = ''; requestId = '' }
watch(provider, reset)
watch(sourceKey, () => { confirmed.value = false; requestId = '' })
watch(() => props.workspaceId, () => { reset(); content.value = ''; fileName.value = ''; sourceKey.value = '' })
onBeforeUnmount(() => fence.invalidate())
async function readFile(event: Event) {
  reset(); content.value = ''; fileName.value = ''
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (file.size > 1024 * 1024) { message.value = '文件超过 1 MiB，请明确拆分后重试。'; return }
  const ticket = fence.begin('file'); busy.value = true
  try { const text = await file.text(); if (fence.current(ticket)) { content.value = text; fileName.value = file.name } }
  catch { if (fence.current(ticket)) message.value = '无法读取所选文件。' }
  finally { if (fence.current(ticket)) busy.value = false }
}
async function previewFile() {
  if (busy.value || !content.value) return
  const ticket = fence.begin('preview'); busy.value = true; confirmed.value = false; preview.value = null; message.value = ''
  try { const result = await previewConnectorFile(props.workspaceId, provider.value, content.value); if (fence.current(ticket)) preview.value = result }
  catch (cause) { if (fence.current(ticket)) message.value = cause instanceof Error ? cause.message : '预览失败。' }
  finally { if (fence.current(ticket)) busy.value = false }
}
async function commitFile() {
  if (busy.value || !confirmed.value || !props.canImport || !preview.value?.can_import || !validSource.value) return
  const ticket = fence.begin('import'); busy.value = true; confirmed.value = false
  try {
    requestId ||= globalThis.crypto.randomUUID()
    const result = await importConnectorFile(props.workspaceId, provider.value, sourceKey.value, content.value, requestId)
    if (fence.current(ticket)) { message.value = result.status === 'already_completed' ? '该请求已完成，未重复导入。' : '本批新增 ' + result.imported + ' 篇，未请求网络或消耗供应商额度。'; emit('imported') }
  } catch (cause) { if (fence.current(ticket)) message.value = cause instanceof Error ? cause.message : '导入失败，可用同一请求重试。' }
  finally { if (fence.current(ticket)) busy.value = false }
}
const stateName = (value: string) => ({ queued: '排队中', pending: '待处理', running: '运行中', publishing: '投递中', retry: '等待重试', completed: '完成', delivered: '记录为已送达', failed: '失败', healthy: '可调度', cooldown: '退避中', disabled: '已停用', probe: '待探测' }[value] || value)
const counts = (value: Record<string, number>) => Object.entries(value).map(([state, count]) => stateName(state) + ' ' + count).join(' · ') || '暂无记录'
</script>

<style>
.queue-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0}.queue-summary>div{padding:12px;background:var(--color-fill-2);border-radius:6px;font-size:13px}.connector-import{margin:24px 0;padding:14px;border:1px solid var(--color-border-2);border-radius:8px}.connector-import label{margin:12px 0}.import-preview{max-height:200px;overflow:auto;padding-left:22px;font-size:13px;line-height:1.8}
@media(max-width:480px){.queue-summary{grid-template-columns:1fr}}
</style>
