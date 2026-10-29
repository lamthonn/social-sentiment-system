/* Quản lý đề tài - đọc/ghi pm/QUAN_LY_DE_TAI.md qua pm/server.py */
'use strict'

let doc = null // { overview, tasks, models, warnings, rev, options }
let taskFilter = ''
const $ = (s, r = document) => r.querySelector(s)
const $$ = (s, r = document) => [...r.querySelectorAll(s)]
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
const TASK_COLOR = { 'Chưa làm': 'gray', 'Đang làm': 'blue', 'Xong': 'green', 'Tạm dừng': 'amber' }
const MODEL_COLOR = { 'Ứng viên': 'gray', 'Đang thử': 'blue', 'Đã chọn': 'green', 'Loại': 'red' }
const TASK_ORDER = ['Đang làm', 'Chưa làm', 'Tạm dừng', 'Xong']

function toast(msg, err = false) {
  const t = $('#toast')
  t.textContent = msg
  t.className = 'toast' + (err ? ' error' : '')
  clearTimeout(toast.h)
  toast.h = setTimeout(() => t.classList.add('hidden'), err ? 5000 : 1800)
}
function md(src) {
  if (!src || !src.trim()) return '<p class="muted">Chưa có nội dung.</p>'
  const html = window.marked ? marked.parse(src, { gfm: true, breaks: true }) : `<pre>${esc(src)}</pre>`
  return `<div class="md">${window.DOMPurify ? DOMPurify.sanitize(html) : html}</div>`
}
function openModal(html) {
  $('#modalBox').innerHTML = html
  $('#modal').classList.remove('hidden')
  $('#modalBox input, #modalBox textarea')?.focus()
}
function closeModal() {
  $('#modal').classList.add('hidden')
}
$('#modal').onclick = (e) => e.target.id === 'modal' && closeModal()
document.addEventListener('keydown', (e) => e.key === 'Escape' && closeModal())

// ===== API =====
async function api(path, opts = {}) {
  const res = await fetch(path, opts)
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(data.error || `Lỗi ${res.status}`), { status: res.status, data })
  return data
}
async function save(msg = 'Đã lưu') {
  try {
    doc = await api('/api/doc', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ overview: doc.overview, tasks: doc.tasks, models: doc.models, rev: doc.rev }),
    })
    toast(msg)
  } catch (e) {
    if (e.status === 409 && e.data.current) {
      doc = e.data.current
      toast(e.message, true)
    } else toast(e.message, true)
  }
  render()
}

// Dán ảnh (Ctrl+V) / kéo thả file vào ô soạn thảo -> lưu vào pm/assets
function attachUpload(ta) {
  const upload = async (files) => {
    for (const f of files) {
      try {
        const r = await api('/api/upload', { method: 'POST', headers: { 'Content-Type': f.type || 'application/octet-stream', 'X-Filename': encodeURIComponent(f.name || '') }, body: f })
        const text = r.is_image ? `![](${r.path})` : `[${f.name}](${r.path})`
        const p = ta.selectionStart
        ta.value = ta.value.slice(0, p) + text + ta.value.slice(ta.selectionEnd)
        ta.selectionStart = ta.selectionEnd = p + text.length
      } catch (e) { toast('Tải file lỗi: ' + e.message, true) }
    }
  }
  ta.addEventListener('paste', (e) => {
    const files = [...(e.clipboardData?.items || [])].filter((i) => i.kind === 'file').map((i) => i.getAsFile())
    if (files.length) { e.preventDefault(); upload(files) }
  })
  ta.addEventListener('dragover', (e) => e.preventDefault())
  ta.addEventListener('drop', (e) => {
    if (e.dataTransfer.files.length) { e.preventDefault(); upload([...e.dataTransfer.files]) }
  })
}

