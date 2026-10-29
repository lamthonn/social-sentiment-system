/* Giao diện quản lý đề tài - JS thuần, đọc/ghi qua pm/server.py */
'use strict'

const S = { config: null, user: '', items: [], byId: {}, dirty: false, filters: {} }
const $ = (sel, root = document) => root.querySelector(sel)
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)]
const REF_RE = /\b([A-Z]{1,6}-\d{3,4})\b/g
const CHECK_RE = /^(\s*[-*] \[)( |x|X)(\] +)(?=\S)/gm
const MAIN_TABS = [['task', 'Đầu việc'], ['decision', 'Cần chốt'], ['question', 'Khảo sát'], ['doc', 'Tài liệu']]
const CLOSED = ['done', 'dropped', 'decided', 'cancelled', 'answered', 'skipped', 'selected', 'rejected', 'closed', 'stable', 'final', 'wontfix', 'out', 'failed']

// ===== tiện ích =====
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
const asList = (v) => (Array.isArray(v) ? v : v ? String(v).split(',').map((x) => x.trim()).filter(Boolean) : [])
const typeOf = (key) => S.config.types[key]
const isClosed = (status) => CLOSED.includes(status)
function statusInfo(typeKey, status) {
  const t = typeOf(typeKey)
  return (t && t.statuses.find((s) => s.key === status)) || { key: status, label: status || '—', color: 'gray' }
}
const statusText = (typeKey, status) => {
  const s = statusInfo(typeKey, status)
  return `<span class="status ${s.color}">${esc(s.label)}</span>`
}
function toast(msg, isError = false) {
  const el = $('#toast')
  el.textContent = msg
  el.className = 'toast' + (isError ? ' error' : '')
  clearTimeout(toast.t)
  toast.t = setTimeout(() => el.classList.add('hidden'), isError ? 6000 : 2200)
}
async function api(path, opts = {}) {
  const init = { method: opts.method || 'GET', headers: {} }
  if (opts.body !== undefined) {
    if (opts.raw) {
      init.body = opts.body
      init.headers['Content-Type'] = opts.contentType || 'application/octet-stream'
      if (opts.filename) init.headers['X-Filename'] = encodeURIComponent(opts.filename)
    } else {
      init.body = JSON.stringify(opts.body)
      init.headers['Content-Type'] = 'application/json'
    }
  }
  const res = await fetch(path, init)
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = new Error(data.error || `Lỗi ${res.status}`)
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

// ===== markdown =====
function renderMd(src) {
  if (!src || !src.trim()) return '<p class="muted">Chưa có nội dung.</p>'
  let html = window.marked ? marked.parse(src, { gfm: true, breaks: true }) : `<pre>${esc(src)}</pre>`
  html = html.replace(/(src|href)="\.\.\/assets\//g, '$1="/assets/')
  if (window.DOMPurify) html = DOMPurify.sanitize(html)
  const wrap = document.createElement('div')
  wrap.className = 'md'
  wrap.innerHTML = html
  $$('pre > code.language-mermaid', wrap).forEach((code) => {
    const div = document.createElement('div')
    div.className = 'mermaid'
    div.textContent = code.textContent
    code.parentElement.replaceWith(div)
  })
  linkRefs(wrap)
  return wrap.outerHTML
}
function linkRefs(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  const nodes = []
  while (walker.nextNode()) {
    const n = walker.currentNode
    if (n.parentElement.closest('a, code, pre, .mermaid')) continue
    REF_RE.lastIndex = 0
    if (REF_RE.test(n.nodeValue)) nodes.push(n)
  }
  nodes.forEach((n) => {
    const span = document.createElement('span')
    span.innerHTML = esc(n.nodeValue).replace(REF_RE, (m, id) =>
      S.byId[id] ? `<a class="ref" href="#/item/${id}" title="${esc(S.byId[id].meta.title)}">${id}</a>` : m,
    )
    n.replaceWith(...span.childNodes)
  })
}
function afterRender(root) {
  if (window.mermaid) {
    const nodes = $$('.mermaid:not([data-processed])', root)
    if (nodes.length) mermaid.run({ nodes }).catch((e) => console.warn('mermaid', e))
  }
  $$('.md img', root).forEach((img) => (img.onclick = () => openModal(`<img src="${esc(img.getAttribute('src'))}" alt="">`, true)))
}

// ===== modal =====
function openModal(html, wide = false) {
  $('#modalBox').className = 'modal-box' + (wide ? ' wide' : '')
  $('#modalBox').innerHTML = html
  $('#modal').classList.remove('hidden')
  $('#modalBox input, #modalBox select, #modalBox textarea')?.focus()
}
function closeModal() {
  $('#modal').classList.add('hidden')
  $('#modalBox').innerHTML = ''
}
$('#modal').addEventListener('click', (e) => e.target.id === 'modal' && closeModal())
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeModal()
    closeMenu()
  }
})

