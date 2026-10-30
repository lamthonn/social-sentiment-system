// Giao diện quản lý dự án — đọc PROJECT.md qua tools/server.js, mọi số liệu được tính tại đây (không lưu trong file).
'use strict'

// ===== Lược đồ các loại đối tượng (khớp quy ước ở đầu PROJECT.md) =====
const COMMON = ['Chưa bắt đầu', 'Đang làm', 'Bị chặn', 'Hoàn thành', 'Hủy']
const PEOPLE = ['Nam', 'Lâm']
const TYPES = {
  TQ: { name: 'Tổng quan', fields: [] },
  GD: { name: 'Giai đoạn', fields: [['Kết quả dự kiến'], ['Người thực hiện (theo thuyết minh)']] },
  NV: { name: 'Nghiệp vụ', fields: [] },
  T: {
    name: 'Đầu việc', statuses: COMMON, cancel: 'Hủy', logKinds: ['Kết quả', 'Vướng mắc', 'Đề xuất điều chỉnh'],
    fields: [['Mô tả'], ['Người phụ trách', 'person'], ['Giai đoạn', 'phase'], ['Trạng thái', 'status'], ['Liên kết']],
  },
  PL: { name: 'Bước pipeline', statuses: COMMON, fields: [['Đầu vào'], ['Đầu ra'], ['Công cụ/thuật toán'], ['Model đang chọn', 'model'], ['An ninh an toàn'], ['Trạng thái', 'status']] },
  DS: {
    name: 'Nguồn dữ liệu', statuses: ['Chưa thu thập', 'Đang thu thập', 'Đã thu thập', 'Dừng', 'Hủy'], cancel: 'Hủy',
    fields: [['Nền tảng'], ['Phạm vi'], ['Cách lấy'], ['Tần suất'], ['Ghi chú pháp lý'], ['Trạng thái', 'status'], ['Số bản ghi'], ['Khoảng thời gian dữ liệu'], ['Nơi lưu']],
  },
  CL: { name: 'Bước làm sạch', statuses: COMMON, cancel: 'Hủy', fields: [['Thuật toán/thư viện'], ['Tham số'], ['Áp dụng cho nguồn'], ['Số bản ghi trước'], ['Số bản ghi sau'], ['Trạng thái', 'status']] },
  ST: { name: 'Lưu trữ', statuses: COMMON, cancel: 'Hủy', fields: [['Hệ lưu trữ'], ['Định dạng'], ['Schema'], ['Vị trí'], ['Thời gian giữ'], ['Sao lưu'], ['Kiểm soát truy cập'], ['Ẩn danh'], ['Trạng thái', 'status']] },
  M: {
    name: 'Model', statuses: ['Đề xuất', 'Đang thử', 'Đã đánh giá', 'Loại', 'Được chọn', 'Hủy'], cancel: 'Hủy',
    fields: [['Loại', 'select', ['Baseline cổ điển', 'Deep learning', 'Transformer', 'LLM']], ['Bài toán phù hợp'], ['Lý do chọn'], ['Trạng thái', 'status']],
  },
  R: {
    name: 'Lần huấn luyện', statuses: COMMON, cancel: 'Hủy',
    fields: [['Model', 'model'], ['Dữ liệu'], ['Phiên bản dữ liệu'], ['Tham số'], ['Accuracy'], ['F1-macro'], ['Precision'], ['Recall'], ['Theo lớp'], ['Ngày chạy'], ['Người chạy', 'person'], ['Đường dẫn kết quả'], ['Nhận xét'], ['Trạng thái', 'status']],
  },
  BT: { name: 'Bài toán', statuses: COMMON, fields: [['Đầu vào'], ['Đầu ra'], ['Tập nhãn'], ['Model được chọn', 'model'], ['Metric mục tiêu'], ['Trạng thái', 'status']] },
  QD: { name: 'Quyết định', fields: [['Ngày'], ['Người chốt', 'person'], ['Lý do']] },
}
// Màu trạng thái — một bảng duy nhất cho mọi màn hình
const COLOR = {
  'Chưa bắt đầu': 'gray', 'Chưa thu thập': 'gray', 'Đề xuất': 'gray',
  'Đang làm': 'blue', 'Đang thu thập': 'blue', 'Đang thử': 'blue',
  'Bị chặn': 'red', 'Dừng': 'amber', 'Đã đánh giá': 'violet',
  'Hoàn thành': 'green', 'Đã thu thập': 'green', 'Được chọn': 'green',
  'Loại': 'muted', 'Hủy': 'muted',
}
// Bước pipeline -> loại đối tượng liên quan
const STEP_TYPES = { 'PL-01': ['DS'], 'PL-02': ['CL'], 'PL-03': [], 'PL-04': ['ST'], 'PL-05': ['M', 'R'], 'PL-06': ['R'], 'PL-07': ['BT'], 'PL-08': [] }
const ID_RE = /\b([A-Z]{1,3}-\d{2,})\b/g

const S = { doc: null, byId: {}, user: '', drawer: null, editing: false, git: null, taskView: 'kanban', f: { person: '', phase: '', status: '', q: '' }, runSort: 'F1-macro', step: 'PL-01', actPerson: '' }
const $ = (s, r = document) => r.querySelector(s)
const $$ = (s, r = document) => [...r.querySelectorAll(s)]
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
const blocksOf = (p) => S.doc.blocks.filter((b) => b.prefix === p)
const attr = (b, k) => (b && b.attrs[k]) || ''
const statusOf = (b) => attr(b, 'Trạng thái')
const color = (st) => COLOR[st] || 'gray'
const badge = (st) => (st ? `<span class="st c-${color(st)}">${esc(st)}</span>` : '<span class="muted small">—</span>')
const idsIn = (s) => [...String(s || '').matchAll(ID_RE)].map((m) => m[1])
const label = (id) => (S.byId[id] ? `${id} ${S.byId[id].title}` : id)
const num = (v) => { const n = parseFloat(String(v || '').replace(',', '.').replace('%', '')); return Number.isFinite(n) ? n : null }
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }

