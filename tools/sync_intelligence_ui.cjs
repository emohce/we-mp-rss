// Additive local build-artifact synchronization. No install, server or deletion.
const fs = require('node:fs')
const path = require('node:path')
const { execFileSync } = require('node:child_process')
const root = path.resolve(__dirname, '..')
const source = path.join(root, 'web_ui/dist')
const target = path.join(root, 'static')
const mode = process.argv[2]
if (!['--sync', '--check'].includes(mode) || process.argv.length !== 3) throw new Error('Use --sync or --check')

function regularTree(directory, relative = '') {
  if (fs.lstatSync(directory).isSymbolicLink()) throw new Error('Symlink build tree refused')
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const item = path.join(relative, entry.name), absolute = path.join(directory, entry.name)
    if (entry.isSymbolicLink()) throw new Error('Symlink artifact refused')
    if (entry.isDirectory()) return regularTree(absolute, item)
    if (!entry.isFile()) throw new Error('Non-file artifact refused')
    return [item]
  }).sort()
}
function safeTarget(relative) {
  const absolute = path.resolve(target, relative)
  if (!absolute.startsWith(target + path.sep)) throw new Error('Artifact escaped static root')
  let current = target
  for (const part of relative.split(path.sep)) {
    current = path.join(current, part)
    if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink()) throw new Error('Symlink destination refused')
  }
  return absolute
}

if (fs.lstatSync(target).isSymbolicLink()) throw new Error('Symlink static root refused')
const files = regularTree(source)
if (!files.includes('index.html') || !files.some(file => file.startsWith('assets/'))) throw new Error('Production build missing')
// Preflight everything before copying; only the generated index may change in
// place. Old content-hashed chunks stay available for cached pages and recovery.
for (const file of files) {
  const destination = safeTarget(file)
  if (mode === '--sync' && file !== 'index.html' && fs.existsSync(destination) &&
      !fs.readFileSync(destination).equals(fs.readFileSync(path.join(source, file)))) {
    throw new Error(`Existing non-index artifact differs: ${file}`)
  }
}
if (mode === '--sync') {
  const dirty = execFileSync('git', ['status', '--porcelain', '--untracked-files=all', '--', 'static'], { cwd: root, encoding: 'utf8' })
  if (dirty.trim()) throw new Error('static has existing changes; review ownership before synchronizing')
  for (const file of files) {
    const destination = safeTarget(file)
    if (fs.existsSync(destination) && fs.readFileSync(destination).equals(fs.readFileSync(path.join(source, file)))) continue
    fs.mkdirSync(path.dirname(destination), { recursive: true })
    fs.copyFileSync(path.join(source, file), destination)
  }
}
for (const file of files) {
  const destination = safeTarget(file)
  if (!fs.existsSync(destination) || !fs.readFileSync(destination).equals(fs.readFileSync(path.join(source, file)))) {
    throw new Error(`Served artifact differs or is missing: ${file}`)
  }
}
const index = fs.readFileSync(path.join(target, 'index.html'), 'utf8')
const references = [...index.matchAll(/(?:src|href)=["']\/(?:static\/)?(assets\/[^"']+|logo\.svg)["']/g)].map(match => match[1])
for (const reference of references) if (!fs.existsSync(safeTarget(reference))) throw new Error('Missing index artifact')
if (!references.some(reference => reference.endsWith('.js'))) throw new Error('Module entry missing')
process.stdout.write(`Verified ${files.length} build files and ${references.length} local index references; old artifacts retained.\n`)
