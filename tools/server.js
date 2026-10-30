// Server quản lý dự án: đọc/ghi PROJECT.md theo từng khối và chạy một số lệnh git cố định.
// Chạy: node tools/server.js [port]   (mặc định 8765, chỉ nghe 127.0.0.1, không cần npm install)
'use strict'

const http = require('http')
const fs = require('fs')
const path = require('path')
const crypto = require('crypto')
const { execFile } = require('child_process')

const ROOT = path.resolve(__dirname, '..')
const DOC = path.join(ROOT, 'PROJECT.md')
const PORT = Number(process.argv.find((a) => /^\d+$/.test(a))) || 8765
const MEMBERS = ['Nam', 'Lâm']
const STATIC = { '/': 'index.html', '/index.html': 'index.html', '/app.js': 'app.js' }

// ===== Định dạng PROJECT.md =====
const HEAD_RE = /^###\s+([A-Z]{1,3}-\d{2,})\s*(.*)$/
const ATTR_RE = /^- \*\*([^*]+?):\*\*[ \t]?(.*)$/
const LOG_RE = /^- \[([^\]·]+?) · (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\] \[([^\]]+)\] (.*)$/
const LOG_LABEL = '**Nhật ký:**'
const KIND_RE = /^<!--\s*loại:\s*([A-Z]{1,3})\s*-->$/
const BOUNDARY_RE = /^#{1,3}\s/ // heading cấp 1-3 kết thúc một khối
const CONFLICT_RE = /^(<{7}|={7}|>{7})( |$)/

const sha = (s) => crypto.createHash('sha1').update(s).digest('hex').slice(0, 12)
const oneLine = (s) => String(s ?? '').replace(/\s*[\r\n]+\s*/g, ' ').trim()

class HttpError extends Error {
  constructor(status, message, extra = {}) {
    super(message)
    this.status = status
    this.extra = extra
  }
}