function toast(msg, err = false) {
  const t = document.createElement('div')
  t.className = 'toast' + (err ? ' err' : '')
  t.textContent = msg
  document.body.appendChild(t)
  setTimeout(() => t.remove(), err ? 6000 : 2200)
}
function md(src) {
  if (!src || !String(src).trim()) return ''
  const html = window.marked ? marked.parse(src, { gfm: true }) : `<pre>${esc(src)}</pre>`
  return `<div class="md">${window.DOMPurify ? DOMPurify.sanitize(html) : html}</div>`
}
async function api(path, body) {
  const res = await fetch(path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(data.error || `Lỗi ${res.status}`), { status: res.status, data })
  return data
}
function setDoc(doc) {
  S.doc = doc
  S.byId = Object.fromEntries(doc.blocks.map((b) => [b.id, b]))
}

// Gửi một thao tác; khi xung đột (409) server trả bản mới -> cập nhật giao diện và báo
async function op(body, okMsg) {
  try {
    const r = await api('/api/op', body)
    setDoc(r.doc)
    if (okMsg) toast(okMsg)
    refresh()
    refreshGit()
    return r
  } catch (e) {
    if (e.data && e.data.doc) { setDoc(e.data.doc); refresh() }
    toast(e.message, true)
    throw e
  }
}
const needUser = () => {
  if (S.user) return false
  toast('Chọn bạn là Nam hay Lâm ở góc phải trước đã.', true)
  $('#userSel').focus()
  return true
}

// ===== Điều hướng =====
const VIEWS = { 'tong-quan': viewOverview, 'nghiep-vu': viewBusiness, 'dau-viec': viewTasks, pipeline: viewPipeline, model: viewModels }
const current = () => (VIEWS[location.hash.slice(1)] ? location.hash.slice(1) : 'tong-quan')
window.addEventListener('hashchange', () => { closeDrawer(); refresh() })
function refresh() {
  $$('#nav a').forEach((a) => a.classList.toggle('on', a.getAttribute('href') === '#' + current()))
  const main = $('#main')
  const banner = S.doc.conflict ? '<div class="banner">PROJECT.md đang có xung đột git chưa giải quyết. <button class="btn sm" id="openConflict">Xử lý xung đột</button></div>' : ''
  main.innerHTML = banner + '<div id="view"></div>'
  if ($('#openConflict')) $('#openConflict').onclick = openConflict
  VIEWS[current()]($('#view'))
  if (S.drawer) renderDrawer()
}

// ===== 1. Tổng quan =====
function viewOverview(v) {
  const tasks = blocksOf('T')
  const active = tasks.filter((t) => statusOf(t) !== 'Hủy')
  const done = active.filter((t) => statusOf(t) === 'Hoàn thành').length
  const blocked = active.filter((t) => statusOf(t) === 'Bị chặn')
  const doing = active.filter((t) => statusOf(t) === 'Đang làm').length
  const unassigned = active.filter((t) => !attr(t, 'Người phụ trách') && statusOf(t) !== 'Hoàn thành').length
  const pct = active.length ? Math.round((100 * done) / active.length) : 0

  const phases = blocksOf('GD').map((g) => {
    const list = tasks.filter((t) => attr(t, 'Giai đoạn') === g.id)
    const counts = COMMON.map((s) => [s, list.filter((t) => statusOf(t) === s).length]).filter(([, n]) => n)
    const total = list.length || 1
    return `<div class="phase" data-open="${g.id}" style="cursor:pointer" title="${esc(attr(g, 'Kết quả dự kiến'))}"><div><span class="id">${g.id}</span> ${esc(g.title)}</div>
      <div class="stack">${counts.map(([s, n]) => `<span class="c-${color(s)}" style="width:${(100 * n) / total}%" title="${s}: ${n}"></span>`).join('')}</div>
      <div class="small muted">${list.length ? counts.map(([s, n]) => `${n} ${s.toLowerCase()}`).join(' · ') : 'chưa có đầu việc'}</div></div>`
  }).join('')

  const logs = []
  S.doc.blocks.forEach((b) => b.logs.forEach((l) => logs.push({ ...l, id: b.id, title: b.title })))
  logs.sort((a, b) => b.time.localeCompare(a.time))
  const shown = logs.filter((l) => !S.actPerson || l.author === S.actPerson).slice(0, 15)

  v.innerHTML = `
    <div class="kpis">
      <div class="kpi"><b>${pct}%</b><span>hoàn thành (${done}/${active.length} đầu việc, không tính Hủy)</span></div>
      <div class="kpi"><b>${doing}</b><span>đang làm</span></div>
      <div class="kpi"><b style="color:var(--red)">${blocked.length}</b><span>bị chặn</span></div>
      <div class="kpi"><b>${unassigned}</b><span>chưa phân công</span></div>
    </div>
    <div class="grid2">
      <div>
        <div class="card"><h2>Tiến độ theo giai đoạn</h2>${phases}
          <div class="legend small" style="margin-top:8px">${COMMON.map(badge).join('')}</div></div>
        <div class="card"><h2>Việc bị chặn</h2>${blocked.length ? `<ul class="mini">${blocked.map((t) => {
          const last = [...t.logs].reverse().find((l) => l.kind === 'Vướng mắc')
          return `<li data-open="${t.id}"><span class="id">${t.id}</span><span class="nm">${esc(t.title)}${last ? `<div class="small muted">${esc(last.author)}: ${esc(last.text)}</div>` : ''}</span><span class="small muted">${esc(attr(t, 'Người phụ trách'))}</span></li>`
        }).join('')}</ul>` : '<p class="muted">Không có việc bị chặn.</p>'}</div>
      </div>
      <div>
        <div class="card"><h2>Pipeline</h2><ul class="mini">${blocksOf('PL').map((p) => `<li data-go="pipeline:${p.id}"><span class="id">${p.id}</span><span class="nm">${esc(p.title)}</span>${badge(statusOf(p))}</li>`).join('')}</ul></div>
        <div class="card"><h2>Model được chọn theo bài toán</h2><ul class="mini">${blocksOf('BT').map((b) => {
          const m = idsIn(attr(b, 'Model được chọn'))[0]
          return `<li data-go="model"><span class="id">${b.id}</span><span class="nm">${esc(b.title)}</span><span class="small">${m ? esc(label(m)) : '<span class="muted">Chưa chọn</span>'}</span></li>`
        }).join('')}</ul></div>
        <div class="card"><h2>Hoạt động gần đây</h2>
          <div class="seg" style="margin-bottom:8px">${['', ...PEOPLE].map((p) => `<button data-act="${p}" class="${S.actPerson === p ? 'on' : ''}">${p || 'Tất cả'}</button>`).join('')}</div>
          ${shown.length ? shown.map((l) => `<div class="log" data-open="${l.id}" style="cursor:pointer"><span class="who">${esc(l.author)}</span><span class="small muted">${esc(l.time)}</span>${kindTag(l.kind)}<span class="id">${l.id}</span><span>${esc(l.text)}</span></div>`).join('') : '<p class="muted">Chưa có hoạt động.</p>'}
        </div>
      </div>
    </div>`
  bindOpen(v)
  $$('[data-act]', v).forEach((b) => (b.onclick = () => { S.actPerson = b.dataset.act; refresh() }))
  $$('[data-go]', v).forEach((el) => (el.onclick = () => {
    const [view, step] = el.dataset.go.split(':')
    if (step) S.step = step
    location.hash = view
  }))
}
function kindTag(k) {
  const cls = { 'Kết quả': 'k-ketqua', 'Vướng mắc': 'k-vuongmac', 'Đề xuất điều chỉnh': 'k-dexuat' }[k] || ''
  return `<span class="kind ${cls}">${esc(k)}</span>`
}
function bindOpen(root) {
  $$('[data-open]', root).forEach((el) => (el.onclick = (e) => { e.stopPropagation(); openDrawer(el.dataset.open) }))
}

