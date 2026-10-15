// Task Hierarchy UI — /api/task-аас ирсэн бодит module өгөгдлийг SVG модоор зурна.
// Шинэчлэлт бүрийг өмнөхтэй нь харьцуулж (шинэ / алга болсон / төлөв өөрчлөгдсөн)
// тодруулж, snapshot бүрийг түүхэнд хадгална — алхамчилж эргэн харах боломжтой.
"use strict";

const STATES = {
  R: "running", S: "sleeping", D: "disk sleep", T: "stopped", t: "tracing stop",
  Z: "zombie", I: "idle", X: "dead",
};
// Байрлалын тогтмол, layoutTree(), diffTrees() — static/tree.js
const { NODE_W, NODE_H, V_GAP } = TREE;
const ANC_GAP = 18, PAD = 24;
const HISTORY_MAX = 50;
const SVG_NS = "http://www.w3.org/2000/svg";

const $ = (id) => document.getElementById(id);
const state = {
  pid: null, depth: 2, timer: null, procs: [], busy: false,
  demoRoot: null,
  last: null,          // хамгийн сүүлийн live хариу
  history: [],         // [{time, pid, comm, depth, data, diff}]
  view: null,          // null = live; эсвэл history-ийн индекс
};

// ---------------------------------------------------------------- API
class NetworkError extends Error {}

async function api(path, options, retry = 1) {
  let res;
  try {
    res = await fetch(path, options);
  } catch (e) {
    // Сүлжээний түр алдаа (жнь WSL localhost-ийн ERR_NETWORK_CHANGED) — GET-ийг нэг удаа дахин оролдоно
    if (retry > 0 && (!options || !options.method || options.method === "GET")) {
      await new Promise((r) => setTimeout(r, 300));
      return api(path, options, retry - 1);
    }
    throw new NetworkError("Сервертэй холбогдож чадсангүй — сүлжээний түр алдаа. Дахин оролдоно уу.");
  }
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
    setDemoRoot(s.demo_root);
  } catch (e) {
    pill.className = "pill pill-bad";
    pill.textContent = "● сервер холбогдохгүй";
  }
}