// ===== dữ liệu =====
async function loadItems() {
  S.items = await api('/api/items')
  S.byId = {}
  S.items.forEach((i) => (S.byId[i.meta.id] = i))
}
const itemsOf = (typeKey) =>
  S.items.filter((i) => i.meta.type === typeKey).sort((a, b) => a.meta.id.localeCompare(b.meta.id, 'en', { numeric: true }))
function upsertSummary(full) {
  const last = full.comments[full.comments.length - 1]
  const summary = {
    meta: full.meta,
    checklist: full.checklist,
    comment_count: full.comments.length,
    last_comment: last ? { time: last.time, author: last.author } : null,
    recent_comments: full.comments.slice(-3).map((c) => ({ time: c.time, author: c.author, text: c.text.slice(0, 160) })),
    excerpt: full.content.slice(0, 400),
    warnings: full.warnings,
    file: full.file,
  }
  const idx = S.items.findIndex((i) => i.meta.id === full.meta.id)
  if (idx >= 0) S.items[idx] = summary
  else S.items.push(summary)
  S.byId[full.meta.id] = summary
}

// ===== dán ảnh / kéo thả file =====
function insertAtCursor(ta, text) {
  const { selectionStart: a, selectionEnd: b } = ta
  ta.value = ta.value.slice(0, a) + text + ta.value.slice(b)
  ta.selectionStart = ta.selectionEnd = a + text.length
  ta.dispatchEvent(new Event('input'))
}
function attachUpload(ta, zone = ta) {
  const handle = async (files) => {
    for (const file of files) {
      const token = `![Đang tải ${file.name || 'ảnh'}…]()`
      insertAtCursor(ta, token)
      try {
        const res = await api('/api/upload', { method: 'POST', body: file, raw: true, contentType: file.type, filename: file.name || 'anh.png' })
        const name = (file.name || 'ảnh').replace(/[[\]]/g, '')
        ta.value = ta.value.replace(token, res.is_image ? `![${name}](${res.path})` : `[${name}](${res.path})`)
      } catch (e) {
        ta.value = ta.value.replace(token, '')
        toast('Tải file lỗi: ' + e.message, true)
      }
      ta.dispatchEvent(new Event('input'))
    }
  }
  ta.addEventListener('paste', (e) => {
    const files = [...(e.clipboardData?.items || [])].filter((it) => it.kind === 'file').map((it) => it.getAsFile()).filter(Boolean)
    if (files.length) {
      e.preventDefault()
      handle(files)
    }
  })
  zone.addEventListener('dragover', (e) => {
    if ([...e.dataTransfer.types].includes('Files')) {
      e.preventDefault()
      zone.classList.add('dragover')
    }
  })
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'))
  zone.addEventListener('drop', (e) => {
    if (!e.dataTransfer.files.length) return
    e.preventDefault()
    zone.classList.remove('dragover')
    handle([...e.dataTransfer.files])
  })
}