// ===== 2. Nghiệp vụ (xem như tài liệu) =====
function viewBusiness(v) {
  const groups = S.doc.containers.filter((c) => ['TQ', 'NV', 'QD'].includes(c.prefix))
  v.innerHTML = `<div class="doc">
    <div class="toc">${groups.map((c) => `<div class="grp">${esc(c.title)}</div>${c.ids.map((id) => `<a href="#nghiep-vu" data-jump="${id}">${id} ${esc(S.byId[id].title)}</a>`).join('')}`).join('')}</div>
    <div>${groups.map((c) => `<h1 style="margin-top:6px">${esc(c.title)}</h1>
      ${c.ids.map((id) => docBlock(S.byId[id])).join('')}
      ${c.prefix === 'QD' ? '<button class="btn" data-new="QD">+ Ghi quyết định</button>' : ''}`).join('')}</div>
  </div>`
  $$('[data-jump]', v).forEach((a) => (a.onclick = (e) => { e.preventDefault(); $(`#b-${a.dataset.jump}`).scrollIntoView({ behavior: 'smooth' }) }))
  bindDocBlocks(v)
  $$('[data-new]', v).forEach((b) => (b.onclick = () => createDialog(b.dataset.new)))
}
function docBlock(b) {
  const t = TYPES[b.prefix]
  const attrs = b.attrOrder.length ? `<dl class="attrs">${b.attrOrder.map((k) => `<dt>${esc(k)}</dt><dd>${k === 'Trạng thái' ? badge(b.attrs[k]) : esc(b.attrs[k]) || '<span class="muted">—</span>'}</dd>`).join('')}</dl>` : ''
  return `<div class="card" id="b-${b.id}">
    <div class="blk-head"><span class="id">${b.id}</span><h2>${esc(b.title)}</h2>
      <span class="acts"><button class="link" data-edit="${b.id}">Sửa</button>${t.fields.length ? `<button class="link" data-open="${b.id}">Chi tiết</button>` : ''}</span></div>
    <div data-area="${b.id}">${attrs}${md(b.body)}</div>
    ${logsHtml(b)}
  </div>`
}
function logsHtml(b, full = false) {
  const kinds = TYPES[b.prefix].logKinds || ['Bình luận']
  return `<div class="logs">
    ${b.logs.map((l) => `<div class="log"><span class="who">${esc(l.author)}</span><span class="small muted">${esc(l.time)}</span>${kindTag(l.kind)}<span>${esc(l.text)}</span></div>`).join('')}
    <div class="addlog" data-log="${b.id}">
      ${kinds.length > 1 || full ? `<select>${kinds.map((k) => `<option>${esc(k)}</option>`).join('')}</select>` : `<input type="hidden" value="${esc(kinds[0])}">`}
      <input placeholder="${kinds.length > 1 ? 'Thêm kết quả / vướng mắc / đề xuất…' : 'Thêm bình luận…'}"><button class="btn sm">Gửi</button>
    </div></div>`
}
function bindLogs(root) {
  $$('[data-log]', root).forEach((box) => {
    const [kindEl, textEl] = [box.querySelector('select, input[type=hidden]'), box.querySelector('input:not([type=hidden])')]
    const send = async () => {
      if (needUser() || !textEl.value.trim()) return
      const text = textEl.value
      textEl.value = ''
      try { await op({ op: 'addLog', id: box.dataset.log, kind: kindEl.value, text, author: S.user }, 'Đã ghi') } catch { textEl.value = text }
    }
    box.querySelector('button').onclick = send
    textEl.onkeydown = (e) => { if (e.key === 'Enter') send() }
  })
}
function bindDocBlocks(root) {
  bindLogs(root)
  bindOpen(root)
  $$('[data-edit]', root).forEach((btn) => (btn.onclick = () => rawEditor($(`[data-area="${btn.dataset.edit}"]`, root), S.byId[btn.dataset.edit])))
}
// Sửa markdown thô của một khối (phần nhật ký không sửa được ở đây)
function rawEditor(area, b) {
  S.editing = true
  const base = { hash: b.hash }
  area.innerHTML = `<textarea rows="${Math.min(30, b.core.split('\n').length + 3)}">${esc(b.core)}</textarea>
    <div class="small muted">Giữ nguyên dòng đầu "### ${b.id} …". Không dùng heading cấp 1–3. Nhật ký thêm ở ô bên dưới.</div>
    <div class="theirs"></div>
    <div class="actions"><button class="btn" data-x="cancel">Hủy</button><button class="btn primary" data-x="save">Lưu khối</button></div>`
  const ta = area.querySelector('textarea')
  ta.focus()
  area.querySelector('[data-x=cancel]').onclick = () => { S.editing = false; refresh() }
  area.querySelector('[data-x=save]').onclick = async () => {
    try {
      S.editing = false
      await op({ op: 'raw', id: b.id, raw: ta.value, hash: base.hash }, 'Đã lưu')
    } catch (e) {
      // bị người khác sửa trước: giữ bản đang soạn, hiện bản mới để đối chiếu
      if (e.status === 409 && S.byId[b.id]) {
        const fresh = S.byId[b.id]
        const target = $(`[data-area="${b.id}"]`) || (S.drawer === b.id && $('#dArea')) || area
        const draft = ta.value
        rawEditor(target, fresh)
        target.querySelector('textarea').value = draft
        target.querySelector('.theirs').innerHTML = `<div class="section-title">Bản mới trên đĩa (đối chiếu rồi lưu lại)</div><pre class="small" style="white-space:pre-wrap;background:var(--hover);padding:8px;border-radius:6px">${esc(fresh.core)}</pre>`
      } else S.editing = true
    }
  }
}

