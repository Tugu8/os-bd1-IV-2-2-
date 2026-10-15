// static/tree.js-ийн тест (Node 18+, нэмэлт сангүй):
//   node --test src/ui/tests/test_tree.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { TREE, layoutTree, flattenTree, diffTrees, stripLayout } = require("../static/tree.js");

const STEP = TREE.NODE_W + TREE.H_GAP;
const ROW = TREE.NODE_H + TREE.V_GAP;

let nextPid = 100;
const node = (children = [], state_char = "S") => ({ pid: nextPid++, comm: "p", state_char, children });
const leaves = (k) => Array.from({ length: k }, () => node());

function allNodes(tree) { return [...flattenTree(tree).values()]; }

function assertNoOverlap(tree) {
  const ns = allNodes(tree);
  for (let i = 0; i < ns.length; i++) {
    for (let j = i + 1; j < ns.length; j++) {
      const a = ns[i], b = ns[j];
      const apart = a._x + TREE.NODE_W <= b._x || b._x + TREE.NODE_W <= a._x ||
                    a._y + TREE.NODE_H <= b._y || b._y + TREE.NODE_H <= a._y;
      assert.ok(apart, `PID ${a.pid} (${a._x},${a._y}) ба ${b.pid} (${b._x},${b._y}) давхцаж байна`);
    }
  }
}

function assertParentsAbove(tree) {
  (function walk(n) {
    for (const c of n.children) {
      assert.ok(c._y >= n._y + TREE.NODE_H, `хүү ${c.pid} эцэг ${n.pid}-ийн доор байх ёстой`);
      walk(c);
    }
  })(tree);
}

function assertFits(tree, size) {
  for (const n of allNodes(tree)) {
    assert.ok(n._x >= 0 && n._x + TREE.NODE_W <= size.width + 1e-9, `PID ${n.pid} өргөнөөс гарсан`);
    assert.ok(n._y >= 0 && n._y + TREE.NODE_H <= size.height + 1e-9, `PID ${n.pid} өндрөөс гарсан`);
  }
}

test("ганц зангилаа", () => {
  const t = node();
  const size = layoutTree(t);
  assert.deepEqual([t._x, t._y], [0, 0]);
  assert.deepEqual(size, { width: TREE.NODE_W, height: TREE.NODE_H });
});

test("3 навч — нэг эгнээ, эцэг голд", () => {
  const t = node(leaves(3));
  layoutTree(t);
  assert.deepEqual(t.children.map((c) => c._x), [0, STEP, 2 * STEP]);
  assert.ok(t.children.every((c) => c._y === ROW));
  assert.equal(t._x, STEP);
  assert.equal(t._grid, undefined);
});

test(`GRID_MIN-ээс (${TREE.GRID_MIN}) цөөн навч бол сүлжээ үүсэхгүй`, () => {
  const t = node(leaves(TREE.GRID_MIN - 1));
  layoutTree(t);
  assert.equal(t._grid, undefined);
});

test("13 навч — 6 баганатай 3 мөр сүлжээ", () => {
  const t = node(leaves(13));
  const size = layoutTree(t);
  assert.deepEqual([t._grid.cols, t._grid.rows], [TREE.GRID_COLS, 3]);
  const k = t.children[TREE.GRID_COLS];                  // 2-р мөрийн эхний навч
  assert.deepEqual([k._x, k._y], [0, ROW + TREE.NODE_H + TREE.GRID_ROW_GAP]);
  assert.equal(size.width, TREE.GRID_COLS * STEP - TREE.H_GAP);
  assertNoOverlap(t);
  assertFits(t, size);
});

test("сүлжээ ба гүн дэд мод хамт — давхцалгүй", () => {
  const t = node([node(leaves(9)), node([node(leaves(2)), node(leaves(1))]), node()]);
  const size = layoutTree(t);
  assertNoOverlap(t);
  assertParentsAbove(t);
  assertFits(t, size);
});

test("380 навчтай мод (systemd төст) — өргөн нь нэг эгнээнийхээс олон дахин бага", () => {
  const t = node(Array.from({ length: 20 }, () => node(leaves(19))));
  const size = layoutTree(t);
  const singleRow = 380 * STEP - TREE.H_GAP;
  assert.ok(size.width < singleRow / 2.5, `өргөн ${size.width} ≥ ${singleRow / 2.5}`);
  assertNoOverlap(t);
  assertFits(t, size);
});

test("санамсаргүй 300 мод — давхцалгүй, эцэг дээр, хүрээнд багтана", () => {
  let seed = 12345;
  const rand = () => (seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31;
  const gen = (depth) => node(depth > 0 && rand() < 0.8
    ? Array.from({ length: Math.floor(rand() * (rand() < 0.3 ? 15 : 4)) }, () => gen(depth - 1))
    : []);
  for (let i = 0; i < 300; i++) {
    const t = gen(4);
    const size = layoutTree(t);
    assertNoOverlap(t);
    assertParentsAbove(t);
    assertFits(t, size);
  }
});

test("diffTrees — шинэ, алга болсон, төлөв өөрчлөгдсөн", () => {
  const a = node([], "S"), b = node([], "S"), c = node([], "R");
  const before = { pid: 1, state_char: "S", children: [a, b] };
  const after = { pid: 1, state_char: "S", children: [{ ...a, state_char: "T" }, c] };
  const d = diffTrees(before, after);
  assert.deepEqual(d.added.map((n) => n.pid), [c.pid]);
  assert.deepEqual(d.removed.map((n) => n.pid), [b.pid]);
  assert.deepEqual(d.changed.map((x) => [x.node.pid, x.from, x.to]), [[a.pid, "S", "T"]]);
});

test("stripLayout — экспортод layout талбар үлдэхгүй, эх мод өөрчлөгдөхгүй", () => {
  const t = node([node(leaves(8)), node()]);
  layoutTree(t);
  const s = stripLayout(t);
  const json = JSON.stringify(s);
  assert.ok(!/"_(x|y|grid|inGrid)"/.test(json), json.slice(0, 120));
  assert.equal(s.children[0].children.length, 8);
  assert.ok("_x" in t && "_grid" in t.children[0]);           // эх мод хэвээр
});

test("diffTrees — ижил мод бол хоосон", () => {
  const t = node(leaves(4));
  const d = diffTrees(t, structuredClone(t));
  assert.deepEqual([d.added.length, d.removed.length, d.changed.length], [0, 0, 0]);
});

test("diffTrees — зангилаа нээх/хаах нь шинэ/алга болсон гэж тооцогдохгүй", () => {
  const closed = node([node(), { ...node(), unexpanded: true }]);
  const open = structuredClone(closed);
  delete open.children[1].unexpanded;
  open.children[1].children = leaves(3);                       // нээхэд харагдах болсон ач нар
  for (const [a, b] of [[closed, open], [open, closed]]) {
    const d = diffTrees(a, b);
    assert.deepEqual([d.added.length, d.removed.length, d.changed.length], [0, 0, 0]);
  }
});

test("diffTrees — нээлттэй эцгийн доор бодитоор үүссэн/дууссан процесс тооцогдоно", () => {
  const before = node([node([node()]), { ...node(), unexpanded: true }]);
  const after = structuredClone(before);
  const gone = after.children[0].children[0].pid, fresh = node([], "R");
  after.children[0].children = [fresh];
  const d = diffTrees(before, after);
  assert.deepEqual(d.added.map((n) => n.pid), [fresh.pid]);
  assert.deepEqual(d.removed.map((n) => n.pid), [gone]);
});