function setDemoRoot(root) {
  state.demoRoot = root ?? null;
  $("demo-panel").hidden = state.demoRoot === null;
  updateDemoControls();
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
async function select(pidText, { push = true, note = null } = {}) {
  if (state.busy) return;
  state.busy = true;
  $("pid-input").value = pidText;
  try {
    const d = await api(`/api/task?pid=${encodeURIComponent(pidText)}&depth=${state.depth}`);
    const samePid = state.last && state.last.task.pid === d.task.pid && state.last.depth === d.depth;
    const diff = samePid ? diffTrees(state.last.tree, d.tree) : null;
    state.pid = d.task.pid;
    state.last = d;
    setDemoRoot(d.demo_root);
    record(d, diff, note);
    state.view = null;
    $("error").hidden = true;
    render(d, diff);
    if (push) history.replaceState(null, "", `?pid=${state.pid}&depth=${state.depth}`);
  } catch (e) {
    showError(e.message);
    if (!(e instanceof NetworkError)) {   // сүлжээний түр алдаанд өмнөх дүрслэлийг хадгална
      clearView();
      stopAuto();
    }
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
  $("calls").replaceChildren();
  $("calls-total").textContent = "";
  $("diff").hidden = true;
  $("hist-banner").hidden = true;
  state.last = null;
  updateDemoControls();
}

// ---------------------------------------------------------------- diff (өмнөх шинэчлэлттэй харьцуулах — diffTrees: tree.js)
function renderDiff(diff) {
  const box = $("diff");
  if (!diff || (!diff.added.length && !diff.removed.length && !diff.changed.length)) {
    box.hidden = !diff;
    box.textContent = diff ? "Өмнөх шинэчлэлтээс хойш өөрчлөлтгүй." : "";
    box.className = "diff";
    return;
  }
  const parts = [];
  diff.added.forEach((n) => parts.push(["add", `+ ${n.comm} (${n.pid}) шинээр үүссэн`]));
  diff.changed.forEach((c) => parts.push(["chg", `~ ${c.node.comm} (${c.node.pid}) ${c.from} → ${c.to}`]));
  diff.removed.forEach((n) => parts.push(["del", `− ${n.comm} (${n.pid}) алга болсон`]));
  box.className = "diff active";
  box.replaceChildren(...parts.map(([cls, text]) => {
    const s = document.createElement("span"); s.className = cls; s.textContent = text; return s;
  }));
  box.hidden = false;
}

// ---------------------------------------------------------------- history (алхамчилж эргэн харах)
function record(d, diff, note = null) {
  state.history.push({
    time: new Date().toLocaleTimeString("en-GB"), pid: d.task.pid, comm: d.task.comm,
    depth: d.depth, nodes: d.nodes, data: d, diff, note,
  });
  if (state.history.length > HISTORY_MAX) state.history.shift();
  renderHistory();
}

function diffBadge(diff) {
  if (!diff) return "эхний";
  const { added, removed, changed } = diff;
  if (!added.length && !removed.length && !changed.length) return "өөрчлөлтгүй";
  return [added.length && `+${added.length}`, removed.length && `−${removed.length}`,
          changed.length && `~${changed.length}`].filter(Boolean).join(" ");
}

function renderHistory() {
  const list = $("history");
  const active = state.view ?? state.history.length - 1;
  $("hist-count").textContent = `(${state.history.length}/${HISTORY_MAX})`;
  list.replaceChildren(...state.history.map((h, i) => {
    const li = document.createElement("li");
    if (i === active) li.className = "active";
    li.textContent = `${h.time} · PID ${h.pid} ${h.comm} · depth ${h.depth} · ${h.nodes} зангилаа · ${diffBadge(h.diff)}`;
    if (h.note) {
      const n = document.createElement("div"); n.className = "note"; n.textContent = h.note;
      li.append(n);
    }
    li.addEventListener("click", () => viewHistory(i));
    return li;
  }).reverse());
  $("hist-prev").disabled = active <= 0;
  $("hist-next").disabled = state.view === null || active >= state.history.length - 1;
}

function viewHistory(i) {
  if (i < 0 || i >= state.history.length) return;
  if (i === state.history.length - 1) return backToLive();
  stopAuto();
  state.view = i;
  const h = state.history[i];
  render(h.data, h.diff);
  $("hist-text").textContent = `⏪ Түүх харж байна: ${h.time} · PID ${h.pid} (${h.comm}) — live өгөгдөл биш` +
    (h.note ? ` · ${h.note}` : "");
  $("hist-banner").hidden = false;
  renderHistory();
}

function backToLive() {
  state.view = null;
  $("hist-banner").hidden = true;
  if (state.history.length) {
    const h = state.history[state.history.length - 1];
    render(h.data, h.diff);
  }
  renderHistory();
}

// ---------------------------------------------------------------- render
function render(d, diff) {
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
  renderCalls(d);
  renderDiff(diff);
  drawTree(d, diff);
  updateDemoControls();
}

function renderCalls(d) {
  const calls = d.calls || [];
  $("calls").replaceChildren(...calls.map((c, i) => {
    const tr = document.createElement("tr");
    [i + 1, c.op, c.path, c.data, c.bytes, c.us].forEach((v, j) => {
      const td = document.createElement("td");
      td.textContent = v;
      if (j === 3) td.className = "mono";
      tr.append(td);
    });
    return tr;
  }));
  $("calls-total").textContent =
    `Сонгосон task-ийн асуулга дээр харуулав. Мод бүхэлдээ ${d.queries} асуулга × ${calls.length} үйлдэл = ` +
    `${d.queries * calls.length} систем дуудалт (write/read) хийсэн. Сервер бичих+уншихыг мутексээр нэг эгзэгтэй мужид оруулдаг.`;
}

function el(name, attrs = {}, text) {
  const e = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  return e;
}

function drawTree(d, diff) {
  const svg = $("tree");
  svg.replaceChildren();
  const added = new Set((diff?.added || []).map((n) => n.pid));
  const changed = new Map((diff?.changed || []).map((c) => [c.node.pid, c]));

  // 1) Хүү процессын мод: layoutTree() (tree.js) — олон навч хүүхдийг сүлжээ болгоно
  const size = layoutTree(d.tree);

  // 2) Өвөг эцгүүд (PID 1 → ... → эцэг) сонгосон task-ийн дээр нэг баганад,
  //    эсвэл "товчлох" үед модны дээр нэг мөр (breadcrumb)
  const compact = $("compact").checked;
  renderCrumbs(d, compact);
  const ancestors = compact ? [] : [...d.ancestors].reverse();
  const ancH = NODE_H + ANC_GAP;
  const selY = PAD + 14 + ancestors.length * ancH + (ancestors.length ? V_GAP - ANC_GAP : 0);
  const width = size.width + PAD * 2;
  const height = selY + size.height + PAD + 16;
  // Самбарт багтахгүй бол viewBox-оор жижигрүүлнэ (60%-иас доош бол гүйлгэх мөр)
  const avail = svg.parentElement.clientWidth - 4;
  const scale = avail > 0 ? Math.max(0.6, Math.min(1, avail / width)) : 1;
  svg.setAttribute("width", Math.round(width * scale));
  svg.setAttribute("height", Math.round(height * scale));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const grids = el("g"), edges = el("g"), nodes = el("g");
  svg.append(grids, edges, nodes);
  const cx = (n) => PAD + n._x + NODE_W / 2;
  const Y = (n) => selY + n._y;

  if (ancestors.length) nodes.append(el("text", { x: PAD, y: PAD, class: "label" }, "Өвөг эцгүүд (real_parent)"));
  ancestors.forEach((a, i) => {
    a._x = d.tree._x;
    const y = PAD + 14 + i * ancH;
    const next = i === ancestors.length - 1 ? selY : y + ancH;
    drawNode(nodes, a, PAD + a._x, y, { ancestor: true });
    edges.append(link(cx(a), y + NODE_H, cx(a), next, true));
  });

  (function draw(n) {
    const y = Y(n);
    drawNode(nodes, n, PAD + n._x, y, {
      selected: n === d.tree, isNew: added.has(n.pid), change: changed.get(n.pid),
    });
    if (n._grid) {
      // Олон навч хүүхэд: нэг хүрээнд сүлжээ, эцгээс хүрээ рүү ганц шугам
      const g = n._grid, gx = PAD + g.x - 8, gy = selY + g.y - 8;
      grids.append(el("rect", { class: "grid-box", x: gx, y: gy, width: g.width + 16, height: g.height + 16, rx: 10 }));
      grids.append(el("text", { x: gx + 8, y: gy - 6, class: "label" }, `${n.children.length} хүүхэд`));
      edges.append(link(cx(n), y + NODE_H, gx + (g.width + 16) / 2, gy));
      n.children.forEach(draw);
    } else {
      n.children.forEach((c) => {
        edges.append(link(cx(n), y + NODE_H, cx(c), Y(c)));
        draw(c);
      });
    }
    const hidden = (n.child_count || 0) - n.children.length + (n.truncated ? 1 : 0);
    if (hidden > 0) nodes.append(el("text", { x: cx(n), y: y + NODE_H + 14, "text-anchor": "middle", class: "more" }, `+${hidden} харуулаагүй`));
  })(d.tree);

  // Шинэ task сонгоход сонгосон зангилааг хэвтээ тэнхлэгт голлуулна (утас, өргөн мод);
  // ижил task-ийг автоматаар шинэчлэхэд хэрэглэгчийн гүйлгэсэн байрлалыг хадгална.
  if (state.centeredPid !== d.task.pid) {
    const sc = svg.parentElement;
    sc.scrollLeft = Math.max(0, cx(d.tree) * scale - sc.clientWidth / 2);
    state.centeredPid = d.task.pid;
  }
}

function renderCrumbs(d, compact) {
  const nav = $("crumbs");
  nav.hidden = !compact;
  if (!compact) return;
  const chain = [...d.ancestors].reverse();
  const items = chain.map((a) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = `${a.comm} (${a.pid})`;
    b.style.borderColor = stateColor(a.state_char);
    b.addEventListener("click", () => select(String(a.pid)));
    return b;
  });
  const cur = document.createElement("b");
  cur.textContent = `${d.task.comm} (${d.task.pid})`;
  nav.replaceChildren(...items.flatMap((b) => [b, document.createTextNode(" › ")]), cur);
}

function currentView() {
  if (state.view !== null) return state.history[state.view];
  const h = state.history[state.history.length - 1];
  return h ? { data: h.data, diff: h.diff } : null;
}

function link(x1, y1, x2, y2, up = false) {
  const my = (y1 + y2) / 2;
  return el("path", { d: `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`, class: up ? "edge up" : "edge" });
}

function drawNode(parent, n, x, y, { selected = false, ancestor = false, isNew = false, change = null } = {}) {
  const color = stateColor(n.state_char);
  const cls = ["node", selected && "selected", n.unexpanded && "unexpanded", ancestor && "ancestor",
               isNew && "added", change && "changed"].filter(Boolean).join(" ");
  const g = el("g", { class: cls, transform: `translate(${x},${y})`, tabindex: 0 });
  g.append(el("title", {}, `${n.comm}\nPID ${n.pid}  PPID ${n.ppid}  TGID ${n.tgid}\nState ${n.state_char} (${STATES[n.state_char] || "?"})\nUID ${n.uid}  threads ${n.threads}` + (n.demo ? "\n(demo процесс)" : "")));
  if (isNew || change) g.append(el("rect", { class: "halo", x: -4, y: -4, width: NODE_W + 8, height: NODE_H + 8, rx: 11 }));
  g.append(el("rect", { class: "box", width: NODE_W, height: NODE_H, rx: 8, stroke: color }));
  g.append(el("rect", { class: "band", width: 6, height: NODE_H, rx: 3, fill: color }));
  const name = n.comm.length > 19 ? n.comm.slice(0, 18) + "…" : n.comm;
  g.append(el("text", { x: 14, y: 21, "font-weight": selected ? 700 : 500 }, name));
  const sub = `PID ${n.pid} · ${n.state_char}` + (n.threads > 1 ? ` · ${n.threads} урсгал` : "");
  g.append(el("text", { x: 14, y: 39, class: "sub" }, sub));
  if (isNew) g.append(el("text", { x: NODE_W - 6, y: -7, "text-anchor": "end", class: "tag tag-new" }, "шинэ"));
  if (change) g.append(el("text", { x: NODE_W - 6, y: -7, "text-anchor": "end", class: "tag tag-chg" }, `${change.from}→${change.to}`));
  g.addEventListener("click", () => select(String(n.pid)));
  g.addEventListener("keydown", (e) => { if (e.key === "Enter") select(String(n.pid)); });
  parent.append(g);
}

// ---------------------------------------------------------------- demo control (туршилт удирдах)
function updateDemoControls() {
  const t = state.view === null ? state.last?.tree : state.history[state.view]?.data.tree;
  const isDemo = !!t && t.demo && state.view === null;
  const isRoot = !!t && t.pid === state.demoRoot;
  $("sel-label").textContent = t ? `${t.comm} (${t.pid})${isDemo ? "" : " — demo биш"}` : "—";
  document.querySelectorAll("button[data-sig]").forEach((b) => { b.disabled = !isDemo || isRoot; });
  document.querySelectorAll("button[data-demo]").forEach((b) => { b.disabled = state.demoRoot === null || state.view !== null; });
  $("demo-hint").textContent = isRoot
    ? "demo_root-д signal илгээхгүй — 'Demo зогсоох' ашиглана. Хүүхэд дээр нь дарж сонгоно уу."
    : "Зөвхөн demo процесст илгээгдэнэ. KILL хийсэн процесс эцэг нь wait() хийх хүртэл zombie (Z) болно.";
}

async function demoAction(kind) {
  try {
    await api(`/api/demo/${kind}`, { method: "POST" });
    await loadProcesses();
    if (state.pid !== null) await select(String(state.pid), { push: false });
  } catch (e) { showError(e.message); }
}

async function demoSignal(sig) {
  const t = state.last?.tree;
  if (!t) return;
  try {
    await api(`/api/demo/signal?pid=${t.pid}&sig=${sig}`, { method: "POST" });
    await select(String(t.pid), { push: false });
  } catch (e) { showError(e.message); }
}

// ---------------------------------------------------------------- scenario (процессын амьдралын мөчлөг)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function newestDemoChild() {
  const kids = state.last?.tree.children || [];
  const fresh = kids.filter((c) => c.comm.startsWith("demo_new_"));
  return fresh.length ? Math.max(...fresh.map((c) => c.pid)) : null;
}