// ===== 3. Đầu việc =====
function viewTasks(v) {
  const f = S.f
  const tasks = blocksOf('T').filter((t) =>
    (!f.person || (f.person === '-' ? !attr(t, 'Người phụ trách') : attr(t, 'Người phụ trách') === f.person)) &&
    (!f.phase || attr(t, 'Giai đoạn') === f.phase) &&
    (!f.status || statusOf(t) === f.status) &&
    (!f.q || `${t.id} ${t.title} ${attr(t, 'Mô tả')}`.toLowerCase().includes(f.q.toLowerCase())))
  const opt = (list, cur) => list.map(([val, txt]) => `<option value="${esc(val)}" ${val === cur ? 'selected' : ''}>${esc(txt)}</option>`).join('')
  v.innerHTML = `
    <div class="toolbar">
      <div class="seg"><button data-v="kanban" class="${S.taskView === 'kanban' ? 'on' : ''}">Kanban</button><button data-v="table" class="${S.taskView === 'table' ? 'on' : ''}">Bảng</button></div>
      <select id="fPerson">${opt([['', 'Mọi người'], ...PEOPLE.map((p) => [p, p]), ['-', 'Chưa phân công']], f.person)}</select>
      <select id="fPhase">${opt([['', 'Mọi giai đoạn'], ...blocksOf('GD').map((g) => [g.id, `${g.id} ${g.title}`])], f.phase)}</select>
      <select id="fStatus">${opt([['', 'Mọi trạng thái'], ...COMMON.map((s) => [s, s])], f.status)}</select>
      <input id="fQ" type="search" placeholder="Tìm…" value="${esc(f.q)}">
      <div class="right"><span class="muted small">${tasks.length} việc</span><button class="btn primary" data-new="T">+ Thêm việc</button></div>
    </div>
    <div id="tasksBody"></div>`
  $$('[data-v]', v).forEach((b) => (b.onclick = () => { S.taskView = b.dataset.v; refresh() }))
  ;[['#fPerson', 'person'], ['#fPhase', 'phase'], ['#fStatus', 'status']].forEach(([sel, k]) => ($(sel, v).onchange = (e) => { f[k] = e.target.value; refresh() }))
  $('#fQ', v).oninput = (e) => { f.q = e.target.value; clearTimeout(S.qt); S.qt = setTimeout(() => { refresh(); const q = $('#fQ'); q.focus(); q.setSelectionRange(q.value.length, q.value.length) }, 250) }
  $('[data-new]', v).onclick = () => createDialog('T')
  const body = $('#tasksBody', v)
  if (S.taskView === 'table') {
    body.innerHTML = `<div class="tablewrap"><table class="t"><thead><tr><th>Mã</th><th>Đầu việc</th><th>Người</th><th>Giai đoạn</th><th>Trạng thái</th><th>Liên kết</th><th>Nhật ký</th></tr></thead><tbody>
      ${tasks.map((t) => `<tr class="click" data-open="${t.id}"><td class="id">${t.id}</td><td>${esc(t.title)}</td><td>${esc(attr(t, 'Người phụ trách')) || '<span class="muted">—</span>'}</td>
        <td class="id">${esc(attr(t, 'Giai đoạn'))}</td><td>${badge(statusOf(t))}</td><td class="small muted">${esc(attr(t, 'Liên kết'))}</td><td class="small muted">${t.logs.length || ''}</td></tr>`).join('')}
    </tbody></table></div>`
  } else {
    body.innerHTML = `<div class="kanban">${COMMON.map((s) => {
      const col = tasks.filter((t) => statusOf(t) === s)
      return `<div class="col" data-status="${s}"><h3>${badge(s)} <span class="muted">${col.length}</span></h3>
        ${col.map((t) => `<div class="kc c-${color(s)}" draggable="true" data-open="${t.id}" data-drag="${t.id}">
          <div class="tt">${esc(t.title)}</div>
          <div class="meta"><span class="id">${t.id}</span><span>${esc(attr(t, 'Người phụ trách')) || 'chưa phân công'}</span><span class="id">${esc(attr(t, 'Giai đoạn'))}</span>${t.logs.length ? `<span>💬 ${t.logs.length}</span>` : ''}</div>
        </div>`).join('')}</div>`
    }).join('')}</div>`
    $$('[data-drag]', body).forEach((c) => (c.ondragstart = (e) => e.dataTransfer.setData('text/plain', c.dataset.drag)))
    $$('.col', body).forEach((col) => {
      col.ondragover = (e) => { e.preventDefault(); col.classList.add('drop') }
      col.ondragleave = () => col.classList.remove('drop')
      col.ondrop = (e) => {
        e.preventDefault()
        col.classList.remove('drop')
        const id = e.dataTransfer.getData('text/plain')
        const t = S.byId[id]
        if (t && statusOf(t) !== col.dataset.status) {
          op({ op: 'setField', id, key: 'Trạng thái', value: col.dataset.status, old: statusOf(t) }, `${id} → ${col.dataset.status}`).catch(() => {})
        }
      }
    })
  }
  bindOpen(body)
}

