// Task Hierarchy UI — /api/task-аас ирсэн бодит module өгөгдлийг SVG модоор зурна.
"use strict";

const STATES = {
  R: "running", S: "sleeping", D: "disk sleep", T: "stopped", t: "tracing stop",
  Z: "zombie", I: "idle", X: "dead",
};
const NODE_W = 160, NODE_H = 50, H_GAP = 14, V_GAP = 54, ANC_GAP = 18, PAD = 24;
const SVG_NS = "http://www.w3.org/2000/svg";

const $ = (id) => document.getElementById(id);
const state = { pid: null, depth: 2, timer: null, procs: [], busy: false };

// ---------------------------------------------------------------- API
async function api(path, options) {
  const res = await fetch(path, options);
  let body;
  try { body = await res.json(); } catch { body = { error: `HTTP ${res.status}` }; }
  if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
  return body;
}

function stateColor(ch) {
  const key = ch === "t" ? "T" : ch;
  const v = getComputedStyle(document.documentElement).getPropertyValue(`--st-${key}`).trim();
  return v || "#888";
}

// ---------------------------------------------------------------- status
async function refreshStatus() {
  const pill = $("status");
  try {
    const s = await api("/api/status");
    if (s.module_loaded) {
      pill.className = "pill pill-ok";
      pill.textContent = `● module loaded · ${s.kernel}`;
    } else if (s.fallback_allowed) {
      pill.className = "pill pill-warn";
      pill.textContent = "● fallback (module биш)";
    } else {
      pill.className = "pill pill-bad";
      pill.textContent = "● module ачаалагдаагүй";
    }
    pill.title = s.backend || "backend байхгүй";
    $("fallback").hidden = s.module_loaded || !s.fallback_allowed;
  } catch (e) {
    pill.className = "pill pill-bad";
    pill.textContent = "● сервер холбогдохгүй";
  }
}

// ---------------------------------------------------------------- process list
async function loadProcesses() {
  try {
    state.procs = await api("/api/processes");
    renderProcList();
  } catch (e) { /* жагсаалт заавал биш */ }
}

function renderProcList() {
  const q = $("filter").value.trim().toLowerCase();
  const list = $("proc-list");
  const items = state.procs.filter((p) => !q || String(p.pid).startsWith(q) || p.comm.toLowerCase().includes(q));
  $("proc-count").textContent = `(${items.length}/${state.procs.length})`;
  list.replaceChildren(...items.slice(0, 600).map((p) => {
    const li = document.createElement("li");
    if (p.pid === state.pid) li.className = "active";
    li.title = `PPID ${p.ppid} · ${STATES[p.state_char] || p.state_char}`;
    const pid = document.createElement("span"); pid.className = "pid"; pid.textContent = p.pid;
    const comm = document.createElement("span"); comm.textContent = p.comm;
    const dot = document.createElement("span"); dot.textContent = "●"; dot.style.color = stateColor(p.state_char);
    li.append(pid, comm, dot);
    li.addEventListener("click", () => select(String(p.pid)));
    return li;
  }));
}

// ---------------------------------------------------------------- query
async function select(pidText, { push = true } = {}) {
  if (state.busy) return;
  state.busy = true;
  $("pid-input").value = pidText;
  try {
    const d = await api(`/api/task?pid=${encodeURIComponent(pidText)}&depth=${state.depth}`);
    state.pid = d.task.pid;
    $("error").hidden = true;
    render(d);
    if (push) history.replaceState(null, "", `?pid=${state.pid}&depth=${state.depth}`);
  } catch (e) {
    showError(e.message);
    clearView();
    stopAuto();
  } finally {
    state.busy = false;
    renderProcList();
  }
}

function showError(msg) {
  $("error").textContent = "✖ " + msg;
  $("error").hidden = false;
}

function clearView() {
  $("book").innerHTML = '<span class="muted">—</span>';
  $("info").replaceChildren();
  $("tree").replaceChildren();
  $("tree").setAttribute("width", 0); $("tree").setAttribute("height", 0);
  $("tree-meta").textContent = "";
  $("raw").textContent = "";
}