// ===== thanh tab =====
function currentTab() {
  const [page, arg] = location.hash.replace(/^#\/?/, '').split('/')
  if (!page) return 'home'
  if (page === 'list') return arg
  if (page === 'item') return S.byId[arg]?.meta.type
  return page
}
function renderTabs() {
  const cur = currentTab()
  const otherKeys = Object.keys(S.config.types).filter((k) => !MAIN_TABS.some(([m]) => m === k))
  const otherActive = otherKeys.includes(cur) || cur === 'trace'
  $('#tabs').innerHTML =
    `<a href="#/" class="${cur === 'home' ? 'active' : ''}">Tổng quan</a>` +
    MAIN_TABS.map(([k, label]) => `<a href="#/list/${k}" class="${cur === k ? 'active' : ''}">${label}</a>`).join('') +
    `<a href="#" id="moreBtn" class="${otherActive ? 'active' : ''}">${otherActive && cur !== 'trace' ? esc(typeOf(cur).label) : cur === 'trace' ? 'Truy vết' : 'Khác'} ▾</a>`
  $('#moreBtn').onclick = (e) => {
    e.preventDefault()
    if ($('.menu')) return closeMenu()
    const r = e.target.getBoundingClientRect()
    const menu = document.createElement('div')
    menu.className = 'menu'
    menu.style.top = `${r.bottom + window.scrollY + 4}px`
    menu.style.left = `${Math.min(r.left, window.innerWidth - 220)}px`
    menu.innerHTML =
      otherKeys.map((k) => `<a href="#/list/${k}">${esc(typeOf(k).label)} <span class="muted small">${itemsOf(k).length}</span></a>`).join('') +
      '<a href="#/trace">Truy vết câu hỏi nghiên cứu</a>'
    document.body.appendChild(menu)
    menu.onclick = closeMenu
    setTimeout(() => document.addEventListener('click', closeMenu, { once: true }))
  }
}
function closeMenu() {
  $('.menu')?.remove()
}

// ===== router =====
async function route() {
  if (S.dirty && !confirm('Bạn có thay đổi chưa lưu. Rời trang?')) {
    history.replaceState(null, '', S.lastHash)
    return
  }
  S.dirty = false
  S.lastHash = location.hash
  closeMenu()
  const [page, ...rest] = location.hash.replace(/^#\/?/, '').split('/').map(decodeURIComponent)
  const main = $('#main')
  window.scrollTo(0, 0)
  try {
    if (page === 'item') await renderItem(main, rest[0])
    else if (page === 'list') renderList(main, rest[0])
    else if (page === 'trace') renderTrace(main)
    else if (page === 'search') renderSearch(main, rest.join('/'))
    else renderHome(main)
  } catch (e) {
    main.innerHTML = `<div class="warn">Lỗi: ${esc(e.message)}</div>`
  }
  renderTabs()
}
window.addEventListener('hashchange', route)
window.addEventListener('beforeunload', (e) => {
  if (S.dirty) {
    e.preventDefault()
    e.returnValue = ''
  }
})
$('#searchForm').onsubmit = (e) => {
  e.preventDefault()
  const q = $('#searchInput').value.trim()
  if (q) location.hash = '#/search/' + encodeURIComponent(q)
}

// ===== tổng quan =====
function simpleList(list, empty) {
  if (!list.length) return `<p class="muted">${empty}</p>`
  return `<ul class="simple">${list
    .map((i) => `<li><span class="code">${i.meta.id}</span><a href="#/item/${i.meta.id}">${esc(i.meta.title)}</a></li>`)
    .join('')}</ul>`
}
function renderHome(main) {
  const tasks = itemsOf('task').filter((i) => i.meta.status !== 'dropped')
  const done = tasks.filter((i) => i.meta.status === 'done').length
  const decisions = itemsOf('decision')
  const openDec = decisions.filter((i) => !isClosed(i.meta.status))
  const qs = itemsOf('question')
  const answered = qs.filter((i) => isClosed(i.meta.status)).length
  const mine = itemsOf('task').filter((i) => i.meta.owner === S.user && !isClosed(i.meta.status))
  const doing = mine.filter((i) => i.meta.status === 'doing').concat(mine.filter((i) => i.meta.status !== 'doing'))
  const recent = []
  S.items.forEach((i) => (i.recent_comments || []).forEach((c) => recent.push({ ...c, id: i.meta.id, title: i.meta.title })))
  recent.sort((a, b) => b.time.localeCompare(a.time))
  const warnings = S.items.filter((i) => i.warnings?.length)
  const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0)

  main.innerHTML = `
    ${warnings.length ? `<div class="warn">Có ${warnings.length} mục bị sửa trùng cùng lúc, cần xem lại: ${warnings.map((i) => `<a href="#/item/${i.meta.id}">${i.meta.id}</a>`).join(', ')}</div>` : ''}
    <div class="stats">
      <a class="stat" href="#/list/task"><div class="num">${done}<span class="muted" style="font-size:18px"> / ${tasks.length}</span></div><div class="label">Đầu việc đã xong</div><div class="bar"><span style="width:${pct(done, tasks.length)}%"></span></div></a>
      <a class="stat" href="#/list/decision"><div class="num">${openDec.length}</div><div class="label">Việc cần chốt còn mở (trên ${decisions.length})</div><div class="bar"><span style="width:${pct(decisions.length - openDec.length, decisions.length)}%"></span></div></a>
      <a class="stat" href="#/list/question"><div class="num">${answered}<span class="muted" style="font-size:18px"> / ${qs.length}</span></div><div class="label">Câu hỏi khảo sát đã trả lời</div><div class="bar"><span style="width:${pct(answered, qs.length)}%"></span></div></a>
    </div>
    <div class="cols">
      <div>
        <div class="box"><h2>Việc của ${esc(S.user || 'tôi')}</h2>${simpleList(doing.slice(0, 8), S.user ? 'Không có việc đang mở.' : 'Chọn tên ở góc phải để xem việc của bạn.')}
          ${doing.length > 8 ? `<p class="small"><a href="#/list/task">Xem tất cả ${doing.length} việc →</a></p>` : ''}</div>
        <div class="box"><h2>Cần chốt</h2>${simpleList(openDec.slice(0, 8), 'Đã chốt hết.')}
          ${openDec.length > 8 ? `<p class="small"><a href="#/list/decision">Xem tất cả →</a></p>` : ''}</div>
      </div>
      <div class="box"><h2>Thảo luận gần đây</h2>
        ${recent.length ? recent.slice(0, 8).map((c) => `
          <div class="comment"><div class="comment-head"><b>${esc(c.author)}</b><span class="muted small">${esc(c.time.slice(0, 16))}</span></div>
          <a href="#/item/${c.id}">${esc(c.title)}</a>
          <div class="muted small">${esc(c.text.replace(/!\[[^\]]*\]\([^)]*\)/g, '[ảnh]').slice(0, 120))}</div></div>`).join('') : '<p class="muted">Chưa có thảo luận.</p>'}
      </div>
    </div>`
}