// ===== 4. Pipeline =====
function viewPipeline(v) {
  const steps = blocksOf('PL')
  if (!S.byId[S.step]) S.step = steps[0] && steps[0].id
  const fill = { gray: '#eef0f2,#8b939e', blue: '#e7efff,#2563eb', red: '#fdecea,#d92d20', green: '#e6f6ec,#16a34a', amber: '#fdf2dc,#c27803', violet: '#f0eaff,#7c3aed', muted: '#f3f4f5,#a3a9b1' }
  const nid = (id) => id.replace('-', '')
  const graph = ['flowchart LR',
    ...steps.map((p) => `  ${nid(p.id)}["${p.title.replace(/"/g, "'")}<br/><small>${statusOf(p) || '—'}</small>"]:::${color(statusOf(p))}`),
    ...steps.slice(1).map((p, i) => `  ${nid(steps[i].id)} --> ${nid(p.id)}`),
    ...Object.entries(fill).map(([k, v2]) => { const [bg, st] = v2.split(','); return `  classDef ${k} fill:${bg},stroke:${st},color:#1f2328,stroke-width:1.5px` }),
    `  style ${nid(S.step)} stroke-width:3px`].join('\n')
  const step = S.byId[S.step]
  const types = STEP_TYPES[S.step] || []
  const tasks = blocksOf('T').filter((t) => idsIn(attr(t, 'Liên kết')).includes(S.step))
  v.innerHTML = `
    <div class="mermaid-box"><pre class="mermaid">${esc(graph)}</pre></div>
    <div class="legend small" style="margin:-6px 0 12px">${[...new Set(COMMON)].map(badge).join('')}<span class="muted">Bấm vào một bước để xem chi tiết</span></div>
    ${step ? `<div class="grid2">
      <div class="card"><div class="blk-head"><span class="id">${step.id}</span><h2>${esc(step.title)}</h2><span class="acts"><button class="link" data-open="${step.id}">Sửa bước</button></span></div>
        <dl class="attrs">${step.attrOrder.map((k) => `<dt>${esc(k)}</dt><dd>${k === 'Trạng thái' ? badge(step.attrs[k]) : esc(step.attrs[k]) || '<span class="muted">—</span>'}</dd>`).join('')}</dl>
        <div class="section-title">Đầu việc liên kết (${tasks.length})</div>
        ${tasks.length ? `<ul class="mini">${tasks.map((t) => `<li data-open="${t.id}"><span class="id">${t.id}</span><span class="nm">${esc(t.title)}</span>${badge(statusOf(t))}</li>`).join('')}</ul>` : '<p class="muted small">Chưa có đầu việc nào ghi liên kết tới bước này.</p>'}
      </div>
      <div>${types.length ? types.map((tp) => `<div class="card"><div class="blk-head"><h2>${TYPES[tp].name}</h2><span class="acts"><button class="link" data-new="${tp}">+ Thêm</button></span></div>
        ${blocksOf(tp).length ? `<ul class="mini">${blocksOf(tp).map((b) => `<li data-open="${b.id}"><span class="id">${b.id}</span><span class="nm">${esc(b.title)}<div class="small muted">${esc(summaryOf(b))}</div></span>${badge(statusOf(b))}</li>`).join('')}</ul>` : '<p class="muted small">Chưa có.</p>'}</div>`).join('')
        : '<div class="card"><p class="muted">Bước này không có danh sách đối tượng riêng — theo dõi qua thuộc tính của bước và các đầu việc liên kết.</p></div>'}</div>
    </div>` : ''}`
  bindOpen(v)
  $$('[data-new]', v).forEach((b) => (b.onclick = () => createDialog(b.dataset.new)))
  if (window.mermaid) {
    mermaid.run({ nodes: $$('.mermaid', v) }).then(() => {
      steps.forEach((p) => {
        const node = $(`.mermaid-box g.node[id*="-${nid(p.id)}-"]`, v) || $(`.mermaid-box g.node[id="${nid(p.id)}"]`, v)
        if (node) node.onclick = () => { S.step = p.id; refresh() }
      })
    }).catch((e) => console.warn(e))
  }
}
function summaryOf(b) {
  const keys = { DS: ['Nền tảng', 'Cách lấy', 'Số bản ghi'], CL: ['Thuật toán/thư viện'], ST: ['Hệ lưu trữ', 'Vị trí'], M: ['Loại', 'Bài toán phù hợp'], R: ['Model', 'F1-macro', 'Ngày chạy'], BT: ['Model được chọn', 'Metric mục tiêu'] }[b.prefix] || []
  return keys.map((k) => attr(b, k) && `${k}: ${attr(b, k)}`).filter(Boolean).join(' · ')
}