function parse(text) {
  const eol = text.includes('\r\n') ? '\r\n' : '\n'
  const lines = text.split(/\r?\n/)
  const blocks = []
  const containers = []
  let container = null
  let inFence = false
  let cur = null
  const close = (end) => {
    if (!cur) return
    cur.end = end
    let ce = end
    while (ce > cur.start + 1 && lines[ce - 1].trim() === '') ce--
    cur.contentEnd = ce
    // thuộc tính: các dòng "- **Khóa:** giá trị" liền nhau ngay sau heading
    let i = cur.start + 1
    while (i < ce && lines[i].trim() === '') i++
    cur.attrs = []
    while (i < ce && ATTR_RE.test(lines[i])) {
      const m = lines[i].match(ATTR_RE)
      cur.attrs.push({ key: m[1].trim(), value: m[2].trim(), line: i })
      i++
    }
    cur.attrEnd = cur.attrs.length ? cur.attrs[cur.attrs.length - 1].line + 1 : cur.start + 1
    // nhật ký: từ nhãn "**Nhật ký:**" (hoặc dòng nhật ký đầu tiên) tới cuối khối
    cur.logs = []
    cur.logStart = ce
    for (let j = cur.attrEnd; j < ce; j++) {
      if (lines[j].trim() === LOG_LABEL) { cur.logStart = Math.min(cur.logStart, j); continue }
      const m = lines[j].match(LOG_RE)
      if (m) {
        cur.logStart = Math.min(cur.logStart, j)
        cur.logs.push({ author: m[1].trim(), time: m[2], kind: m[3], text: m[4], line: j })
      }
    }
    let coreEnd = cur.logStart
    while (coreEnd > cur.start + 1 && lines[coreEnd - 1].trim() === '') coreEnd--
    cur.coreEnd = coreEnd
    cur.core = lines.slice(cur.start, coreEnd).join('\n')
    cur.body = lines.slice(cur.attrEnd, coreEnd).join('\n').trim()
    cur.hash = sha(cur.core)
    blocks.push(cur)
    cur = null
  }
  lines.forEach((line, i) => {
    if (/^\s*(```|~~~)/.test(line)) inFence = !inFence
    if (inFence) return
    if (BOUNDARY_RE.test(line)) {
      close(i)
      const h = line.match(HEAD_RE)
      if (h) {
        cur = { id: h[1], prefix: h[1].split('-')[0], title: h[2].trim(), start: i, container: container && container.title }
        if (container) container.ids.push(h[1])
      } else if (/^##\s/.test(line) || /^#\s/.test(line)) {
        if (container) container.end = i
        container = /^##\s/.test(line) ? { title: line.replace(/^##\s+/, '').trim(), start: i, prefix: null, ids: [] } : null
        if (container) containers.push(container)
      }
      return
    }
    const k = line.trim().match(KIND_RE)
    if (k && container && !cur) container.prefix = k[1]
  })
  close(lines.length)
  if (container) container.end = lines.length
  containers.forEach((c) => { if (c.end === undefined) c.end = lines.length })
  return { eol, lines, blocks, containers, hasConflict: lines.some((l) => CONFLICT_RE.test(l)) }
}

function forClient(text) {
  const p = parse(text)
  return {
    hash: sha(text),
    conflict: p.hasConflict,
    containers: p.containers.map((c) => ({ title: c.title, prefix: c.prefix, ids: c.ids })),
    blocks: p.blocks.map((b) => ({
      id: b.id, prefix: b.prefix, title: b.title, container: b.container,
      attrs: Object.fromEntries(b.attrs.map((a) => [a.key, a.value])), attrOrder: b.attrs.map((a) => a.key),
      body: b.body, core: b.core, hash: b.hash,
      logs: b.logs.map(({ author, time, kind, text }) => ({ author, time, kind, text })),
    })),
  }
}

function nowStamp() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

// Áp một thao tác lên văn bản hiện tại; chỉ đụng tới các dòng của khối liên quan.
function applyOp(text, op) {
  const doc = parse(text)
  if (doc.hasConflict) throw new HttpError(409, 'PROJECT.md đang có xung đột git chưa giải quyết — hãy xử lý xung đột trước.')
  const lines = doc.lines
  const find = (id) => {
    const b = doc.blocks.find((x) => x.id === id)
    if (!b) throw new HttpError(404, `Không tìm thấy ${id} trong PROJECT.md (có thể vừa bị đổi ở nơi khác).`)
    return b
  }
  let result = {}
  switch (op.op) {
    case 'setField': {
      const b = find(op.id)
      const key = oneLine(op.key)
      if (!key || key.includes('*')) throw new HttpError(400, 'Tên trường không hợp lệ')
      const value = oneLine(op.value)
      const a = b.attrs.find((x) => x.key === key)
      const cur = a ? a.value : ''
      if (cur === value) break
      if (op.old !== undefined && cur !== oneLine(op.old)) {
        throw new HttpError(409, `${op.id} · "${key}" vừa được đổi thành "${cur || '(trống)'}" ở nơi khác. Đã tải bản mới.`)
      }
      const newLine = `- **${key}:** ${value}`.trimEnd()
      if (a) lines[a.line] = newLine
      else lines.splice(b.attrEnd, 0, newLine)
      break
    }
    case 'setTitle': {
      const b = find(op.id)
      const title = oneLine(op.title)
      if (!title) throw new HttpError(400, 'Tên không được để trống')
      if (op.old !== undefined && b.title !== oneLine(op.old) && b.title !== title) {
        throw new HttpError(409, `Tên của ${op.id} vừa được đổi ở nơi khác thành "${b.title}". Đã tải bản mới.`)
      }
      lines[b.start] = `### ${b.id} ${title}`
      break
    }
    case 'raw': {
      const b = find(op.id)
      if (op.hash !== b.hash) {
        throw new HttpError(409, `${op.id} vừa được sửa ở nơi khác. Đã tải bản mới — nội dung bạn đang soạn vẫn được giữ trong ô sửa.`)
      }
      const raw = String(op.raw ?? '').replace(/\r\n/g, '\n').replace(/\s+$/, '').split('\n')
      const h = raw[0].match(HEAD_RE)
      if (!h || h[1] !== b.id) throw new HttpError(400, `Dòng đầu phải giữ nguyên dạng "### ${b.id} Tên".`)
      for (const l of raw.slice(1)) {
        if (BOUNDARY_RE.test(l)) throw new HttpError(400, `Không dùng heading cấp 1–3 trong nội dung khối (dòng "${l}"). Dùng #### trở xuống.`)
        if (LOG_RE.test(l) || l.trim() === LOG_LABEL) throw new HttpError(400, 'Nhật ký chỉ được thêm bằng ô "Thêm nhật ký", không sửa trong chế độ thô.')
        if (CONFLICT_RE.test(l)) throw new HttpError(400, 'Nội dung có dấu xung đột git.')
      }
      const hasLogs = b.logs.length > 0
      lines.splice(b.start, b.coreEnd - b.start, ...raw)
      // giữ đúng một dòng trống giữa phần nội dung và phần nhật ký
      if (hasLogs) {
        const after = b.start + raw.length
        let k = after
        while (k < lines.length && lines[k].trim() === '') k++
        lines.splice(after, k - after, '')
      }
      break
    }
    case 'addLog': {
      const b = find(op.id)
      if (!MEMBERS.includes(op.author)) throw new HttpError(400, 'Người ghi phải là Nam hoặc Lâm')
      const kind = oneLine(op.kind)
      const textLine = oneLine(op.text)
      if (!kind || /[[\]]/.test(kind)) throw new HttpError(400, 'Loại nhật ký không hợp lệ')
      if (!textLine) throw new HttpError(400, 'Nội dung trống')
      const entry = `- [${op.author} · ${nowStamp()}] [${kind}] ${textLine}`
      if (b.logs.length) lines.splice(b.logs[b.logs.length - 1].line + 1, 0, entry)
      else lines.splice(b.contentEnd, 0, '', LOG_LABEL, entry)
      break
    }
    case 'create': {
      const prefix = String(op.prefix || '')
      const c = doc.containers.find((x) => x.prefix === prefix)
      if (!c) throw new HttpError(400, `Không có mục chứa loại ${prefix} trong PROJECT.md`)
      const title = oneLine(op.title)
      if (!title) throw new HttpError(400, 'Tên không được để trống')
      // ID không bao giờ dùng lại: lấy số lớn nhất từng có trong file + 1
      const nums = [...text.matchAll(new RegExp(`\\b${prefix}-(\\d{2,})\\b`, 'g'))].map((m) => Number(m[1]))
      const width = Math.max(2, ...[...text.matchAll(new RegExp(`### ${prefix}-(\\d+)`, 'g'))].map((m) => m[1].length))
      const id = `${prefix}-${String((nums.length ? Math.max(...nums) : 0) + 1).padStart(width, '0')}`
      const attrs = Object.entries(op.attrs || {}).map(([k, v]) => `- **${oneLine(k)}:** ${oneLine(v)}`.trimEnd())
      let at = c.end
      while (at > c.start + 1 && lines[at - 1].trim() === '') at--
      const block = ['', `### ${id} ${title}`, ...attrs]
      const body = String(op.body || '').trim()
      if (body) block.push('', ...body.split(/\r?\n/))
      lines.splice(at, 0, ...block)
      result = { id }
      break
    }
    default:
      throw new HttpError(400, 'Thao tác không hợp lệ')
  }
  return { text: lines.join(doc.eol), result }
}

// ===== Ghi file an toàn: khóa tuần tự + kiểm tra file không bị đổi giữa lúc đọc và lúc ghi =====
let queue = Promise.resolve()
const withLock = (fn) => {
  const run = queue.then(fn, fn)
  queue = run.catch(() => {})
  return run
}
const readDoc = () => fs.readFileSync(DOC, 'utf8')

function writeOp(op) {
  return withLock(() => {
    for (let attempt = 0; attempt < 3; attempt++) {
      const before = readDoc()
      const { text, result } = applyOp(before, op)
      if (text === before) return { result, doc: forClient(before) }
      // nếu file vừa bị đổi bởi tiến trình khác (editor, git) thì đọc lại và áp lại thao tác lên bản mới
      if (readDoc() !== before) continue
      const tmp = `${DOC}.tmp-${process.pid}`
      fs.writeFileSync(tmp, text, 'utf8')
      fs.renameSync(tmp, DOC)
      return { result, doc: forClient(text) }
    }
    throw new HttpError(409, 'PROJECT.md đang bị thay đổi liên tục bởi tiến trình khác, thử lại sau.')
  })
}

// ===== Git (chỉ các lệnh cố định) =====
function git(args, timeout = 120000) {
  return new Promise((resolve) => {
    execFile('git', args, {
      cwd: ROOT, timeout, windowsHide: true, maxBuffer: 10 * 1024 * 1024,
      env: { ...process.env, GIT_TERMINAL_PROMPT: '0', GIT_EDITOR: 'true', GIT_MERGE_AUTOEDIT: 'no' },
    }, (err, stdout, stderr) => resolve({ code: err ? (typeof err.code === 'number' ? err.code : 1) : 0, out: String(stdout), err: String(stderr) }))
  })
}
const logOf = (args, r) => `$ git ${args.join(' ')}\n${(r.out + r.err).trim()}`

let gitDirCache = null
async function gitDir() {
  if (!gitDirCache) gitDirCache = path.resolve(ROOT, (await git(['rev-parse', '--git-dir'])).out.trim())
  return gitDirCache
}
const isMerging = async () => fs.existsSync(path.join(await gitDir(), 'MERGE_HEAD'))
async function gitStatus(fetch) {
  let fetchError = ''
  if (fetch) {
    const f = await git(['fetch', '--quiet'], 60000)
    if (f.code) fetchError = (f.err || f.out).trim()
  }
  const [branch, docSt, conflicted, counts, upstream] = await Promise.all([
    git(['rev-parse', '--abbrev-ref', 'HEAD']),
    git(['status', '--porcelain', '--', 'PROJECT.md']),
    git(['diff', '--name-only', '--diff-filter=U']),
    git(['rev-list', '--left-right', '--count', 'HEAD...@{u}']),
    git(['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}']),
  ])
  const [ahead, behind] = counts.code ? [0, 0] : counts.out.trim().split(/\s+/).map(Number)
  return {
    branch: branch.out.trim(),
    upstream: upstream.code ? '' : upstream.out.trim(),
    docDirty: docSt.out.trim() !== '',
    merging: await isMerging(),
    conflicted: conflicted.out.split(/\r?\n/).filter(Boolean),
    ahead, behind, fetchError,
  }
}

// Mã các khối bị đổi so với HEAD -> dùng cho commit message "Nam: cập nhật T-03, R-02"
async function changedIds() {
  const tracked = await git(['ls-files', '--error-unmatch', 'PROJECT.md'])
  if (tracked.code) return null
  const diff = await git(['diff', '-U0', 'HEAD', '--', 'PROJECT.md'])
  const doc = parse(readDoc())
  const ids = []
  for (const m of diff.out.matchAll(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@/gm)) {
    const startLine = Number(m[1]) - 1
    const count = m[2] === undefined ? 1 : Math.max(Number(m[2]), 1)
    for (let l = startLine; l < startLine + count; l++) {
      const b = doc.blocks.find((x) => l >= x.start && l < x.end)
      if (b && !ids.includes(b.id)) ids.push(b.id)
    }
  }
  return ids
}

function conflictHunks(text) {
  const lines = text.split(/\r?\n/)
  const hunks = []
  let lastHead = ''
  for (let i = 0; i < lines.length; i++) {
    if (HEAD_RE.test(lines[i]) || /^##\s/.test(lines[i])) lastHead = lines[i].replace(/^#+\s*/, '')
    if (!lines[i].startsWith('<<<<<<<')) continue
    const h = { index: hunks.length, context: lastHead, ours: [], theirs: [], start: i }
    let j = i + 1
    while (j < lines.length && !/^={7}( |$)/.test(lines[j])) h.ours.push(lines[j++])
    j++
    while (j < lines.length && !lines[j].startsWith('>>>>>>>')) h.theirs.push(lines[j++])
    h.end = j
    hunks.push(h)
    i = j
  }
  return { lines, hunks }
}

// Lấy phần nội dung theo bản người dùng chọn. Nhật ký là dữ liệu chỉ-thêm-vào-cuối nên dòng nhật ký của
// bên không được chọn vẫn được giữ (thêm sau nhật ký của bên được chọn) — không bao giờ mất bình luận.
function pickHunk(h, choice) {
  if (choice === 'both') return [...h.ours, ...h.theirs.filter((l) => !(LOG_RE.test(l) && h.ours.includes(l)))]
  if (choice === 'both-rev') return [...h.theirs, ...h.ours.filter((l) => !(LOG_RE.test(l) && h.theirs.includes(l)))]
  const [mine, other] = choice === 'ours' ? [h.ours, h.theirs] : [h.theirs, h.ours]
  const result = [...mine]
  const extraLogs = other.filter((l) => LOG_RE.test(l) && !mine.includes(l))
  if (!extraLogs.length) return result
  let at = -1
  result.forEach((l, i) => { if (LOG_RE.test(l) || l.trim() === LOG_LABEL) at = i })
  if (at >= 0) {
    result.splice(at + 1, 0, ...extraLogs)
  } else {
    const needLabel = other.some((l) => l.trim() === LOG_LABEL)
    if (needLabel && result.length && result[result.length - 1].trim() !== '') result.push('')
    result.push(...(needLabel ? [LOG_LABEL] : []), ...extraLogs)
  }
  return result
}
const keptLogs = (h, choice) => pickHunk(h, choice).filter((l) => LOG_RE.test(l))

async function pull(log) {
  const args = ['-c', 'merge.conflictStyle=merge', 'pull', '--no-rebase', '--no-edit']
  const r = await git(args, 180000)
  log.push(logOf(args, r))
  if (!r.code) return { ok: true }
  const st = await gitStatus(false)
  if (st.merging && st.conflicted.includes('PROJECT.md')) {
    const others = st.conflicted.filter((f) => f !== 'PROJECT.md')
    return { ok: false, conflict: true, others, error: 'Có xung đột trong PROJECT.md — chọn bản giữ lại cho từng đoạn.' }
  }
  if (st.merging && st.conflicted.length) {
    return { ok: false, conflict: false, others: st.conflicted, error: `Xung đột ở file khác: ${st.conflicted.join(', ')}. Hãy xử lý trong VS Code hoặc bấm "Hủy gộp".` }
  }
  return { ok: false, error: 'Không pull được (xem log). Nếu có file khác đang sửa dở bị đụng, hãy commit/stash trong VS Code trước.' }
}

async function push(log) {
  const args = ['push']
  const r = await git(args, 180000)
  log.push(logOf(args, r))
  if (r.code) return { ok: false, error: 'Push thất bại (xem log). Không bao giờ force push — hãy Pull rồi thử lại.' }
  return { ok: true }
}

async function commitPush(author) {
  if (!MEMBERS.includes(author)) throw new HttpError(400, 'Chọn người dùng (Nam hoặc Lâm) trước')
  const log = []
  const st = await gitStatus(false)
  if (st.merging) return { ok: false, conflict: st.conflicted.includes('PROJECT.md'), error: 'Đang gộp dở — hãy hoàn tất hoặc hủy gộp trước.', log }
  if (st.docDirty) {
    const ids = await changedIds()
    const what = ids === null ? 'tạo PROJECT.md' : ids.length ? `cập nhật ${ids.slice(0, 8).join(', ')}${ids.length > 8 ? '…' : ''}` : 'cập nhật PROJECT.md'
    for (const args of [['add', '--', 'PROJECT.md'], ['commit', '-m', `${author}: ${what}`, '--', 'PROJECT.md']]) {
      const r = await git(args)
      log.push(logOf(args, r))
      if (r.code) return { ok: false, error: 'Commit thất bại (xem log).', log }
    }
  }
  // luôn pull trước khi push
  const p = await pull(log)
  if (!p.ok) return { ...p, log, pushAfterResolve: true }
  const after = await gitStatus(false)
  if (!after.ahead) return { ok: true, log, message: 'Không có gì mới để đẩy lên.' }
  return { ...(await push(log)), log }
}

async function resolveConflict(body) {
  if (!MEMBERS.includes(body.author)) throw new HttpError(400, 'Chọn người dùng (Nam hoặc Lâm) trước')
  return withLock(async () => {
    const { lines, hunks } = conflictHunks(readDoc())
    if (!hunks.length) throw new HttpError(400, 'Không còn xung đột trong PROJECT.md')
    const choices = body.choices || []
    if (choices.length !== hunks.length || choices.some((c) => !['ours', 'theirs', 'both', 'both-rev'].includes(c))) {
      throw new HttpError(400, 'Phải chọn bản giữ lại cho mọi đoạn xung đột')
    }
    const out = []
    let pos = 0
    hunks.forEach((h, i) => {
      out.push(...lines.slice(pos, h.start))
      out.push(...pickHunk(h, choices[i]))
      pos = h.end + 1
    })
    out.push(...lines.slice(pos))
    const eol = readDoc().includes('\r\n') ? '\r\n' : '\n'
    const text = out.join(eol)
    if (text.split(/\r?\n/).some((l) => CONFLICT_RE.test(l))) throw new HttpError(400, 'Kết quả vẫn còn dấu xung đột')
    fs.writeFileSync(DOC, text, 'utf8')
    const log = []
    for (const args of [['add', '--', 'PROJECT.md']]) log.push(logOf(args, await git(args)))
    const st = await gitStatus(false)
    if (st.conflicted.length) {
      return { ok: false, log, error: `Đã lưu PROJECT.md. Còn xung đột ở file khác: ${st.conflicted.join(', ')} — xử lý trong VS Code rồi commit.` }
    }
    const args = ['commit', '--no-edit']
    const r = await git(args)
    log.push(logOf(args, r))
    if (r.code) return { ok: false, log, error: 'Commit gộp thất bại (xem log).' }
    if (body.push) return { ...(await push(log)), log }
    return { ok: true, log }
  })
}

// ===== HTTP =====
function send(res, status, data, type = 'application/json; charset=utf-8') {
  const body = typeof data === 'string' || Buffer.isBuffer(data) ? data : JSON.stringify(data)
  res.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' })
  res.end(body)
}
function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0
    const chunks = []
    req.on('data', (c) => {
      size += c.length
      if (size > 1024 * 1024) { reject(new HttpError(413, 'Dữ liệu quá lớn')); req.destroy() } else chunks.push(c)
    })
    req.on('end', () => {
      try { resolve(chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {}) } catch { reject(new HttpError(400, 'JSON không hợp lệ')) }
    })
  })
}

