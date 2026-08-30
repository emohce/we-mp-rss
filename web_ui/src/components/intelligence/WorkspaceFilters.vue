<template>
  <form class="workspace-filters" aria-label="文章总体筛选" @submit.prevent="emit('apply')">
    <label class="search-field">{{ digest ? '在此日报标题和摘要中查找' : '搜索本地标题、摘要与正文' }}
      <input data-hub-search :value="modelValue.search" type="search" maxlength="120" placeholder="输入关键词，按 Enter 应用" @input="set('search', value($event))" />
    </label>
    <div class="filter-grid">
      <label>来源
        <select :value="modelValue.source_id" @change="set('source_id', value($event)); emit('apply')">
          <option value="">全部公众号</option>
          <option v-for="source in sources" :key="source.id" :value="source.id">{{ source.name }}</option>
        </select>
      </label>
      <label>主题
        <select :value="modelValue.topic" @change="set('topic', value($event)); emit('apply')">
          <option value="">全部主题</option>
          <option v-for="topic in topics" :key="topic.slug" :value="topic.slug">{{ topic.name }} · {{ topic.article_count }}</option>
        </select>
      </label>
      <label v-if="!digest">阅读状态
        <select :value="modelValue.state_filter" @change="set('state_filter', value($event)); emit('apply')">
          <option value="">未隐藏文章</option><option value="unread">未读</option><option value="favorite">收藏</option><option value="hidden">已隐藏</option>
        </select>
      </label>
      <label v-if="!digest">排序
        <select :value="modelValue.order" @change="set('order', value($event)); emit('apply')">
          <option value="relevance">相关度优先</option><option value="newest">最新发布</option>
        </select>
      </label>
      <label v-if="!digest">发布日期从
        <input type="date" :value="dateText(modelValue.date_from)" @change="setDate('date_from', value($event))" />
      </label>
      <label v-if="!digest">到（上海时间）
        <input type="date" :value="dateText(modelValue.date_to)" @change="setDate('date_to', value($event))" />
      </label>
      <label class="score-field">最低相关度 {{ Math.round(modelValue.min_relevance * 100) }}%
        <input type="range" min="0" max="1" step="0.1" :value="modelValue.min_relevance" @input="set('min_relevance', Number(value($event)))" @change="emit('apply')" />
      </label>
    </div>
    <div class="filter-actions">
      <a-button html-type="submit" type="primary" size="small">应用筛选</a-button>
      <a-button size="small" @click="emit('update:modelValue', defaultFilters()); emit('apply')">重置</a-button>
      <span v-if="digest" class="field-help">仅筛选本日报视图；不改变原始排名、修订或分享内容。状态与发布日期筛选在收件箱生效。</span>
    </div>
    <details class="saved-filter-panel">
      <summary>保存与复用筛选 · {{ savedFilters.length }}</summary>
      <div class="filter-actions">
        <label>筛选名称<input v-model="savedName" maxlength="100" placeholder="例如：AI 开源工具" /></label>
        <a-button size="small" :disabled="!savedName.trim() || busy" @click="emit('save', savedName.trim())">保存当前条件</a-button>
      </div>
      <div v-for="saved in savedFilters" :key="saved.id" class="saved-filter-row">
        <button type="button" class="text-action" @click="emit('select', saved)">{{ saved.name }}</button>
        <a-button size="mini" :disabled="busy" @click="emit('remove', saved.id)">删除此筛选</a-button>
      </div>
    </details>
  </form>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { SavedFilter, SourceOption, TopicSummary } from '@/api/intelligence'
import { defaultFilters, shanghaiDate, type HubFilters } from './workspaceState'
const props = defineProps<{ modelValue: HubFilters; sources: SourceOption[]; topics: TopicSummary[]; savedFilters: SavedFilter[]; digest: boolean; busy: boolean }>()
const emit = defineEmits<{
  (event: 'update:modelValue', value: HubFilters): void
  (event: 'apply'): void
  (event: 'save', name: string): void
  (event: 'select', value: SavedFilter): void
  (event: 'remove', id: string): void
}>()
const savedName = ref('')
const value = (event: Event) => (event.target as HTMLInputElement).value
const set = (key: keyof HubFilters, value: string | number | undefined) => emit('update:modelValue', { ...props.modelValue, [key]: value })
const dateText = (seconds?: number) => seconds === undefined ? '' : shanghaiDate(new Date(seconds * 1000))
function setDate(key: 'date_from' | 'date_to', value: string) {
  set(key, value ? Date.parse(`${value}T${key === 'date_to' ? '23:59:59' : '00:00:00'}+08:00`) / 1000 : undefined)
  emit('apply')
}
</script>