// ===== 5. Model & thí nghiệm =====
function viewModels(v) {
  const models = blocksOf('M')
  const runs = blocksOf('R').filter((r) => statusOf(r) !== 'Hủy')
  const metrics = ['Accuracy', 'F1-macro', 'Precision', 'Recall']
  const runsOf = (mid) => runs.filter((r) => idsIn(attr(r, 'Model')).includes(mid))
  const best = (list) => list.reduce((a, r) => (num(attr(r, 'F1-macro')) !== null && (!a || num(attr(r, 'F1-macro')) > num(attr(a, 'F1-macro'))) ? r : a), null)
  const sorted = [...runs].sort((a, b) => (num(attr(b, S.runSort)) ?? -1) - (num(attr(a, S.runSort)) ?? -1))
  const bestIds = new Set(blocksOf('BT').map((bt) => best(runs.filter((r) => idsIn(attr(S.byId[idsIn(attr(r, 'Model'))[0]], 'Bài toán phù hợp')).includes(bt.id)))).filter(Boolean).map((r) => r.id))

  v.innerHTML = `
    <h1>Bài toán ứng dụng</h1>
    <div class="grid2">${blocksOf('BT').map((bt) => {
      const chosen = idsIn(attr(bt, 'Model được chọn'))[0] || ''
      const cand = models.filter((m) => idsIn(attr(m, 'Bài toán phù hợp')).includes(bt.id) && !['Hủy', 'Loại'].includes(statusOf(m)))
      const b = best(runs.filter((r) => cand.some((m) => idsIn(attr(r, 'Model')).includes(m.id))))
      return `<div class="card"><div class="blk-head"><span class="id">${bt.id}</span><h2>${esc(bt.title)}</h2>${badge(statusOf(bt))}<span class="acts"><button class="link" data-open="${bt.id}">Chi tiết</button></span></div>
        <div class="form" style="margin:6px 0"><label>Model được chọn</label>
          <select data-choose="${bt.id}"><option value="">— Chưa chọn —</option>${cand.map((m) => `<option value="${m.id}" ${m.id === chosen ? 'selected' : ''}>${esc(m.id + ' ' + m.title)}</option>`).join('')}</select>
          <label>Metric mục tiêu</label><span class="small">${esc(attr(bt, 'Metric mục tiêu'))}</span>
          <label>F1-macro tốt nhất</label><span class="small">${b ? `${esc(attr(b, 'F1-macro'))} — ${esc(label(idsIn(attr(b, 'Model'))[0]))} (${b.id})` : '<span class="muted">chưa có lần chạy</span>'}</span></div></div>`
    }).join('')}</div>

    <div class="toolbar" style="margin-top:6px"><h1 style="margin:0">Các lần huấn luyện</h1><div class="right"><button class="btn primary" data-new="R">+ Ghi lần huấn luyện</button></div></div>
    <div class="tablewrap" style="margin-bottom:18px"><table class="t"><thead><tr><th>Mã</th><th>Model</th><th>Dữ liệu</th>
      ${metrics.map((m) => `<th class="sort num" data-sort="${m}">${m}${S.runSort === m ? ' ↓' : ''}</th>`).join('')}<th>Ngày chạy</th><th>Người chạy</th><th>Trạng thái</th></tr></thead><tbody>
      ${sorted.length ? sorted.map((r) => `<tr class="click ${bestIds.has(r.id) ? 'best' : ''}" data-open="${r.id}" title="${bestIds.has(r.id) ? 'F1-macro tốt nhất của bài toán' : ''}"><td class="id">${r.id}</td><td>${esc(label(idsIn(attr(r, 'Model'))[0] || attr(r, 'Model')))}</td>
        <td class="small">${esc(attr(r, 'Dữ liệu'))} ${attr(r, 'Phiên bản dữ liệu') ? `<span class="muted">(${esc(attr(r, 'Phiên bản dữ liệu'))})</span>` : ''}</td>
        ${metrics.map((m) => `<td class="num">${esc(attr(r, m))}</td>`).join('')}<td class="small">${esc(attr(r, 'Ngày chạy'))}</td><td class="small">${esc(attr(r, 'Người chạy'))}</td><td>${badge(statusOf(r))}</td></tr>`).join('')
        : `<tr><td colspan="${7 + metrics.length}" class="muted">Chưa có lần huấn luyện nào.</td></tr>`}
    </tbody></table></div>

    <div class="toolbar"><h1 style="margin:0">Model</h1><div class="right"><button class="btn primary" data-new="M">+ Thêm model</button></div></div>
    <div class="tablewrap"><table class="t"><thead><tr><th>Mã</th><th>Model</th><th>Loại</th><th>Bài toán</th><th>Lý do chọn</th><th class="num">Số lần chạy</th><th class="num">F1-macro tốt nhất</th><th>Trạng thái</th></tr></thead><tbody>
      ${models.map((m) => { const b = best(runsOf(m.id)); return `<tr class="click" data-open="${m.id}"><td class="id">${m.id}</td><td>${esc(m.title)}</td><td class="small">${esc(attr(m, 'Loại'))}</td>
        <td class="id">${esc(attr(m, 'Bài toán phù hợp'))}</td><td class="small muted">${esc(attr(m, 'Lý do chọn'))}</td><td class="num">${runsOf(m.id).length || ''}</td><td class="num">${b ? esc(attr(b, 'F1-macro')) : ''}</td><td>${badge(statusOf(m))}</td></tr>` }).join('')}
    </tbody></table></div>`
  bindOpen(v)
  $$('[data-new]', v).forEach((b) => (b.onclick = () => createDialog(b.dataset.new)))
  $$('[data-sort]', v).forEach((th) => (th.onclick = () => { S.runSort = th.dataset.sort; refresh() }))
  $$('[data-choose]', v).forEach((sel) => (sel.onchange = async () => {
    const bt = S.byId[sel.dataset.choose]
    const m = S.byId[sel.value]
    try {
      await op({ op: 'setField', id: bt.id, key: 'Model được chọn', value: m ? `${m.id} ${m.title}` : '', old: attr(bt, 'Model được chọn') })
      if (m && statusOf(m) !== 'Được chọn') await op({ op: 'setField', id: m.id, key: 'Trạng thái', value: 'Được chọn', old: statusOf(m) })
      toast(m ? `${bt.id}: chọn ${m.id}` : `${bt.id}: bỏ chọn`)
    } catch { /* đã báo */ }
  }))
}