async function playScenario() {
  if (state.scenario) return;
  state.scenario = true;
  $("scenario").disabled = true;
  stopAuto();
  const caption = (text) => { $("scenario-text").textContent = text; $("scenario-banner").hidden = false; };
  let pid = null;
  const steps = [
    ["1. fork() — demo_root 5 хүү процесс үүсгэв (S, R/S, T, Z, 5 урсгалтай)", async () => {
      const { root_pid } = await api("/api/demo", { method: "POST" });
      setDemoRoot(root_pid);
      state.history = []; state.last = null;
    }],
    ["2. SIGUSR1 → demo_root fork() хийж шинэ хүү demo_new_1 үүсгэв (ногоон — шинэ)",
      () => api("/api/demo/spawn", { method: "POST" })],
    ["3. SIGSTOP → demo_new_1 зогсов: S → T (шар — төлөв өөрчлөгдсөн)", () => {
      pid = newestDemoChild();
      return api(`/api/demo/signal?pid=${pid}&sig=STOP`, { method: "POST" });
    }],
    ["4. SIGCONT → demo_new_1 үргэлжлэв: T → S",
      () => api(`/api/demo/signal?pid=${pid}&sig=CONT`, { method: "POST" })],
    ["5. SIGTERM → demo_new_1 дууссан ч эцэг нь wait() хийгээгүй тул zombie: S → Z",
      () => api(`/api/demo/signal?pid=${pid}&sig=TERM`, { method: "POST" })],
    ["6. SIGHUP → demo_root wait() дуудав — zombie-уудын ПУБ чөлөөлөгдөж алга болов",
      () => api("/api/demo/reap", { method: "POST" })],
  ];
  try {
    for (const [note, run] of steps) {
      caption(`▶ ${note}`);
      await run();
      await select(String(state.demoRoot), { note });
      await sleep(1400);
    }
    caption("✔ Сценари дууссан — 'Түүх'-ээс алхам бүрийг (◀ ▶) дахин харж болно.");
    await loadProcesses();
  } catch (e) {
    showError(e.message);
  } finally {
    state.scenario = false;
    $("scenario").disabled = false;
  }
}