const hostsOk = new Set([`localhost:${PORT}`, `127.0.0.1:${PORT}`])
const originsOk = new Set([`http://localhost:${PORT}`, `http://127.0.0.1:${PORT}`])

const server = http.createServer(async (req, res) => {
  try {
    // chặn DNS rebinding và trang web lạ gọi vào server local
    if (!hostsOk.has(req.headers.host)) throw new HttpError(403, 'Host không hợp lệ')
    if (req.method !== 'GET' && req.headers.origin && !originsOk.has(req.headers.origin)) throw new HttpError(403, 'Origin không hợp lệ')
    const url = new URL(req.url, `http://${req.headers.host}`)
    const p = url.pathname

    if (req.method === 'GET' && STATIC[p]) {
      const file = path.join(__dirname, STATIC[p])
      return send(res, 200, fs.readFileSync(file), p.endsWith('.js') ? 'text/javascript; charset=utf-8' : 'text/html; charset=utf-8')
    }
    if (req.method === 'GET' && p === '/api/doc') return send(res, 200, forClient(readDoc()))
    if (req.method === 'GET' && p === '/api/version') return send(res, 200, { hash: sha(readDoc()) })
    if (req.method === 'GET' && p === '/api/git/status') return send(res, 200, await gitStatus(url.searchParams.get('fetch') === '1'))
    if (req.method === 'GET' && p === '/api/git/conflict') {
      const { hunks } = conflictHunks(readDoc())
      return send(res, 200, {
        hunks: hunks.map((h) => ({
          index: h.index, context: h.context, ours: h.ours, theirs: h.theirs,
          hasLogs: [...h.ours, ...h.theirs].some((l) => LOG_RE.test(l)),
          logsKept: keptLogs(h, 'ours').length,
        })),
        status: await gitStatus(false),
      })
    }
    if (req.method !== 'POST') throw new HttpError(404, 'Không tìm thấy')

    const body = await readBody(req)
    if (p === '/api/op') {
      if (await isMerging()) throw new HttpError(409, 'Đang gộp git dở dang — hãy xử lý xung đột trước khi sửa.')
      const r = await writeOp(body)
      return send(res, 200, { ok: true, ...r.result, doc: r.doc })
    }
    if (p === '/api/git/pull') {
      return withLock(async () => {
        const st = await gitStatus(false)
        if (st.merging) return send(res, 200, { ok: false, conflict: st.conflicted.includes('PROJECT.md'), error: 'Đang gộp dở — hãy hoàn tất hoặc hủy gộp trước.' })
        if (st.docDirty) return send(res, 200, { ok: false, error: 'PROJECT.md có thay đổi chưa commit — bấm "Commit & Push" (tự pull trước khi push).' })
        const log = []
        const r = await pull(log)
        return send(res, 200, { ...r, log })
      })
    }
    if (p === '/api/git/commit-push') return send(res, 200, await withLock(() => commitPush(body.author)))
    if (p === '/api/git/resolve') return send(res, 200, await resolveConflict(body))
    if (p === '/api/git/abort') {
      return withLock(async () => {
        const args = ['merge', '--abort']
        const r = await git(args)
        return send(res, 200, { ok: !r.code, log: [logOf(args, r)], error: r.code ? 'Không hủy được gộp (xem log).' : '' })
      })
    }
    throw new HttpError(404, 'Không tìm thấy')
  } catch (e) {
    const status = e instanceof HttpError ? e.status : 500
    if (status === 500) console.error(e)
    let extra = e.extra || {}
    if (status === 409 && fs.existsSync(DOC)) extra = { ...extra, doc: forClient(readDoc()) }
    send(res, status, { error: e.message, ...extra })
  }
})

if (require.main === module) {
  if (!fs.existsSync(DOC)) {
    console.error(`Không thấy ${DOC}`)
    process.exit(1)
  }
  server.listen(PORT, '127.0.0.1', () => console.log(`Quản lý dự án: http://localhost:${PORT}  (Ctrl+C để dừng)`))
}

module.exports = { parse, applyOp, conflictHunks, pickHunk }