// ===== danh sách =====
function renderList(main, typeKey) {
  const t = typeOf(typeKey)
  if (!t) return (main.innerHTML = '<p>Không có loại mục này.</p>')
  const f = S.filters[typeKey] || (S.filters[typeKey] = { q: '', status: '', owner: '' })
  const hasOwner = t.fields.some((x) => x.key === 'owner')
  const all = itemsOf(typeKey)
  const scoreKeys = t.fields.filter((x) => x.kind === 'score').map((x) => x.key)
  const extra = typeKey === 'model' ? ['Kết quả', (i) => esc(i.meta.metric || '')]
    : typeKey === 'app' ? ['Điểm', (i) => scoreKeys.reduce((s, k) => s + (+i.meta[k] || 0), 0) || '']
    : ['task', 'fr', 'risk'].includes(typeKey) ? ['Checklist', (i) => (i.checklist.total ? `${i.checklist.done}/${i.checklist.total}` : '')]
    : null

  main.innerHTML = `
    <div class="page-head"><h1>${esc(t.label)}</h1><div class="right"><button class="btn primary" id="newBtn">+ Thêm</button></div></div>
    <div class="seg" id="seg"></div>
    <div class="filters">
      <input type="search" id="fq" placeholder="Lọc theo tên hoặc mã…" value="${esc(f.q)}">
      ${hasOwner ? `<select id="fowner"><option value="">Mọi người</option>${S.config.members.map((m) => `<option ${f.owner === m ? 'selected' : ''}>${esc(m)}</option>`).join('')}<option value="-" ${f.owner === '-' ? 'selected' : ''}>Chưa giao</option></select>` : ''}
    </div>
    <div id="rows"></div>`
  $('#newBtn').onclick = () => newItemDialog(typeKey)
  $('#fq').oninput = (e) => { f.q = e.target.value; draw() }
  if (hasOwner) $('#fowner').onchange = (e) => { f.owner = e.target.value; draw() }

  function draw() {
    const q = f.q.toLowerCase()
    const base = all.filter((i) => {
      if (q && !`${i.meta.id} ${i.meta.title}`.toLowerCase().includes(q)) return false
      if (f.owner === '-' ? i.meta.owner : f.owner && i.meta.owner !== f.owner) return false
      return true
    })
    $('#seg').innerHTML = [['', 'Tất cả', base.length], ...t.statuses.map((s) => [s.key, s.label, base.filter((i) => i.meta.status === s.key).length])]
      .map(([k, label, n]) => `<button data-s="${k}" class="${f.status === k ? 'on' : ''}">${esc(label)} <span class="muted">${n}</span></button>`).join('')
    $$('#seg button').forEach((b) => (b.onclick = () => { f.status = b.dataset.s; draw() }))
    let list = f.status ? base.filter((i) => i.meta.status === f.status) : base
    if (typeKey === 'app') list = [...list].sort((a, b) => extra[1](b) - extra[1](a))
    $('#rows').innerHTML = list.length ? `<table class="list"><thead><tr>
        <th>Mã</th><th>Tiêu đề</th><th>Trạng thái</th>${hasOwner ? '<th class="hide-sm">Phụ trách</th>' : ''}${extra ? `<th class="hide-sm">${extra[0]}</th>` : ''}<th class="hide-sm" title="Số bình luận">Thảo luận</th>
      </tr></thead><tbody>${list.map((i) => `<tr data-id="${i.meta.id}">
        <td class="code">${i.meta.id}</td>
        <td class="title">${esc(i.meta.title)}${i.warnings?.length ? ' <span title="Cần xem lại">⚠️</span>' : ''}</td>
        <td>${statusText(typeKey, i.meta.status)}</td>
        ${hasOwner ? `<td class="hide-sm">${esc(i.meta.owner || '')}</td>` : ''}
        ${extra ? `<td class="hide-sm">${extra[1](i)}</td>` : ''}
        <td class="hide-sm muted">${i.comment_count || ''}</td></tr>`).join('')}</tbody></table>`
      : '<p class="muted">Không có mục nào.</p>'
    $$('#rows tbody tr').forEach((tr) => (tr.onclick = () => (location.hash = '#/item/' + tr.dataset.id)))
  }
  draw()
}