// ---------------------------------------------------------------- auto refresh, demo, reset
function startAuto() {
  stopAuto();
  if (state.view !== null) backToLive();
  $("auto").checked = true;
  state.timer = setInterval(() => { if (state.pid !== null) select(String(state.pid), { push: false }); }, +$("interval").value);
}
function stopAuto() {
  clearInterval(state.timer); state.timer = null; $("auto").checked = false;
}

async function demoStart() {
  try {
    const { root_pid } = await api("/api/demo", { method: "POST" });
    setDemoRoot(root_pid);
    await loadProcesses();
    await select(String(root_pid));
  } catch (e) { showError(e.message); }
}
async function demoStop() {
  try {
    await api("/api/demo/stop", { method: "POST" });
    setDemoRoot(null);
    await loadProcesses();
    if (state.pid !== null) await select(String(state.pid), { push: false });
  } catch (e) { showError(e.message); }
}
function reset() {
  stopAuto();
  state.pid = null; state.depth = 2; state.history = []; state.view = null;
  $("depth").value = "2"; $("pid-input").value = ""; $("filter").value = "";
  $("error").hidden = true;
  clearView();
  renderHistory();
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
$("hist-prev").addEventListener("click", () => viewHistory((state.view ?? state.history.length - 1) - 1));
$("hist-next").addEventListener("click", () => viewHistory((state.view ?? state.history.length - 1) + 1));
$("hist-live").addEventListener("click", backToLive);
$("scenario").addEventListener("click", playScenario);
$("compact").addEventListener("change", () => {
  const v = currentView();
  if (v) drawTree(v.data, v.diff);
  try { localStorage.setItem("compactAncestors", $("compact").checked ? "1" : "0"); } catch { /* optional */ }
});
try { $("compact").checked = localStorage.getItem("compactAncestors") === "1"; } catch { /* optional */ }
$("scenario-close").addEventListener("click", () => { $("scenario-banner").hidden = true; });
document.querySelectorAll("button[data-pid]").forEach((b) => b.addEventListener("click", () => select(b.dataset.pid)));
document.querySelectorAll("button[data-demo]").forEach((b) => b.addEventListener("click", () => demoAction(b.dataset.demo)));
document.querySelectorAll("button[data-sig]").forEach((b) => b.addEventListener("click", () => demoSignal(b.dataset.sig)));

(async function init() {
  renderLegend();
  clearView();
  renderHistory();
  await refreshStatus();
  await loadProcesses();
  const params = new URLSearchParams(location.search);
  if (params.has("depth")) { state.depth = +params.get("depth") || 0; $("depth").value = String(state.depth); }
  if (params.has("compact")) $("compact").checked = params.get("compact") === "1";
  if (params.get("scenario") === "1") await playScenario();
  else if (params.get("demo") === "1") await demoStart();
  else if (params.has("pid")) await select(params.get("pid"));
  if (params.has("view")) viewHistory(+params.get("view") - 1);      // жнь ?scenario=1&view=3
  if (params.get("raw") === "1") $("raw-panel").open = true;
  if (params.get("calls") === "1") $("calls-panel").open = true;
  if (params.get("auto") === "1") startAuto();
  setInterval(refreshStatus, 5000);
})();