// ---------------------------------------------------------------- render
function render(d) {
  const t = d.task;
  $("book").textContent = `$ echo ${t.pid} > /proc/pid\n$ cat /proc/pid\n${d.book_line}`;

  const rows = [
    ["Command", t.comm], ["PID", t.pid], ["TGID", t.tgid], ["PPID", t.ppid],
    ["State", `${t.state_char} — ${STATES[t.state_char] || t.state_name}` + (t.state >= 0 ? `  (__state = ${t.state})` : "")],
    ["UID", t.uid], ["Урсгал (threads)", t.threads],
    ["Өвөг эцэг", d.summary.ancestors], ["Шууд хүүхэд", d.summary.children + (d.summary.truncated ? "+ (тасалсан)" : "")],
  ];
  $("info").replaceChildren(...rows.flatMap(([k, v]) => {
    const dt = document.createElement("dt"); dt.textContent = k;
    const dd = document.createElement("dd"); dd.textContent = v;
    return [dt, dd];
  }));
  $("tree-meta").textContent =
    `· ${d.nodes} зангилаа · ${d.queries} module асуулга · ${d.elapsed_ms} мс · ${d.backend}`;
  $("raw").textContent = d.raw;
  $("fallback").hidden = !d.backend.startsWith("procfs");
  drawTree(d);
}

function el(name, attrs = {}, text) {
  const e = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  return e;
}

function drawTree(d) {
  const svg = $("tree");
  svg.replaceChildren();

  // 1) Хүү процессын модыг байрлуулах: навч бүрт дараалсан x, эцэг — хүүхдүүдийнхээ дунд
  let nextX = 0, maxDepth = 0;
  (function layout(n, depth) {
    n._depth = depth; maxDepth = Math.max(maxDepth, depth);
    if (!n.children.length) { n._x = nextX; nextX += NODE_W + H_GAP; return; }
    n.children.forEach((c) => layout(c, depth + 1));
    n._x = (n.children[0]._x + n.children[n.children.length - 1]._x) / 2;
  })(d.tree, 0);

  // 2) Өвөг эцгүүд (PID 1 → ... → эцэг) сонгосон task-ийн дээр нэг баганад
  const ancestors = [...d.ancestors].reverse();
  const rowH = NODE_H + V_GAP, ancH = NODE_H + ANC_GAP;
  const selY = PAD + 14 + ancestors.length * ancH + (ancestors.length ? V_GAP - ANC_GAP : 0);
  const width = Math.max(nextX - H_GAP, NODE_W) + PAD * 2;
  const height = selY + (maxDepth + 1) * rowH - V_GAP + PAD + 16;
  svg.setAttribute("width", width);
  svg.setAttribute("height", height);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const edges = el("g"), nodes = el("g");
  svg.append(edges, nodes);
  const cx = (n) => PAD + n._x + NODE_W / 2;

  if (ancestors.length) nodes.append(el("text", { x: PAD, y: PAD, class: "label" }, "Өвөг эцгүүд (real_parent)"));
  ancestors.forEach((a, i) => {
    a._x = d.tree._x;
    const y = PAD + 14 + i * ancH;
    const next = i === ancestors.length - 1 ? selY : y + ancH;
    drawNode(nodes, a, PAD + a._x, y, { ancestor: true });
    edges.append(link(cx(a), y + NODE_H, cx(a), next, true));
  });

  (function draw(n) {
    const y = selY + n._depth * rowH;
    drawNode(nodes, n, PAD + n._x, y, { selected: n._depth === 0 });
    n.children.forEach((c) => {
      edges.append(link(cx(n), y + NODE_H, cx(c), y + rowH));
      draw(c);
    });
    const hidden = (n.child_count || 0) - n.children.length + (n.truncated ? 1 : 0);
    if (hidden > 0) nodes.append(el("text", { x: cx(n), y: y + NODE_H + 14, "text-anchor": "middle", class: "more" }, `+${hidden} харуулаагүй`));
  })(d.tree);
}

function link(x1, y1, x2, y2, up = false) {
  const my = (y1 + y2) / 2;
  return el("path", { d: `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`, class: up ? "edge up" : "edge" });
}