function newItemDialog(typeKey) {
  const t = typeOf(typeKey)
  const hasOwner = t.fields.some((x) => x.key === 'owner')
  openModal(`<h2>Thêm ${esc(t.label.toLowerCase())}</h2>
    <div class="field"><label>Tiêu đề</label><input id="nTitle"></div>
    ${hasOwner ? `<div class="field"><label>Phụ trách</label><select id="nOwner"><option value=""></option>${S.config.members.map((m) => `<option ${m === S.user ? 'selected' : ''}>${esc(m)}</option>`).join('')}</select></div>` : ''}
    <div class="actions-row"><button class="btn" id="nCancel">Hủy</button><button class="btn primary" id="nOk">Tạo</button></div>`)
  $('#nCancel').onclick = closeModal
  const submit = async () => {
    const title = $('#nTitle').value.trim()
    if (!title) return toast('Nhập tiêu đề', true)
    const meta = $('#nOwner')?.value ? { owner: $('#nOwner').value } : {}
    try {
      const full = await api('/api/items', { method: 'POST', body: { type: typeKey, title, meta } })
      upsertSummary(full)
      closeModal()
      location.hash = '#/item/' + full.meta.id
    } catch (e) { toast(e.message, true) }
  }
  $('#nOk').onclick = submit
  $('#nTitle').onkeydown = (e) => e.key === 'Enter' && submit()
}

// ===== chi tiết =====
const MAIN_FIELDS = ['owner', 'priority']
function fieldInput(f, v) {
  const opts = (list) => '<option value=""></option>' + list.map((o) => `<option ${String(o) === String(v ?? '') ? 'selected' : ''}>${esc(o)}</option>`).join('')
  switch (f.kind) {
    case 'member': return `<select data-k="${f.key}">${opts(S.config.members)}</select>`
    case 'priority': return `<select data-k="${f.key}">${opts(S.config.priorities)}</select>`
    case 'module': return `<select data-k="${f.key}">${opts(S.config.modules)}</select>`
    case 'select': return `<select data-k="${f.key}">${opts(f.options)}</select>`
    case 'score': return `<select data-k="${f.key}">${opts([1, 2, 3, 4, 5])}</select>`
    case 'ch': return `<div class="checks" data-k="${f.key}" data-kind="checks">${S.config.research_questions.map((q) => `<label title="${esc(q.label)}"><input type="checkbox" value="${q.key}" ${asList(v).includes(q.key) ? 'checked' : ''}>${q.key}</label>`).join('')}</div>`
    case 'links':
    case 'list': return `<input data-k="${f.key}" data-kind="list" value="${esc(asList(v).join(', '))}" placeholder="${f.kind === 'links' ? 'VD: D-001, T-012' : 'cách nhau bằng dấu phẩy'}">`
    default: return `<input data-k="${f.key}" value="${esc(v || '')}">`
  }
}

