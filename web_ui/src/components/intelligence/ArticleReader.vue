<template>
  <section class="inline-reader" aria-label="文章阅读与反馈" :aria-busy="loading">
    <header class="reader-heading">
      <a-button data-reader-back size="small" @click="emit('back')">← 返回列表</a-button>
      <span class="field-help">Esc 返回 · 正文仅使用本地存档</span>
    </header>
    <p v-if="loading" role="status">正在读取正文…</p>
    <template v-else-if="article">
      <div class="reader-meta">{{ sourceName }} · {{ article.is_read ? '已读' : '未读' }}</div>
      <h2>{{ article.title || '未命名文章' }}</h2>
      <p>{{ article.ai_summary || article.description || '暂无摘要' }}</p>
      <p class="field-help">{{ article.rank_reason || article.ai_reason || '尚无推荐理由' }}</p>
      <div class="reader-actions">
        <a-button size="small" :disabled="busy" :type="article.feedback_sentiment === 'like' ? 'primary' : 'secondary'" @click="feedback('like')">有用</a-button>
        <a-button size="small" :disabled="busy" @click="feedback('dislike')">不感兴趣</a-button>
        <a-button size="small" :disabled="busy" @click="feedback(article.is_favorite ? 'unfavorite' : 'favorite')">{{ article.is_favorite ? '取消收藏' : '收藏' }}</a-button>
        <a-dropdown trigger="click">
          <a-button size="small" :disabled="busy">下载 ▾</a-button>
          <template #content><a-doption v-for="format in formats" :key="format" @click="emit('download', article, format)">{{ format.toUpperCase() }}</a-doption></template>
        </a-dropdown>
        <a v-if="safeUrl" :href="safeUrl" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">主动打开原文 ↗</a>
      </div>
      <p v-if="article.content_status === 'metadata_only' || article.content_status === 'unavailable'" class="reader-warning" role="status">
        {{ article.content_warning || '正文尚未保存，当前只能查看元数据。下载不会触发补抓。' }}
      </p>
      <details class="reader-feedback">
        <summary>纠正主题、展示偏好与更多反馈</summary>
        <div class="reader-actions">
          <a-button size="small" :disabled="busy" @click="feedback(article.is_read ? 'unread' : 'read')">标记{{ article.is_read ? '未读' : '已读' }}</a-button>
          <a-button size="small" :disabled="busy" @click="feedback('neutral')">清除相关度覆盖</a-button>
          <a-button size="small" :disabled="busy" @click="feedback(article.is_hidden ? 'unhide' : 'hide')">{{ article.is_hidden ? '恢复展示' : '隐藏此文' }}</a-button>
          <a-button size="small" :disabled="busy" @click="emit('analyze', article)">重新整理</a-button>
        </div>
        <label>纠正主题（逗号分隔，最多 8 个）<input v-model="topicText" maxlength="647" /></label>
        <div class="reader-actions">
          <a-button size="small" :disabled="busy || !validTopics" @click="feedback('topic_correction', { topics: topicNames })">保存主题纠正</a-button>
          <a-button size="small" :disabled="busy" @click="feedback('topic_correction', { reset: true })">恢复分析主题</a-button>
          <a-button size="small" :disabled="busy" @click="feedback('summary_preference', { style: 'brief' })">更简短摘要</a-button>
          <a-button size="small" :disabled="busy" @click="feedback('summary_preference', { style: 'detailed' })">完整摘要</a-button>
        </div>
        <label>具体反馈<textarea v-model="feedbackText" maxlength="2000" rows="3" placeholder="哪些信息有用？希望如何展示？" /></label>
        <a-button size="small" :disabled="busy || !feedbackText.trim()" @click="feedback('free_text', { text: feedbackText.trim() })">保存反馈记录</a-button>
        <p class="field-help">所有反馈保留；自由文本不会直接生成生效规则，学习建议仍需你确认。</p>
      </details>
      <p class="field-help">安全阅读模式不加载远程图片、音视频或脚本；原文链接需你主动打开。</p>
      <iframe class="reader-frame" :srcdoc="readerDocument(article.content_html || article.content || '')" sandbox="" referrerpolicy="no-referrer" title="本地文章正文（隔离阅读模式）" />
    </template>
    <p v-else>文章暂时无法读取，可返回列表重试。</p>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { IntelligenceArticle } from '@/api/intelligence'
import { readerDocument } from './workspaceState'
const props = defineProps<{ article: IntelligenceArticle | null; sourceName: string; loading: boolean; busy: boolean }>()
const emit = defineEmits<{
  (event: 'back'): void
  (event: 'feedback', article: IntelligenceArticle, eventType: string, value: Record<string, unknown>): void
  (event: 'download', article: IntelligenceArticle, format: string): void
  (event: 'analyze', article: IntelligenceArticle): void
}>()
const formats = ['md', 'html', 'json', 'pdf', 'docx']
const topicText = ref(''), feedbackText = ref('')
const topicNames = computed(() => topicText.value.split(/[,，]/).map(item => item.trim()).filter(Boolean))
const validTopics = computed(() => topicNames.value.length <= 8 && topicNames.value.every(name => name.length <= 80))
const safeUrl = computed(() => {
  try { const url = new URL(props.article?.url || ''); return ['http:', 'https:'].includes(url.protocol) ? url.href : '' } catch { return '' }
})
watch(() => props.article?.id, () => {
  topicText.value = (props.article?.topics || []).map((topic: IntelligenceArticle['topics'][number]) => topic.name).join('，')
  feedbackText.value = ''
}, { immediate: true })
const feedback = (eventType: string, value: Record<string, unknown> = {}) => {
  if (props.article) emit('feedback', props.article, eventType, value)
}
</script>