// ===== Ngăn chi tiết (sửa theo trường, sửa thô, nhật ký) =====
function openDrawer(id) { S.drawer = id; renderDrawer() }
function closeDrawer() { S.drawer = null; S.editing = false; $('#layer').innerHTML = '' }
function fieldInput(b, [key, kind, opts]) {
  const val = attr(b, key)
  const t = TYPES[b.prefix]
  const options = (list) => {
    const all = val && !list.some(([v]) => v === val) ? [[val, val], ...list] : list
    return all.map(([v, txt]) => `<option value="${esc(v)}" ${v === val ? 'selected' : ''}>${esc(txt)}</option>`).join('')
  }
  if (kind === 'status') return `<select data-k="${key}">${options(t.statuses.map((s) => [s, s]))}</select>`
  if (kind === 'person') return `<select data-k="${key}">${options([['', '— chưa phân công —'], ...PEOPLE.map((p) => [p, p])])}</select>`
  if (kind === 'phase') return `<select data-k="${key}">${options([['', '—'], ...blocksOf('GD').map((g) => [g.id, `${g.id} ${g.title}`])])}</select>`
  if (kind === 'select') return `<select data-k="${key}">${options([['', '—'], ...opts.map((o) => [o, o])])}</select>`
  if (kind === 'model') {
    const list = blocksOf('M').map((m) => [`${m.id} ${m.title}`, `${m.id} ${m.title}`])
    if (val && !list.some(([v]) => v === val) && idsIn(val)[0] && S.byId[idsIn(val)[0]]) { /* giữ nguyên giá trị cũ */ }
    return `<select data-k="${key}">${options([['', '—'], ...list])}</select>`
  }
  return `<input data-k="${key}" value="${esc(val)}">`
}
function renderDrawer() {
  const b = S.byId[S.drawer]
  if (!b) return closeDrawer()
  const t = TYPES[b.prefix] || { name: b.prefix, fields: [] }
  const known = t.fields.map((f) => f[0])
  const extra = b.attrOrder.filter((k) => !known.includes(k)).map((k) => [k])
  $('#layer').innerHTML = `<div class="drawer-bg"></div><div class="drawer">
    <div class="toolbar"><span class="id">${b.id} · ${esc(t.name)}</span><div class="right">
      <button class="btn sm" id="dRaw">Sửa markdown thô</button>${t.cancel && statusOf(b) !== t.cancel ? `<button class="btn sm danger" id="dCancel">Đánh dấu ${t.cancel}</button>` : ''}
      <button class="btn sm" id="dClose">Đóng</button></div></div>
    <input class="title" id="dTitle" value="${esc(b.title)}">
    <div id="dArea">
      ${t.fields.length || extra.length ? `<div class="form">${[...t.fields, ...extra].map((f) => `<label>${esc(f[0])}</label>${fieldInput(b, f)}`).join('')}</div>` : ''}
      ${b.body ? `<div class="section-title">Nội dung</div>${md(b.body)}` : ''}
    </div>
    <div class="section-title">Nhật ký (${b.logs.length})</div>
    ${logsHtml(b, true)}
  </div>`
  $('.drawer-bg').onclick = closeDrawer
  $('#dClose').onclick = closeDrawer
  $('#dTitle').onchange = (e) => op({ op: 'setTitle', id: b.id, title: e.target.value, old: b.title }, 'Đã đổi tên').catch(() => {})
  $$('#dArea [data-k]').forEach((el) => (el.onchange = () => op({ op: 'setField', id: b.id, key: el.dataset.k, value: el.value, old: attr(b, el.dataset.k) }, 'Đã lưu').catch(() => {})))
  $('#dRaw').onclick = () => rawEditor($('#dArea'), b)
  if ($('#dCancel')) $('#dCancel').onclick = () => {
    if (confirm(`Đánh dấu ${b.id} là "${t.cancel}"? (Khối vẫn được giữ trong PROJECT.md, mã không bị dùng lại.)`)) {
      op({ op: 'setField', id: b.id, key: 'Trạng thái', value: t.cancel, old: statusOf(b) }, `Đã đánh dấu ${t.cancel}`).catch(() => {})
    }
  }
  bindLogs($('.drawer'))
}
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !S.editing) { closeDrawer(); closeModal() } })

// ===== Tạo mới =====
function closeModal() { const m = $('.modal-bg'); if (m) m.remove() }
function modal(html, wide = false) {
  closeModal()
  const el = document.createElement('div')
  el.className = 'modal-bg'
  el.innerHTML = `<div class="modal ${wide ? 'wide' : ''}">${html}</div>`
  el.onclick = (e) => { if (e.target === el) closeModal() }
  document.body.appendChild(el)
  return el
}
function createDialog(prefix) {
  if (needUser()) return
  const t = TYPES[prefix]
  const draft = { id: '', prefix, title: '', attrs: {}, attrOrder: [], logs: [] }
  // giá trị mặc định
  t.fields.forEach(([k, kind]) => { draft.attrs[k] = kind === 'status' ? t.statuses[0] : '' })
  if (prefix === 'T') { draft.attrs['Người phụ trách'] = S.user; draft.attrs['Giai đoạn'] = S.f.phase }
  if (prefix === 'R') { draft.attrs['Ngày chạy'] = today(); draft.attrs['Người chạy'] = S.user }
  if (prefix === 'QD') { draft.attrs['Ngày'] = today(); draft.attrs['Người chốt'] = S.user }
  const el = modal(`<h2>Thêm ${esc(t.name.toLowerCase())}</h2>
    <div class="form"><label>Tên</label><input id="nTitle">${t.fields.map((f) => `<label>${esc(f[0])}</label>${fieldInput(draft, f)}`).join('')}</div>
    <div class="actions"><button class="btn" id="nCancel">Hủy</button><button class="btn primary" id="nOk">Thêm</button></div>`)
  $('#nTitle', el).focus()
  $('#nCancel', el).onclick = closeModal
  $('#nOk', el).onclick = async () => {
    const title = $('#nTitle', el).value.trim()
    if (!title) return toast('Nhập tên', true)
    const attrs = {}
    t.fields.forEach(([k]) => { attrs[k] = $(`[data-k="${k}"]`, el).value })
    try {
      const r = await op({ op: 'create', prefix, title, attrs }, 'Đã thêm')
      closeModal()
      openDrawer(r.id)
    } catch { /* đã báo */ }
  }
}