async function renderItem(main, id) {
  let item = await api(`/api/items/${id}`)
  upsertSummary(item)
  const t = typeOf(item.meta.type) || { label: item.meta.type, statuses: [], fields: [] }
  const mainFields = t.fields.filter((f) => MAIN_FIELDS.includes(f.key))
  const moreFields = t.fields.filter((f) => !MAIN_FIELDS.includes(f.key))
  const backlinks = S.items.filter((i) => i.meta.id !== id && (asList(i.meta.links).includes(id) || (i.excerpt || '').includes(id)))
  const links = asList(item.meta.links).filter((x) => S.byId[x])

  main.innerHTML = `
    <a class="back" href="#/list/${item.meta.type}">← ${esc(t.label)}</a>
    ${item.warnings.length ? `<div class="warn" style="margin-top:12px">${item.warnings.map(esc).join('<br>')}. Chọn lại giá trị đúng rồi lưu là hết cảnh báo.</div>` : ''}
    <input class="title-input" id="titleInput" value="${esc(item.meta.title)}" title="Bấm để sửa tiêu đề">
    <div class="meta-row">
      <span class="code">${esc(id)}</span>
      <label>Trạng thái <select data-k="status">${t.statuses.map((s) => `<option value="${s.key}" ${s.key === item.meta.status ? 'selected' : ''}>${esc(s.label)}</option>`).join('')}</select></label>
      ${mainFields.map((f) => `<label>${esc(f.label)} ${fieldInput(f, item.meta[f.key])}</label>`).join('')}
    </div>
    ${moreFields.length ? `<details class="more"><summary>Thông tin thêm</summary>
      <div class="fields">${moreFields.map((f) => `<div><label>${esc(f.label)}</label>${fieldInput(f, item.meta[f.key])}</div>`).join('')}</div>
      ${links.length ? `<p class="small">Liên kết: ${links.map((x) => `<a class="ref" href="#/item/${x}" title="${esc(S.byId[x].meta.title)}">${x}</a>`).join(' ')}</p>` : ''}
    </details>` : ''}
    <div class="box">
      <div class="box-head"><h2>Nội dung</h2><div class="right"><button class="btn" id="editBtn">Sửa</button></div></div>
      <div id="contentView"></div>
    </div>
    <div class="box">
      <h2 id="commentsTitle"></h2>
      <div id="comments"></div>
      <div class="composer" id="composer">
        <textarea id="cText" placeholder="Viết ý kiến… (dán ảnh bằng Ctrl+V, Ctrl+Enter để gửi)"></textarea>
        <div class="actions-row"><span class="hint">Gửi với tên ${esc(S.user || '?')}</span><button class="btn primary" id="cSend">Gửi</button></div>
      </div>
    </div>
    ${backlinks.length ? `<div class="box"><h2>Được nhắc tới ở</h2>${simpleList(backlinks, '')}</div>` : ''}
    <p class="small" style="text-align:right"><span class="muted">pm/${esc(item.file)}</span> · <a href="#" id="delBtn" style="color:var(--red)">Xóa mục này</a></p>`

  const setItem = (full) => { item = full; upsertSummary(full) }
  const save = async (patch) => {
    try { setItem(await api(`/api/items/${id}`, { method: 'PUT', body: { ...patch, rev: item.rev } })); toast('Đã lưu') } catch (err) { onSaveError(err) }
  }

  // tiêu đề & trường
  $('#titleInput').onchange = (e) => e.target.value.trim() && save({ meta: { title: e.target.value.trim() } })
  $$('[data-k]', main).forEach((el) => {
    const k = el.dataset.k
    el.onchange = () => save({ meta: { [k]: el.dataset.kind === 'checks' ? $$('input:checked', el).map((c) => c.value) : el.dataset.kind === 'list' ? asList(el.value) : el.value.trim() } })
  })

  // nội dung
  function drawContent() {
    $('#contentView').innerHTML = renderMd(item.content)
    afterRender($('#contentView'))
    const boxes = $$('#contentView input[type=checkbox]')
    if (boxes.length !== (item.content.match(CHECK_RE) || []).length) return
    boxes.forEach((cb, idx) => {
      cb.disabled = false
      cb.onclick = async (e) => {
        e.preventDefault()
        let n = -1
        const content = item.content.replace(CHECK_RE, (m, a, v, b) => (++n === idx ? a + (v === ' ' ? 'x' : ' ') + b : m))
        try { setItem(await api(`/api/items/${id}`, { method: 'PUT', body: { content, rev: item.rev } })); drawContent() } catch (err) { onSaveError(err) }
      }
    })
  }
  drawContent()
  $('#editBtn').onclick = () => {
    const view = $('#contentView')
    view.innerHTML = `<div class="ed-tabs"><button class="on" data-m="edit">Soạn</button><button data-m="prev">Xem trước</button></div>
      <textarea id="contentTa" style="min-height:360px"></textarea><div id="contentPrev" class="hidden"></div>
      <div class="actions-row"><span class="hint">Dán ảnh bằng Ctrl+V · Ctrl+S để lưu</span><button class="btn" id="cancelEdit">Hủy</button><button class="btn primary" id="saveEdit">Lưu</button></div>`
    const ta = $('#contentTa')
    ta.value = item.content
    ta.oninput = () => (S.dirty = true)
    attachUpload(ta)
    $$('.ed-tabs button', view).forEach((b) => (b.onclick = () => {
      $$('.ed-tabs button', view).forEach((x) => x.classList.toggle('on', x === b))
      const prev = b.dataset.m === 'prev'
      ta.classList.toggle('hidden', prev)
      $('#contentPrev').classList.toggle('hidden', !prev)
      if (prev) { $('#contentPrev').innerHTML = renderMd(ta.value); afterRender($('#contentPrev')) }
    }))
    $('#editBtn').classList.add('hidden')
    const close = () => { S.dirty = false; $('#editBtn').classList.remove('hidden'); drawContent() }
    $('#cancelEdit').onclick = () => (!S.dirty || confirm('Bỏ các thay đổi?')) && close()
    const doSave = async () => {
      try { setItem(await api(`/api/items/${id}`, { method: 'PUT', body: { content: ta.value, rev: item.rev } })); toast('Đã lưu'); close() } catch (err) { onSaveError(err) }
    }
    $('#saveEdit').onclick = doSave
    ta.onkeydown = (e) => { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); doSave() } }
    ta.focus()
  }

  // thảo luận
  function drawComments() {
    $('#commentsTitle').textContent = item.comments.length ? `Thảo luận (${item.comments.length})` : 'Thảo luận'
    $('#comments').innerHTML = item.comments.map((c) => `
      <div class="comment" data-i="${c.index}">
        <div class="comment-head"><b>${esc(c.author)}</b><span class="muted small">${esc(c.time.slice(0, 16))}</span>
          ${c.author === S.user ? '<span class="right"><button data-act="edit">Sửa</button><button data-act="del">Xóa</button></span>' : ''}</div>
        <div class="cbody">${renderMd(c.text)}</div>
      </div>`).join('')
    afterRender($('#comments'))
    $$('#comments .comment').forEach((el) => {
      const c = item.comments[+el.dataset.i]
      el.querySelector('[data-act=del]')?.addEventListener('click', async () => {
        if (!confirm('Xóa bình luận này?')) return
        try { setItem(await api(`/api/items/${id}/comments/${c.index}`, { method: 'DELETE', body: { time: c.time } })); drawComments() } catch (err) { toast(err.message, true) }
      })
      el.querySelector('[data-act=edit]')?.addEventListener('click', () => {
        const body = el.querySelector('.cbody')
        body.innerHTML = `<textarea>${esc(c.text)}</textarea><div class="actions-row"><button class="btn" data-x="cancel">Hủy</button><button class="btn primary" data-x="save">Lưu</button></div>`
        const ta = body.querySelector('textarea')
        attachUpload(ta)
        S.dirty = true
        body.querySelector('[data-x=cancel]').onclick = () => { S.dirty = false; drawComments() }
        body.querySelector('[data-x=save]').onclick = async () => {
          try { setItem(await api(`/api/items/${id}/comments/${c.index}`, { method: 'PUT', body: { text: ta.value, time: c.time } })); S.dirty = false; drawComments() } catch (err) { toast(err.message, true) }
        }
      })
    })
  }
  drawComments()
  const cText = $('#cText')
  attachUpload(cText, $('#composer'))
  cText.oninput = () => (S.dirty = !!cText.value.trim())
  const send = async () => {
    if (!cText.value.trim()) return
    if (!S.user) return askUser()
    try {
      setItem(await api(`/api/items/${id}/comments`, { method: 'POST', body: { text: cText.value } }))
      cText.value = ''
      S.dirty = false
      drawComments()
    } catch (err) { toast(err.message, true) }
  }
  $('#cSend').onclick = send
  cText.onkeydown = (e) => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') send() }

  $('#delBtn').onclick = async (e) => {
    e.preventDefault()
    if (!confirm(`Xóa hẳn ${id} và toàn bộ thảo luận của nó?`)) return
    try {
      await api(`/api/items/${id}`, { method: 'DELETE' })
      await loadItems()
      location.hash = `#/list/${item.meta.type}`
    } catch (err) { toast(err.message, true) }
  }

  function onSaveError(err) {
    if (err.status === 409) {
      toast('Mục vừa được thay đổi ở nơi khác — đã tải lại bản mới nhất.', true)
      S.dirty = false
      renderItem(main, id)
    } else toast(err.message, true)
  }
}

