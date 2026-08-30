const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const Module = require('node:module')
const ts = require('typescript')
const { effectScope, nextTick } = require('vue')
const root = path.resolve(__dirname, '..')
// Compile only task-owned TypeScript in memory, without browser or service I/O.
function load(relative) {
  const filename = path.join(root, relative)
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS } }).outputText
  const mod = new Module(filename, module)
  mod.filename = filename; mod.paths = Module._nodeModulePaths(path.dirname(filename))
  const baseRequire = mod.require.bind(mod)
  mod.require = name => name === '@/api/intelligence' ? {} : name === './workspaceState' ? state : baseRequire(name)
  mod._compile(compiled, filename)
  return mod.exports
}
const state = load('src/components/intelligence/workspaceState.ts')
const { useIntelligenceWorkspace } = load('src/components/intelligence/useIntelligenceWorkspace.ts')
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done }); return { promise, resolve } }
const article = id => ({ id, title: id, topics: [], effective_relevance: 0.5 })
function fixture(overrides = {}, storage) {
  const effects = effectScope()
  const api = {
    bootstrapWorkspace: async () => ({ id: 'workspace-a', user_id: 'user-a', name: 'A', can_import_legacy: true }),
    listIntelligenceTopics: async () => [], listAvailableSources: async () => [], listSavedFilters: async () => [],
    listIntelligenceArticles: async () => ({ items: [], next_cursor: '', total: 0 }),
    listDigests: async () => [], getDigest: async (_, date) => ({ date, items: [] }),
    getIntelligenceInfrastructure: async () => ({}), getIntelligenceOperations: async () => ({ recent_digests: [] }),
    listIntelligenceSubscriptions: async () => [],
    ...overrides
  }
  return { hub: effects.run(() => useIntelligenceWorkspace(api, storage)), stop: () => effects.stop() }
}
test('state persistence is scoped, whitelisted and excludes body/capability URLs', () => {
  const value = state.initialState()
  value.articleId = 'private'; value.reader = { content: 'body secret' }; value.share = { url: 'capability' }
  const saved = state.serializeState(value)
  assert(!saved.includes('private')); assert(!saved.includes('body secret')); assert(!saved.includes('capability'))
  assert.notEqual(state.preferenceKey('a:b', 'c'), state.preferenceKey('a', 'b:c'))
  assert.deepEqual(state.restoreState('broken'), {})
  assert.equal(state.restoreState('{"version":3,"width":9999,"filters":{"min_relevance":8}}').width, 1440)
  assert.equal(state.restoreState('{"version":3,"filters":{"min_relevance":8}}').filters.min_relevance, 1)
})
test('Shanghai dates, bounded resizing and two-level Escape are deterministic', () => {
  assert.equal(state.shanghaiDate(new Date('2026-08-29T16:00:00Z')), '2026-08-30')
  assert.equal(state.clampWidth(2000, 1200), 1184)
  const value = state.initialState(); value.visible = true; value.articleId = 'one'
  assert.equal(state.escapeSurface(value), 'reader'); assert.equal(value.visible, true)
  assert.equal(state.escapeSurface(value), 'workspace'); assert.equal(value.visible, false)
  assert.equal(state.focusAfterRemoval(['a', 'b', 'c'], 'b'), 'c')
  assert.equal(state.focusAfterRemoval(['a', 'b'], 'b'), 'a')
})
test('request fencing rejects stale generations and stale users', () => {
  const fence = new state.RequestFence(), old = fence.begin('articles'), current = fence.begin('articles')
  assert.equal(fence.current(old), false); assert.equal(fence.current(current), true)
  fence.invalidate(); assert.equal(fence.current(current), false)
})
test('reader sandbox document forbids automatic remote media, scripts, forms and base URLs', () => {
  const html = state.readerDocument('<img src="https://example.test/tracker"><script>unsafe()</script>')
  assert(html.includes("default-src 'none'")); assert(html.includes('img-src data:;'))
  assert(html.includes("form-action 'none'")); assert(html.includes("base-uri 'none'"))
  assert(!html.includes('img-src https:')); assert(!html.includes("script-src 'unsafe-inline'"))
  const reader = fs.readFileSync(path.join(root, 'src/components/intelligence/ArticleReader.vue'), 'utf8')
  assert(reader.includes('sandbox=""')); assert(!reader.includes('v-html'))
  const main = fs.readFileSync(path.join(root, 'src/components/intelligence/IntelligenceHub.vue'), 'utf8')
  assert(!main.includes('<a-modal')); assert(main.includes(':esc-to-close="false"'))
  assert(main.includes('popup-container="#intelligence-overlay-root"'))
})
test('opening an admin workspace does not import or create subscriptions', async () => {
  let writes = 0
  const { hub, stop } = fixture({ importLegacyBatch: async () => { writes++; return {} }, createIntelligenceSubscription: async () => { writes++ } })
  await hub.open(); assert.equal(writes, 0); assert.equal(hub.ready.value, true)
  hub.close(); stop()
})
test('older article filters and reader responses cannot replace the newest selection', async () => {
  const first = deferred(), second = deferred(), readerA = deferred(), readerB = deferred()
  let calls = 0
  const { hub, stop } = fixture({ listIntelligenceArticles: () => (++calls === 1 ? first.promise : second.promise),
    getIntelligenceArticle: (_, id) => id === 'a' ? readerA.promise : readerB.promise })
  const opening = hub.open(); await nextTick(); await nextTick()
  hub.state.filters.topic = 'new'; const refresh = hub.loadArticles()
  second.resolve({ items: [article('new')], total: 1, next_cursor: '' }); await refresh
  first.resolve({ items: [article('old')], total: 1, next_cursor: '' }); await opening
  assert.equal(hub.articles.value[0].id, 'new')
  const a = hub.openArticle(article('a')), b = hub.openArticle(article('b'))
  readerB.resolve(article('b')); await b; readerA.resolve(article('a')); await a
  assert.equal(hub.reader.value.id, 'b'); stop()
})
test('close invalidates pending responses, then reopening loads a different user safely', async () => {
  const pending = deferred(); let user = 'a'
  const data = new Map(), storage = { getItem: key => data.get(key) || null, setItem: (key, value) => data.set(key, value) }
  const { hub, stop } = fixture({ bootstrapWorkspace: async () => ({ id: 'workspace-' + user, user_id: user }),
    getIntelligenceArticle: () => pending.promise }, storage)
  await hub.open(); hub.state.filters.search = 'A private preference'; await nextTick()
  const reading = hub.openArticle(article('private')); hub.close(); pending.resolve(article('private')); await reading
  assert.equal(hub.reader.value, null)
  user = 'b'; await hub.open(); assert.equal(hub.state.filters.search, ''); assert.equal(hub.reader.value, null)
  assert(data.has(state.preferenceKey('a', 'workspace-a'))); stop()
})
test('a share response for a previous date cannot leak into the new date view', async () => {
  const pending = deferred()
  const { hub, stop } = fixture({ shareDigest: () => pending.promise })
  await hub.open(); const sharing = hub.createShareLink(); await hub.selectDate('2026-08-29')
  pending.resolve({ id: 'old', url: 'https://example.test/private' }); await sharing
  assert.equal(hub.share.value, null); assert.equal(hub.digest.value.date, '2026-08-29'); stop()
})
test('operations from a previous workspace cannot replace the newly opened account', async () => {
  const old = deferred(); let user = 'a'
  const { hub, stop } = fixture({ bootstrapWorkspace: async () => ({ id: 'workspace-' + user, user_id: user }),
    getIntelligenceOperations: id => id === 'workspace-a' ? old.promise : Promise.resolve({ marker: 'b', recent_digests: [] }) })
  await hub.open(); const loadingOld = hub.setMode('system'); await nextTick()
  hub.close(); user = 'b'; await hub.open(); await hub.setMode('system')
  old.resolve({ marker: 'private-a', recent_digests: [] }); await loadingOld
  assert.equal(hub.operations.value.marker, 'b'); stop()
})
test('file import refreshes source choices and local operations without importing again', async () => {
  let imported = false, operationReads = 0, writes = 0
  const { hub, stop } = fixture({ listAvailableSources: async () => imported ? [{ id: 'imported', name: 'reading-ai', provider: 'local-feed' }] : [],
    getIntelligenceOperations: async () => ({ read: ++operationReads, recent_digests: [] }),
    importConnectorFile: async () => { writes++ } })
  await hub.open(); await hub.setMode('system'); const before = operationReads
  imported = true; await hub.refreshAfterImport()
  assert.equal(hub.sources.value[0].name, 'reading-ai'); assert(operationReads > before)
  assert.equal(writes, 0); stop()
})
