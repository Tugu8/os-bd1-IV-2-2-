// Task Hierarchy — DOM-гүй цэвэр логик: модны байрлал (layout) ба өөрчлөлт илрүүлэх (diff).
// Браузерт app.js-ээс өмнө ачаалагдана; Node дээр src/ui/tests/test_tree.mjs тестлэнэ.
"use strict";

const TREE = {
  NODE_W: 160, NODE_H: 50, H_GAP: 14, V_GAP: 54,
  GRID_MIN: 7,      // хүүхдүүд бүгд навч бөгөөд үүнээс олон бол сүлжээ (grid) болгоно
  GRID_COLS: 6,     // сүлжээний баганын тоо
  GRID_ROW_GAP: 16, // сүлжээний мөр хоорондын зай
};

/**
 * Модыг байрлуулна — зангилаа бүрт _x, _y (зүүн дээд булан, PAD-гүй) онооно.
 *  - Навч бүр дараалсан x авна; эцэг нь хүүхдүүдийнхээ голд.
 *  - Олон навч хүүхэдтэй эцгийн хүүхдүүдийг GRID_COLS баганатай сүлжээнд (n._grid = {cols, rows}).
 * Буцаах: {width, height} — модны эзлэх хэмжээ (top = 0-ээс).
 */
function layoutTree(root, cfg = TREE) {
  const step = cfg.NODE_W + cfg.H_GAP;
  const rowH = cfg.NODE_H + cfg.V_GAP;
  let nextX = 0, maxBottom = 0;

  (function place(n, y) {
    n._y = y;
    maxBottom = Math.max(maxBottom, y + cfg.NODE_H);
    const kids = n.children || [];
    if (!kids.length) {
      n._x = nextX;
      nextX += step;
      return;
    }
    const leaves = kids.every((c) => !(c.children && c.children.length));
    if (leaves && kids.length >= cfg.GRID_MIN) {
      const cols = cfg.GRID_COLS, rows = Math.ceil(kids.length / cols);
      const x0 = nextX;
      kids.forEach((c, i) => {
        c._x = x0 + (i % cols) * step;
        c._y = y + rowH + Math.floor(i / cols) * (cfg.NODE_H + cfg.GRID_ROW_GAP);
        c._inGrid = true;
        maxBottom = Math.max(maxBottom, c._y + cfg.NODE_H);
      });
      nextX = x0 + cols * step;
      n._grid = { cols, rows, x: x0, y: y + rowH, width: cols * step - cfg.H_GAP,
                  height: rows * (cfg.NODE_H + cfg.GRID_ROW_GAP) - cfg.GRID_ROW_GAP };
      n._x = x0 + (n._grid.width - cfg.NODE_W) / 2;
      return;
    }
    kids.forEach((c) => place(c, y + rowH));
    n._x = (kids[0]._x + kids[kids.length - 1]._x) / 2;
  })(root, 0);

  return { width: Math.max(nextX - cfg.H_GAP, cfg.NODE_W), height: maxBottom };
}

/** Модыг pid → зангилаа Map болгоно. */
function flattenTree(tree) {
  const m = new Map();
  (function walk(n) { m.set(n.pid, n); (n.children || []).forEach(walk); })(tree);
  return m;
}

/** pid → эцгийн pid (модны бүтцээс). */
function parentMap(tree) {
  const m = new Map();
  (function walk(n) { (n.children || []).forEach((c) => { m.set(c.pid, n.pid); walk(c); }); })(tree);
  return m;
}

/**
 * Хоёр snapshot-ийн ялгаа: шинэ, алга болсон, төлөв өөрчлөгдсөн зангилаанууд.
 * Шинэ/алга болсныг зөвхөн эцгийнх нь хүүхдийн жагсаалт нөгөө snapshot-д ч мэдэгдэж
 * байсан (unexpanded навч биш) үед тооцно — зангилаа нээх/хаах, гүн солиход
 * "харагдах болсон" процессыг "шинээр үүссэн" гэж андуурахгүй.
 */
function diffTrees(oldTree, newTree) {
  const before = flattenTree(oldTree), after = flattenTree(newTree);
  const pBefore = parentMap(oldTree), pAfter = parentMap(newTree);
  const listed = (nodes, parent) => parent === undefined || (nodes.has(parent) && !nodes.get(parent).unexpanded);
  const added = [], removed = [], changed = [];
  for (const [pid, n] of after) {
    const o = before.get(pid);
    if (!o) { if (listed(before, pAfter.get(pid))) added.push(n); }
    else if (o.state_char !== n.state_char) changed.push({ node: n, from: o.state_char, to: n.state_char });
  }
  for (const [pid, o] of before) if (!after.has(pid) && listed(after, pBefore.get(pid))) removed.push(o);
  return { added, removed, changed };
}

/** Экспортын өмнө layout-ын туслах талбаруудыг (_x, _y, _grid, _inGrid) хасна — эх модыг өөрчлөхгүй. */
function stripLayout(n) {
  const { _x, _y, _grid, _inGrid, children, ...rest } = n;
  return { ...rest, children: (children || []).map(stripLayout) };
}

if (typeof module !== "undefined") module.exports = { TREE, layoutTree, flattenTree, diffTrees, stripLayout };