// ===== truy vết & tìm kiếm =====
function renderTrace(main) {
  main.innerHTML = `<div class="page-head"><h1>Truy vết câu hỏi nghiên cứu</h1></div>
    <p class="muted">Các mục được gắn với từng câu hỏi nghiên cứu (trường "Câu hỏi NC" trong phần Thông tin thêm).</p>
    ${S.config.research_questions.map((q) => {
      const rel = S.items.filter((i) => asList(i.meta.ch).includes(q.key) && i.meta.status !== 'dropped')
      const tasks = rel.filter((i) => i.meta.type === 'task')
      return `<div class="box"><h2>${q.key}. ${esc(q.label)}</h2>
        <p class="small muted">${tasks.filter((i) => i.meta.status === 'done').length}/${tasks.length} đầu việc đã xong · ${rel.length} mục liên quan</p>
        <ul class="simple">${rel.map((i) => `<li><span class="code">${i.meta.id}</span><a href="#/item/${i.meta.id}">${esc(i.meta.title)}</a><span style="margin-left:auto">${statusText(i.meta.type, i.meta.status)}</span></li>`).join('')}</ul></div>`
    }).join('')}`
}
function renderSearch(main, q) {
  const ql = q.toLowerCase()
  const res = S.items.filter((i) => `${i.meta.id} ${i.meta.title} ${i.excerpt} ${(i.recent_comments || []).map((c) => c.text).join(' ')}`.toLowerCase().includes(ql))
  main.innerHTML = `<div class="page-head"><h1>Kết quả cho "${esc(q)}"</h1><span class="muted">${res.length} mục</span></div>
    <div class="box">${simpleList(res, 'Không tìm thấy.')}</div>`
}