function drawNode(parent, n, x, y, { selected = false, ancestor = false } = {}) {
  const color = stateColor(n.state_char);
  const cls = ["node", selected && "selected", n.unexpanded && "unexpanded", ancestor && "ancestor"].filter(Boolean).join(" ");
  const g = el("g", { class: cls, transform: `translate(${x},${y})`, tabindex: 0 });
  g.append(el("title", {}, `${n.comm}\nPID ${n.pid}  PPID ${n.ppid}  TGID ${n.tgid}\nState ${n.state_char} (${STATES[n.state_char] || "?"})\nUID ${n.uid}  threads ${n.threads}`));
  g.append(el("rect", { class: "box", width: NODE_W, height: NODE_H, rx: 8, stroke: color }));
  g.append(el("rect", { class: "band", width: 6, height: NODE_H, rx: 3, fill: color }));
  const name = n.comm.length > 19 ? n.comm.slice(0, 18) + "…" : n.comm;
  g.append(el("text", { x: 14, y: 21, "font-weight": selected ? 700 : 500 }, name));
  const sub = `PID ${n.pid} · ${n.state_char}` + (n.threads > 1 ? ` · ${n.threads} урсгал` : "");
  g.append(el("text", { x: 14, y: 39, class: "sub" }, sub));
  g.addEventListener("click", () => select(String(n.pid)));
  g.addEventListener("keydown", (e) => { if (e.key === "Enter") select(String(n.pid)); });
  parent.append(g);
}

// ---------------------------------------------------------------- auto refresh, demo, reset
function startAuto() {
  stopAuto();
  $("auto").checked = true;
  state.timer = setInterval(() => { if (state.pid !== null) select(String(state.pid), { push: false }); }, +$("interval").value);
}
function stopAuto() {
  clearInterval(state.timer); state.timer = null; $("auto").checked = false;
}

async function demoStart() {
  try {
    const { root_pid } = await api("/api/demo", { method: "POST" });
    await loadProcesses();
    await select(String(root_pid));
  } catch (e) { showError(e.message); }
}
async function demoStop() {
  try {
    await api("/api/demo/stop", { method: "POST" });
    await loadProcesses();
    if (state.pid !== null) await select(String(state.pid), { push: false });
  } catch (e) { showError(e.message); }
}
function reset() {
  stopAuto();
  state.pid = null; state.depth = 2;
  $("depth").value = "2"; $("pid-input").value = ""; $("filter").value = "";
  $("error").hidden = true;
  clearView();
  history.replaceState(null, "", "/");
  renderProcList();
}

function renderLegend() {
  $("legend").replaceChildren(...["R", "S", "D", "T", "Z", "I"].map((c) => {
    const li = document.createElement("li");
    const i = document.createElement("i"); i.style.background = stateColor(c);
    li.append(i, `${c} ${STATES[c]}`);
    return li;
  }));
}

// ---------------------------------------------------------------- init
$("query-form").addEventListener("submit", (e) => { e.preventDefault(); select($("pid-input").value); });
$("depth").addEventListener("change", () => { state.depth = +$("depth").value; if (state.pid !== null) select(String(state.pid)); });
$("filter").addEventListener("input", renderProcList);
$("auto").addEventListener("change", () => ($("auto").checked ? startAuto() : stopAuto()));
$("interval").addEventListener("change", () => { if (state.timer) startAuto(); });
$("demo-start").addEventListener("click", demoStart);
$("demo-stop").addEventListener("click", demoStop);
$("reset").addEventListener("click", reset);
document.querySelectorAll("button[data-pid]").forEach((b) => b.addEventListener("click", () => select(b.dataset.pid)));

(async function init() {
  renderLegend();
  clearView();
  await refreshStatus();
  await loadProcesses();
  const params = new URLSearchParams(location.search);
  if (params.has("depth")) { state.depth = +params.get("depth") || 0; $("depth").value = String(state.depth); }
  if (params.get("demo") === "1") await demoStart();
  else if (params.has("pid")) await select(params.get("pid"));
  if (params.get("raw") === "1") document.querySelector("details.raw").open = true;
  if (params.get("auto") === "1") startAuto();
  setInterval(refreshStatus, 5000);
})();