// ===== Git =====
async function refreshGit(fetch = false) {
  try {
    const g = await api('/api/git/status' + (fetch ? '?fetch=1' : ''))
    S.git = g
    const parts = []
    if (g.merging) parts.push('đang gộp dở')
    if (g.docDirty) parts.push('PROJECT.md có thay đổi chưa commit')
    if (g.ahead) parts.push(`đi trước ${g.ahead} commit`)
    if (g.behind) parts.push(`đi sau ${g.behind} commit`)
    if (!g.upstream) parts.push('nhánh chưa có upstream')
    const info = $('#gitInfo')
    info.textContent = (g.branch ? g.branch + ': ' : '') + (parts.join(' · ') || 'đã đồng bộ')
    info.className = 'info' + (parts.length ? ' warn' : '')
    info.title = g.fetchError ? `Không fetch được: ${g.fetchError}` : ''
  } catch { /* server tạm lỗi */ }
}
function gitResult(r, title) {
  if (r.conflict) return openConflict(r.pushAfterResolve)
  if (r.ok) toast(r.message || title + ' xong')
  else modal(`<h2>${esc(title)} chưa xong</h2><p>${esc(r.error)}</p>${r.log && r.log.length ? `<pre>${esc(r.log.join('\n\n'))}</pre>` : ''}
    <div class="actions">${S.git && S.git.merging ? '<button class="btn danger left" id="abortBtn">Hủy gộp (git merge --abort)</button>' : ''}<button class="btn" onclick="closeModal()">Đóng</button></div>`, true)
  if ($('#abortBtn')) $('#abortBtn').onclick = abortMerge
}
async function gitAction(btn, path, title) {
  if (path.includes('commit') && needUser()) return
  btn.disabled = true
  try {
    const r = await api(path, { author: S.user })
    await reload()
    await refreshGit()
    gitResult(r, title)
  } catch (e) { toast(e.message, true) } finally { btn.disabled = false }
}
$('#pullBtn').onclick = (e) => gitAction(e.target, '/api/git/pull', 'Pull')
$('#pushBtn').onclick = (e) => gitAction(e.target, '/api/git/commit-push', 'Commit & Push')
async function abortMerge() {
  if (!confirm('Hủy gộp: quay về trạng thái trước khi pull (thay đổi của bạn đã commit vẫn còn).')) return
  const r = await api('/api/git/abort', {})
  closeModal()
  await reload()
  await refreshGit()
  toast(r.ok ? 'Đã hủy gộp' : r.error, !r.ok)
}
// Xung đột: không tự gộp ngầm — hiện từng đoạn để người dùng chọn bản giữ lại
async function openConflict(pushAfter = false) {
  const { hunks, status } = await api('/api/git/conflict')
  if (!hunks.length) return toast('Không có xung đột trong PROJECT.md' + (status.conflicted.length ? ` (còn ở: ${status.conflicted.join(', ')})` : ''))
  const choices = hunks.map(() => '')
  const el = modal(`<h2>Xung đột trong PROJECT.md (${hunks.length} đoạn)</h2>
    <p class="small muted">Bản của tôi = trên máy này. Bản từ remote = của người kia. Chọn bản giữ lại cho từng đoạn; "Giữ cả hai" hợp với nhật ký hai người cùng ghi.</p>
    ${status.conflicted.filter((f) => f !== 'PROJECT.md').length ? `<p class="banner">Còn xung đột ở file khác: ${esc(status.conflicted.filter((f) => f !== 'PROJECT.md').join(', '))} — xử lý trong VS Code.</p>` : ''}
    ${hunks.map((h) => `<div class="hunk"><div class="hh"><b>Đoạn ${h.index + 1}</b><span class="muted">gần: ${esc(h.context || 'đầu file')}</span>
      ${h.hasLogs ? `<span class="kind k-ketqua" title="Nhật ký chỉ thêm vào cuối nên dòng nhật ký của bên không chọn vẫn được giữ">nhật ký của cả hai bên luôn được giữ (${h.logsKept} dòng)</span>` : ''}
      <span style="margin-left:auto;display:flex;gap:10px;flex-wrap:wrap">${[['ours', 'Giữ bản của tôi'], ['theirs', 'Giữ bản từ remote'], ['both', 'Giữ cả hai']].map(([v, txt]) => `<label><input type="radio" name="h${h.index}" value="${v}"> ${txt}</label>`).join('')}</span></div>
      <div class="sides"><div><div class="small muted" style="padding:4px 8px">Bản của tôi</div><pre>${esc(h.ours.join('\n')) || '(trống)'}</pre></div>
      <div><div class="small muted" style="padding:4px 8px">Bản từ remote</div><pre>${esc(h.theirs.join('\n')) || '(trống)'}</pre></div></div></div>`).join('')}
    <div class="actions"><button class="btn danger left" id="cAbort">Hủy gộp</button><button class="btn" id="cClose">Để sau</button>
      <button class="btn primary" id="cOk">Hoàn tất gộp${pushAfter ? ' & Push' : ''}</button></div>`, true)
  $$('input[type=radio]', el).forEach((r) => (r.onchange = () => { choices[Number(r.name.slice(1))] = r.value }))
  $('#cClose', el).onclick = closeModal
  $('#cAbort', el).onclick = abortMerge
  $('#cOk', el).onclick = async (e) => {
    if (choices.some((c) => !c)) return toast('Chọn bản giữ lại cho mọi đoạn', true)
    if (needUser()) return
    e.target.disabled = true
    try {
      const r = await api('/api/git/resolve', { choices, author: S.user, push: pushAfter })
      closeModal()
      await reload()
      await refreshGit()
      gitResult(r, pushAfter ? 'Gộp & Push' : 'Gộp')
    } catch (err) { toast(err.message, true); e.target.disabled = false }
  }
}

// ===== Khởi động, tự tải lại khi file đổi =====
async function reload() { setDoc(await api('/api/doc')); refresh() }
async function poll() {
  try {
    const { hash } = await api('/api/version')
    if (hash !== S.doc.hash && !S.editing && !$('.modal-bg') && !(document.activeElement && document.activeElement.matches('input, textarea, select'))) await reload()
  } catch { /* bỏ qua */ }
}
$('#userSel').onchange = (e) => {
  S.user = e.target.value
  try { localStorage.setItem('pm-user', S.user) } catch { /* bỏ qua */ }
}
;(async function init() {
  try { S.user = localStorage.getItem('pm-user') || '' } catch { S.user = '' }
  $('#userSel').value = S.user
  if (window.mermaid) mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'base', flowchart: { htmlLabels: true, curve: 'basis' } })
  await reload()
  if (!S.user) toast('Chọn bạn là Nam hay Lâm ở góc phải để ghi nhật ký và commit.')
  refreshGit(true)
  setInterval(poll, 5000)
  setInterval(() => refreshGit(false), 20000)
  setInterval(() => refreshGit(true), 300000)
  window.addEventListener('focus', () => { poll(); refreshGit(false) })
})().catch((e) => { $('#main').innerHTML = `<div class="banner">Không kết nối được server: ${esc(e.message)}. Chạy <code>node tools/server.js</code> rồi tải lại trang.</div>` })