// ===== người dùng =====
function askUser() {
  openModal(`<h2>Bạn là ai?</h2>
    <p class="muted small">Tên dùng làm tác giả bình luận và commit, chỉ lưu trên máy này.</p>
    <div class="field"><select id="uSel">${S.config.members.map((m) => `<option ${m === S.user ? 'selected' : ''}>${esc(m)}</option>`).join('')}<option value="">Tên khác…</option></select></div>
    <div class="field hidden" id="uOtherWrap"><input id="uOther" placeholder="Nhập tên"></div>
    <div class="actions-row"><button class="btn primary" id="uOk">Lưu</button></div>`)
  $('#uSel').onchange = () => $('#uOtherWrap').classList.toggle('hidden', $('#uSel').value !== '')
  $('#uOk').onclick = async () => {
    const name = $('#uSel').value || $('#uOther').value.trim()
    if (!name) return
    await api('/api/user', { method: 'POST', body: { name } })
    S.user = name
    $('#userBtn').textContent = name
    closeModal()
    route()
  }
}
$('#userBtn').onclick = askUser

// ===== git =====
async function refreshGit(fetch = false) {
  try {
    const g = await api('/api/git/status' + (fetch ? '?fetch=1' : ''))
    const up = (g.local_changes || 0) + (g.ahead || 0)
    $('#syncInfo').textContent = [up ? `↑${up}` : '', g.behind ? `↓${g.behind}` : ''].filter(Boolean).join(' ')
    $('#syncBtn').title = [up ? `${up} thay đổi chưa đẩy lên` : '', g.behind ? `${g.behind} cập nhật mới từ người khác` : ''].filter(Boolean).join(', ') || 'Đã đồng bộ'
    if (fetch && g.behind && !S.notified) {
      S.notified = true
      toast(`Có ${g.behind} cập nhật mới — bấm Đồng bộ để lấy về`)
    }
  } catch { /* bỏ qua */ }
}
$('#syncBtn').onclick = async () => {
  if (S.dirty && !confirm('Nội dung đang soạn chưa lưu sẽ không được đồng bộ. Tiếp tục?')) return
  const btn = $('#syncBtn')
  btn.disabled = true
  try {
    const r = await api('/api/git/sync', { method: 'POST', body: {} })
    S.notified = false
    if (!r.ok) {
      openModal(`<h2>Đồng bộ chưa xong</h2><p>${esc(r.error)}</p><pre>${esc(r.log.join('\n\n'))}</pre><div class="actions-row"><button class="btn" onclick="closeModal()">Đóng</button></div>`, true)
    } else if (r.renamed?.length) {
      openModal(`<h2>Đồng bộ xong</h2><p>Người kia cũng vừa tạo mục cùng mã, nên mục của bạn được đổi mã: ${r.renamed.map(([a, b]) => `${esc(a)} → <a href="#/item/${esc(b)}" onclick="closeModal()">${esc(b)}</a>`).join(', ')}.</p><div class="actions-row"><button class="btn primary" onclick="closeModal()">OK</button></div>`)
    } else toast('Đã đồng bộ')
    await loadItems()
    await refreshGit()
    S.dirty = false
    route()
  } catch (e) {
    toast(e.message, true)
  } finally {
    btn.disabled = false
  }
}

// ===== khởi động =====
;(async function init() {
  if (window.mermaid) mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'strict' })
  const meta = await api('/api/meta')
  S.config = meta.config
  S.user = meta.user
  $('#userBtn').textContent = S.user || 'Chọn tên'
  await loadItems()
  await route()
  if (!S.user) askUser()
  refreshGit(true)
  setInterval(() => refreshGit(false), 30_000)
  setInterval(() => refreshGit(true), 5 * 60_000)
  window.addEventListener('focus', () => refreshGit(false))
})().catch((e) => {
  $('#main').innerHTML = `<div class="warn">Không kết nối được server: ${esc(e.message)}. Chạy <code>python pm/server.py</code> rồi tải lại trang.</div>`
})
