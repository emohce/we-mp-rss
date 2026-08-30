const fs = require('node:fs')
const path = require('node:path')
const ts = require('typescript')
const { parse, compileScript, compileTemplate } = require('@vue/compiler-sfc')
const root = path.resolve(__dirname, '..')
const componentRoot = path.join(root, 'src/components/intelligence')
const files = ['src/api/intelligence.ts', 'src/components/intelligence/workspaceState.ts', 'src/components/intelligence/useIntelligenceWorkspace.ts', 'src/vite-env.d.ts'].map(file => path.join(root, file))
const options = { noEmit: true, strict: true, skipLibCheck: true, target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext, moduleResolution: ts.ModuleResolutionKind.NodeJs, baseUrl: root, paths: { '@/*': ['src/*'] }, lib: ['lib.es2020.d.ts', 'lib.dom.d.ts'], types: ['vite/client'], typeRoots: [path.join(root, 'node_modules/@types')] }
// SFC script blocks are type-checked via virtual files; templates are parsed and
// compiled, NOT advertised as vue-tsc semantic or browser acceptance.
const virtual = new Map()
for (const name of ['IntelligenceHub.vue', 'WorkspaceFilters.vue', 'ArticleReader.vue', 'ConnectorPanel.vue']) {
  const filename = path.join(componentRoot, name), source = fs.readFileSync(filename, 'utf8')
  const { descriptor, errors } = parse(source, { filename })
  if (errors.length) throw new Error(errors.join('\n'))
  const script = compileScript(descriptor, { id: name })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: name, compilerOptions: { bindingMetadata: script.bindings, expressionPlugins: ['typescript'] } })
  if (template.errors.length) throw new Error(template.errors.join('\n'))
  virtual.set(filename + '.ts', script.content)
}
const host = ts.createCompilerHost(options), readFile = host.readFile, fileExists = host.fileExists
host.readFile = file => virtual.get(file) ?? readFile(file)
host.fileExists = file => virtual.has(file) || fileExists(file)
const program = ts.createProgram([...files, ...virtual.keys(), path.join(root, 'src/env.d.ts')], options, host)
const diagnostics = ts.getPreEmitDiagnostics(program)
if (diagnostics.length) {
  process.stderr.write(ts.formatDiagnosticsWithColorAndContext(diagnostics, { getCanonicalFileName: file => file, getCurrentDirectory: () => root, getNewLine: () => '\n' }))
  process.exitCode = 1
} else process.stdout.write('Intelligence TS/scripts checked; SFC templates compiled (browser acceptance not run).\n')