// ===== điều hướng =====
const tab = () => (['overview', 'tasks', 'models'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'overview')
window.addEventListener('hashchange', render)
function render() {
  $$('.tabs a').forEach((a) => a.classList.toggle('active', a.dataset.tab === tab()))
  const main = $('#main')
  const warn = doc.warnings.length ? `<div class="warn">${doc.warnings.map(esc).join('<br>')}</div>` : ''
  main.innerHTML = warn + '<div id="view"></div>'
  ;({ overview: renderOverview, tasks: renderTasks, models: renderModels })[tab()]($('#view'))
}

// ===== 1. Tổng quan =====
function renderOverview(view) {
  view.innerHTML = `
    <div class="toc">${doc.overview.map((s, i) => `<a href="#overview" data-go="${i}">${esc(s.title)}</a>`).join('')}</div>
    ${doc.overview.map((s, i) => `<div class="card" id="ov-${i}">
      <div class="card-head"><h2>${esc(s.title)}</h2><button class="link right" data-edit="${i}">Sửa</button></div>
      ${md(s.body)}</div>`).join('')}
    <button class="btn" id="addSec">+ Thêm mục</button>`
  $$('[data-go]', view).forEach((a) => (a.onclick = (e) => { e.preventDefault(); $(`#ov-${a.dataset.go}`).scrollIntoView({ behavior: 'smooth' }) }))
  $$('[data-edit]', view).forEach((b) => (b.onclick = () => editSection(+b.dataset.edit)))
  $('#addSec').onclick = () => {
    doc.overview.push({ title: 'Mục mới', body: '' })
    editSection(doc.overview.length - 1, true)
  }
}
function editSection(i, isNew = false) {
  const s = doc.overview[i]
  const card = $(`#ov-${i}`) || $('#view').appendChild(Object.assign(document.createElement('div'), { className: 'card', id: `ov-${i}` }))
  card.innerHTML = `<input id="secTitle" value="${esc(s.title)}" style="width:100%;font-weight:600;margin-bottom:10px">
    <textarea id="secBody" style="min-height:280px">${esc(s.body)}</textarea>
    <div class="actions"><button class="btn danger left" id="secDel">Xóa mục</button><span class="muted small">Markdown · dán ảnh bằng Ctrl+V</span>
      <button class="btn" id="secCancel">Hủy</button><button class="btn primary" id="secSave">Lưu</button></div>`
  attachUpload($('#secBody'))
  card.scrollIntoView({ block: 'start' })
  $('#secCancel').onclick = () => { if (isNew) doc.overview.pop(); render() }
  $('#secSave').onclick = () => { s.title = $('#secTitle').value.trim() || 'Không tên'; s.body = $('#secBody').value; save() }
  $('#secDel').onclick = () => { if (confirm(`Xóa mục "${s.title}"?`)) { doc.overview.splice(i, 1); save('Đã xóa') } }
}

// ===== 2. Việc cần làm =====
function renderTasks(view) {
  const { members, task_statuses: statuses } = doc.options
  const count = (s) => doc.tasks.filter((t) => t.status === s).length
  const list = doc.tasks
    .filter((t) => !taskFilter || t.status === taskFilter)
    .sort((a, b) => TASK_ORDER.indexOf(a.status) - TASK_ORDER.indexOf(b.status))
  view.innerHTML = `
    <div class="card add-box"><div class="row">
      <input id="newTitle" class="grow" placeholder="Thêm việc mới…">
      <select id="newOwner"><option value="">Người làm</option>${members.map((m) => `<option>${esc(m)}</option>`).join('')}</select>
      <button class="btn primary" id="addTask">Thêm</button>
    </div></div>
    <div class="chips">
      <button data-f="" class="${taskFilter ? '' : 'on'}">Tất cả ${doc.tasks.length}</button>
      ${statuses.map((s) => `<button data-f="${esc(s)}" class="s-${TASK_COLOR[s] || 'gray'} ${taskFilter === s ? 'on' : ''}"><i></i>${esc(s)} ${count(s)}</button>`).join('')}
    </div>
    <div class="task-grid">${list.map((t) => `
      <div class="task s-${TASK_COLOR[t.status] || 'gray'}">
        <div class="t-title" data-open="${esc(t.id)}">${esc(t.title)}</div>
        ${t.note ? `<div class="t-note">${esc(t.note)}</div>` : ''}
        <div class="t-foot"><span>${esc(t.id)}</span>${t.owner ? `<span>· ${esc(t.owner)}</span>` : ''}
          <select data-status="${esc(t.id)}">${statuses.map((s) => `<option ${s === t.status ? 'selected' : ''}>${esc(s)}</option>`).join('')}</select></div>
      </div>`).join('') || '<p class="muted">Không có việc nào.</p>'}
    </div>`
  const add = () => {
    const title = $('#newTitle').value.trim()
    if (!title) return
    doc.tasks.push({ id: '', title, status: statuses[0], owner: $('#newOwner').value, note: '' })
    save('Đã thêm việc')
  }
  $('#addTask').onclick = add
  $('#newTitle').onkeydown = (e) => e.key === 'Enter' && add()
  $$('.chips button', view).forEach((b) => (b.onclick = () => { taskFilter = b.dataset.f; render() }))
  $$('[data-status]', view).forEach((sel) => (sel.onchange = () => {
    doc.tasks.find((t) => t.id === sel.dataset.status).status = sel.value
    save(`Đã chuyển sang "${sel.value}"`)
  }))
  $$('[data-open]', view).forEach((el) => (el.onclick = () => editTask(doc.tasks.find((t) => t.id === el.dataset.open))))
}
function editTask(t) {
  const { members, task_statuses: statuses } = doc.options
  openModal(`<h2>${esc(t.id)}</h2>
    <label>Việc</label><input id="tTitle" value="${esc(t.title)}">
    <div class="row"><div class="grow"><label>Trạng thái</label><select id="tStatus">${statuses.map((s) => `<option ${s === t.status ? 'selected' : ''}>${esc(s)}</option>`).join('')}</select></div>
      <div class="grow"><label>Người làm</label><select id="tOwner"><option value=""></option>${[...new Set([...members, t.owner].filter(Boolean))].map((m) => `<option ${m === t.owner ? 'selected' : ''}>${esc(m)}</option>`).join('')}</select></div></div>
    <label>Ghi chú</label><textarea id="tNote">${esc(t.note)}</textarea>
    <div class="actions"><button class="btn danger left" id="tDel">Xóa</button><button class="btn" id="tCancel">Hủy</button><button class="btn primary" id="tSave">Lưu</button></div>`)
  $('#tCancel').onclick = closeModal
  $('#tSave').onclick = () => {
    Object.assign(t, { title: $('#tTitle').value.trim() || t.title, status: $('#tStatus').value, owner: $('#tOwner').value, note: $('#tNote').value.replace(/\s*\n\s*/g, ' ').trim() })
    closeModal()
    save()
  }
  $('#tDel').onclick = () => {
    if (!confirm(`Xóa việc "${t.title}"?`)) return
    doc.tasks = doc.tasks.filter((x) => x !== t)
    closeModal()
    save('Đã xóa')
  }
}

// ===== 3. Mô hình =====
const NUM_FIELDS = ['Accuracy', 'Precision', 'Recall', 'Macro-F1']
function renderModels(view) {
  const f = (m, k) => esc(m.fields[k] || '')
  view.innerHTML = `
    <table class="cmp"><thead><tr><th>Mã</th><th>Mô hình</th><th class="hide-sm">Bài toán</th><th>Trạng thái</th><th class="hide-sm">Dataset</th><th>Accuracy</th><th>Macro-F1</th></tr></thead>
    <tbody>${doc.models.map((m) => `<tr><td class="muted">${esc(m.id)}</td><td><a href="#models" data-go="${esc(m.id)}">${esc(m.name)}</a></td><td class="hide-sm">${f(m, 'Bài toán')}</td>
      <td><span class="badge s-${MODEL_COLOR[m.fields['Trạng thái']] || 'gray'}">${f(m, 'Trạng thái') || '—'}</span></td><td class="hide-sm">${f(m, 'Dataset')}</td>
      <td class="num">${f(m, 'Accuracy')}</td><td class="num">${f(m, 'Macro-F1')}</td></tr>`).join('')}</tbody></table>
    ${doc.models.map((m, i) => `<div class="card model s-${MODEL_COLOR[m.fields['Trạng thái']] || 'gray'}" id="m-${esc(m.id)}">
      <div class="card-head"><h2>${esc(m.name)}</h2><span class="badge">${f(m, 'Trạng thái') || '—'}</span><button class="link right" data-edit="${i}">Sửa / nhập kết quả</button></div>
      ${f(m, 'Mô tả') ? `<p class="muted" style="margin:0 0 10px">${f(m, 'Mô tả')}</p>` : ''}
      <div class="kv">${['Bài toán', 'Nhóm', 'Dataset', ...NUM_FIELDS].map((k) => `<div><span>${k}</span>${f(m, k) || '<span class="muted">—</span>'}</div>`).join('')}</div>
      <div class="section-label">Kết quả & nhận xét</div>${md(m.notes)}
    </div>`).join('')}
    <button class="btn" id="addModel">+ Thêm mô hình</button>`
  $$('[data-go]', view).forEach((a) => (a.onclick = (e) => { e.preventDefault(); $(`#m-${a.dataset.go}`).scrollIntoView({ behavior: 'smooth' }) }))
  $$('[data-edit]', view).forEach((b) => (b.onclick = () => editModel(+b.dataset.edit)))
  $('#addModel').onclick = () => {
    doc.models.push({ id: '', name: 'Mô hình mới', fields: { 'Trạng thái': doc.options.model_statuses[0] }, notes: '' })
    editModel(doc.models.length - 1, true)
  }
}
function editModel(i, isNew = false) {
  const m = doc.models[i]
  const input = (k) => k === 'Trạng thái'
    ? `<select data-k="${k}">${doc.options.model_statuses.map((s) => `<option ${s === m.fields[k] ? 'selected' : ''}>${esc(s)}</option>`).join('')}</select>`
    : `<input data-k="${k}" value="${esc(m.fields[k] || '')}" ${NUM_FIELDS.includes(k) ? 'placeholder="VD: 0.871"' : ''}>`
  const card = $(`#m-${m.id}`) || $('#view').appendChild(Object.assign(document.createElement('div'), { className: 'card' }))
  card.innerHTML = `<input id="mName" value="${esc(m.name)}" style="width:100%;font-weight:600;margin-bottom:12px">
    <div class="kv">${doc.options.model_fields.filter((k) => k !== 'Mô tả').map((k) => `<div><label>${k}</label>${input(k)}</div>`).join('')}</div>
    <label class="section-label">Mô tả ngắn</label><input data-k="Mô tả" value="${esc(m.fields['Mô tả'] || '')}" style="width:100%">
    <div class="section-label">Kết quả & nhận xét (bảng số liệu, confusion matrix, ảnh… — dán ảnh bằng Ctrl+V)</div>
    <textarea id="mNotes" style="min-height:220px">${esc(m.notes)}</textarea>
    <div class="actions"><button class="btn danger left" id="mDel">Xóa mô hình</button><button class="btn" id="mCancel">Hủy</button><button class="btn primary" id="mSave">Lưu</button></div>`
  attachUpload($('#mNotes'))
  card.scrollIntoView({ block: 'start' })
  $('#mCancel').onclick = () => { if (isNew) doc.models.pop(); render() }
  $('#mSave').onclick = () => {
    m.name = $('#mName').value.trim() || 'Không tên'
    $$('[data-k]', card).forEach((el) => (m.fields[el.dataset.k] = el.value.trim()))
    m.notes = $('#mNotes').value
    save()
  }
  $('#mDel').onclick = () => { if (confirm(`Xóa mô hình "${m.name}"?`)) { doc.models.splice(i, 1); save('Đã xóa') } }
}

// ===== đồng bộ git =====
async function refreshGit(fetch = false) {
  try {
    const g = await api('/api/git/status' + (fetch ? '?fetch=1' : ''))
    const up = g.local_changes + g.ahead
    $('#syncInfo').textContent = [up ? `↑${up}` : '', g.behind ? `↓${g.behind}` : ''].filter(Boolean).join(' ')
  } catch { /* bỏ qua */ }
}
$('#syncBtn').onclick = async () => {
  const btn = $('#syncBtn')
  btn.disabled = true
  try {
    const r = await api('/api/git/sync', { method: 'POST' })
    if (r.ok) toast('Đã đồng bộ')
    else openModal(`<h2>Chưa đồng bộ được</h2><p>${esc(r.error)}</p><pre>${esc(r.log.join('\n\n'))}</pre><div class="actions"><button class="btn" onclick="closeModal()">Đóng</button></div>`)
    doc = await api('/api/doc')
    render()
    refreshGit()
  } catch (e) { toast(e.message, true) } finally { btn.disabled = false }
}

;(async () => {
  doc = await api('/api/doc')
  render()
  refreshGit(true)
  setInterval(() => refreshGit(false), 30_000)
  setInterval(() => refreshGit(true), 5 * 60_000)
})().catch((e) => {
  $('#main').innerHTML = `<div class="warn">Không kết nối được server (${esc(e.message)}). Chạy <code>python pm/server.py</code> rồi tải lại trang.</div>`
})
