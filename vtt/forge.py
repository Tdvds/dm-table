"""Map Forge: paint terrain, stamp chunks, place objects, or let the forge generate dungeons, caves and wilds."""
import json, os, time
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QImage, QKeySequence, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFileDialog, QFormLayout, QGraphicsPixmapItem,
                               QGraphicsScene, QGraphicsView, QInputDialog, QLabel, QListView, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QStackedWidget, QTabWidget, QVBoxLayout, QWidget)
from . import brew, forge_draw as fd, icons, rules
from .forge_gen import (BUILTIN, GENERATORS, LIQUID, OBJECTS, TERRAIN, VOID, FLOOR, MapData, flip, rotate)
from .panels import btn, check, combo, group, hint, hrow, ispin, slider

CS = 40  # editor pixels per cell; exports use their own size
EXPORT_CS = 70  # matches the table's default grid
INTERACTIVE = {"door", "chest", "torch", "trap"}  # become live objects on the table
TOOLS = [("paint", "🖌 Paint", "B"), ("room", "▭ Room", "U"), ("fill", "◧ Fill", "G"), ("erase", "⌫ Erase", "E"),
         ("object", "⚱ Object", "O"), ("chunk", "▦ Chunk", "C"), ("select", "⬚ Select", "S"), ("pick", "⊙ Pick", "I")]


class Canvas(QGraphicsView):
    def __init__(self, f):
        super().__init__()
        self.f, self.hover, self.pan, self.down = f, None, None, False
        self.setScene(QGraphicsScene())
        self.item = QGraphicsPixmapItem()
        self.scene().addItem(self.item)
        self.setBackgroundBrush(QColor(18, 13, 10))
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def cell(self, e):
        p = self.mapToScene(e.position().toPoint())
        return int(p.x() // CS), int(p.y() // CS)

    def mousePressEvent(self, e):
        if e.button() in (Qt.MiddleButton, Qt.RightButton):
            self.pan = e.position()
        elif e.button() == Qt.LeftButton:
            self.down = True
            self.f.press(*self.cell(e))

    def mouseMoveEvent(self, e):
        c = self.cell(e)
        if self.pan is not None:
            d = e.position() - self.pan
            self.pan = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(d.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(d.y()))
        elif self.down:
            self.f.drag(*c)
        if c != self.hover:
            self.hover = c
            self.f.status(c)
            self.viewport().update()

    def mouseReleaseEvent(self, e):
        if self.pan is not None and e.button() in (Qt.MiddleButton, Qt.RightButton):
            self.pan = None
        elif e.button() == Qt.LeftButton and self.down:
            self.down = False
            self.f.release(*self.cell(e))

    def wheelEvent(self, e):
        k = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale(k, k)

    def leaveEvent(self, e):
        self.hover = None
        self.viewport().update()

    def drawForeground(self, p, rect):
        self.f.overlay(p)


class Forge(QMainWindow):
    closed = Signal()

    def __init__(self, launcher=None, data_dir="."):
        super().__init__()
        self.launcher, self.data_dir = launcher, data_dir
        self.m, self.path, self.dirty = MapData(40, 30), None, False
        self.undo_stack, self.redo_stack = [], []
        self.tool, self.terrain, self.object, self.brush, self.grid = "paint", FLOOR, "door", 1, True
        self.chunk, self.chunk_img, self.sel, self.start, self.last = None, None, None, None, None
        self.custom_file = os.path.join(data_dir, "forge_chunks.json")
        self.chunks = BUILTIN + self.load_custom()
        self.load_brew()
        self.canvas = Canvas(self)
        self.setCentralWidget(self.canvas)
        self.setWindowTitle("Map Forge")
        self.setWindowIcon(icons.icon("forge"))
        self.build_toolbar()
        self.build_menu()
        self.build_palette()
        self.statusBar().showMessage("Paint with the left button, pan with right/middle drag, zoom with the wheel.")
        self.resize(1500, 920)
        self.full_render()

    # ---------- building the window ----------
    def build_toolbar(self):
        tb = self.addToolBar("Tools")
        tb.setMovable(False)
        grp, self.tool_acts = QActionGroup(self), {}
        for key, label, sc in TOOLS:
            a = QAction(label, self, checkable=True, checked=key == "paint", toolTip=f"{label[2:]} ({sc})")
            a.setShortcut(QKeySequence(sc))
            a.triggered.connect(lambda _=False, k=key: self.set_tool(k))
            grp.addAction(a)
            tb.addAction(a)
            self.tool_acts[key] = a
        tb.addSeparator()
        tb.addWidget(QLabel(" Brush "))
        self.brush_box = ispin(1, 9, 1, lambda v: setattr(self, "brush", v))
        tb.addWidget(self.brush_box)
        tb.addSeparator()
        for text, fn, key, show in (("↶", self.undo, "Ctrl+Z", True), ("↷", self.redo, "Ctrl+Y", True),
                                    ("Rotate chunk", self.rot, "R", False), ("Flip chunk", self.flp, "F", False)):
            a = QAction(text, self, shortcut=QKeySequence(key), toolTip=f"{text} ({key})")
            a.triggered.connect(lambda _=False, f=fn: f())
            tb.addAction(a) if show else self.addAction(a)  # R/F work as keys without taking toolbar room
        tb.addSeparator()
        g = QAction("# Grid", self, checkable=True, checked=True)
        g.toggled.connect(self.set_grid)
        tb.addAction(g)
        a = QAction("⤢ Fit", self)
        a.triggered.connect(self.fit)
        tb.addAction(a)
        tb.addSeparator()
        a = QAction("▶ Send to the Table", self, toolTip="Open this map on the table with working doors, chests, torches and traps")
        a.triggered.connect(self.send_to_table)
        tb.addAction(a)

    def build_menu(self):
        m = self.menuBar().addMenu("&Map")
        for text, fn, key in (("New…", self.new_map, "Ctrl+N"), ("Open…", self.open_map, "Ctrl+O"), ("Save", self.save, "Ctrl+S"),
                              ("Save as…", self.save_as, "Ctrl+Shift+S"), ("Export PNG…", self.export_png, "Ctrl+E"),
                              ("Send to the Table", self.send_to_table, "Ctrl+T")):
            a = m.addAction(text)
            a.setShortcut(QKeySequence(key))
            a.triggered.connect(lambda _=False, f=fn: f())
        m.addSeparator()
        m.addAction("Close").triggered.connect(self.close)

    def icon_list(self, size=48):
        lw = QListWidget()
        lw.setViewMode(QListView.IconMode)
        lw.setIconSize(QSize(size, size))
        lw.setResizeMode(QListView.Adjust)
        lw.setMovement(QListView.Static)
        lw.setSpacing(4)
        lw.setWordWrap(True)
        return lw

    def build_palette(self):
        tabs = QTabWidget()
        # terrain
        self.terrain_list = self.icon_list()
        for t, name in TERRAIN.items():
            demo = MapData(3, 3, fill=t, seed=3)
            img = fd.render(demo, 24).copy(24, 24, 24, 24)
            it = QListWidgetItem(QIcon(QPixmap.fromImage(img)), name)
            it.setData(Qt.UserRole, t)
            self.terrain_list.addItem(it)
        self.terrain_list.itemClicked.connect(lambda it: (setattr(self, "terrain", it.data(Qt.UserRole)), self.set_tool("paint")
                                                          if self.tool not in ("paint", "room", "fill") else None))
        self.terrain_list.setCurrentRow(0)
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self.terrain_list, 1)
        v.addWidget(hint("Paint, Room (drag a rectangle) and Fill use this terrain. Walls appear by themselves "
                         "wherever floor meets rock; Erase carves rock back in."))
        tabs.addTab(w, "Terrain")
        # objects
        self.object_list = self.icon_list()
        self.fill_objects()
        self.object_list.itemClicked.connect(lambda it: (setattr(self, "object", it.data(Qt.UserRole)), self.set_tool("object")))
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self.object_list, 1)
        v.addWidget(hint("Doors, chests, torches and traps become working objects when you send the map to the table. "
                         "Traps are never drawn on the players' map."))
        tabs.addTab(w, "Objects")
        # chunks
        self.chunk_list = self.icon_list(64)
        self.chunk_list.itemClicked.connect(self.pick_chunk)
        self.fill_chunks()
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self.chunk_list, 1)
        v.addWidget(hrow(btn("⟳ Rotate (R)", self.rot), btn("⇋ Flip (F)", self.flp)))
        v.addWidget(hrow(btn("Save selection as chunk…", self.save_chunk), btn("Delete", self.delete_chunk)))
        v.addWidget(hint("Click a chunk, then click the map to stamp it. Blank parts of a chunk leave the map as it is."))
        tabs.addTab(w, "Chunks")
        # generate
        w = QWidget()
        v = QVBoxLayout(w)
        f = group("Map size", v)
        self.w_box, self.h_box = ispin(8, 120, self.m.w), ispin(8, 120, self.m.h)
        f.addRow("Width × height", hrow(self.w_box, self.h_box))
        f = group("Procedural generation", v)
        self.kind = combo(list(GENERATORS), "Dungeon", lambda k: self.pages.setCurrentIndex(list(GENERATORS).index(k)))
        f.addRow("Generator", self.kind)
        self.seed = ispin(0, 2 ** 31 - 1, self.m.seed % (2 ** 31))
        f.addRow("Seed", hrow(self.seed, btn("🎲", lambda: self.seed.setValue(int(time.time() * 1000) % (2 ** 31)), "New random seed")))
        self.pages, self.params = QStackedWidget(), {}
        for name, spec in (("Dungeon", [("rooms", "Rooms", 3, 30, 9), ("min_room", "Min room", 3, 12, 4), ("max_room", "Max room", 4, 16, 9),
                                        ("wide", "Corridor width", 1, 3, 1), ("loops", "Loops %", 0, 100, 25), ("prefabs", "Special rooms %", 0, 100, 35),
                                        ("deco", "Clutter %", 0, 100, 50)]),
                           ("Caves", [("fill", "Rock %", 35, 60, 46), ("smooth", "Smoothing", 1, 8, 5), ("lakes", "Lakes %", 0, 100, 30),
                                      ("lava", "Lava instead of water", 0, 1, 0), ("deco", "Clutter %", 0, 100, 50)]),
                           ("Wilderness", [("forest", "Forest %", 0, 100, 50), ("river", "River", 0, 1, 1), ("road", "Road", 0, 1, 1),
                                           ("deco", "Clutter %", 0, 100, 50)])):
            page = QWidget()
            pf = QFormLayout(page)
            self.params[name] = {}
            for key, label, lo, hi, val in spec:
                box = check(label, val, lambda _: None) if hi == 1 else ispin(lo, hi, val)
                pf.addRow(box) if hi == 1 else pf.addRow(label, box)
                self.params[name][key] = box
            self.pages.addWidget(page)
        f.addRow(self.pages)
        v.addWidget(hrow(btn("⚒ Forge whole map", lambda: self.generate(False)), btn("Forge into selection", lambda: self.generate(True))))
        v.addWidget(hint("Generate, then refine by hand: paint, stamp chunks, move things. Same seed = same map. "
                         "‘Forge into selection’ fills only the area picked with the Select tool."))
        v.addStretch()
        tabs.addTab(w, "Generate")
        d = QDockWidget("⚒ The Forge", self)
        d.setWidget(tabs)
        d.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        d.setMinimumWidth(330)
        self.addDockWidget(Qt.LeftDockWidgetArea, d)

    def load_brew(self):
        fd.CUSTOM.clear()
        fd.CUSTOM.update({o["id"]: o for o in brew.load()["objects"]})

    def fill_objects(self):
        self.object_list.clear()
        mine = [("brew:" + i, o["name"] + " ✦") for i, o in fd.CUSTOM.items()]  # ✦ = from the Brewery
        for k, name in [("", "(remove)")] + list(OBJECTS.items()) + mine:
            img = fd.object_image(k, 48) if k else QImage(48, 48, QImage.Format_ARGB32_Premultiplied)
            if not k:
                img.fill(Qt.transparent)
            it = QListWidgetItem(QIcon(QPixmap.fromImage(img)), name)
            it.setData(Qt.UserRole, k)
            self.object_list.addItem(it)

    def brew_changed(self):
        """The Brewery saved: pick up new or edited objects."""
        self.load_brew()
        self.fill_objects()
        self.full_render()

    def name_of(self, o):
        return fd.CUSTOM.get(o[5:], {}).get("name", "missing Brewery object") if o.startswith("brew:") else OBJECTS.get(o, o)

    def fill_chunks(self):
        self.chunk_list.clear()
        for i, c in enumerate(sorted(self.chunks, key=lambda c: (c["cat"], c["name"]))):
            img = fd.chunk_image(c["g"], 10)
            it = QListWidgetItem(QIcon(QPixmap.fromImage(img)), f"{c['name']}\n{c['cat']}")
            it.setData(Qt.UserRole, c)
            self.chunk_list.addItem(it)

    # ---------- rendering ----------
    def full_render(self):
        self.img = fd.render(self.m, CS, self.grid)
        self.canvas.item.setPixmap(QPixmap.fromImage(self.img))
        self.canvas.setSceneRect(QRectF(-CS * 4, -CS * 4, (self.m.w + 8) * CS, (self.m.h + 8) * CS))

    def redraw(self, x0, y0, x1, y1):
        p = QPainter(self.img)
        fd.region(p, self.m, CS, x0 - 1, y0 - 1, x1 + 1, y1 + 1, self.grid)  # +1: walls and edges of neighbours change too
        p.end()
        self.canvas.item.setPixmap(QPixmap.fromImage(self.img))

    def set_grid(self, on):
        self.grid = on
        self.full_render()

    def fit(self):
        self.canvas.fitInView(QRectF(0, 0, self.m.w * CS, self.m.h * CS), Qt.KeepAspectRatio)

    def overlay(self, p):
        h = self.canvas.hover
        gold = QPen(QColor("#e0b84f"), 2)
        gold.setCosmetic(True)
        if self.sel:
            x0, y0, x1, y1 = self.norm(self.sel)
            r = QRectF(x0 * CS, y0 * CS, (x1 - x0 + 1) * CS, (y1 - y0 + 1) * CS)
            dash = QPen(gold)
            dash.setStyle(Qt.DashLine)
            p.setPen(dash)
            p.setBrush(QColor(224, 184, 79, 40) if self.tool == "room" and self.start else Qt.NoBrush)
            p.drawRect(r)
        if h is None:
            return
        if self.tool == "chunk" and self.chunk_img is not None:
            ox, oy = self.chunk_origin(*h)
            p.setOpacity(0.7)
            p.drawImage(QPointF(ox * CS, oy * CS), self.chunk_img)
            p.setOpacity(1)
            p.setPen(gold)
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(ox * CS, oy * CS, self.chunk_img.width(), self.chunk_img.height()))
        elif self.tool in ("paint", "erase"):
            k = self.brush // 2
            p.setPen(gold)
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF((h[0] - k) * CS, (h[1] - k) * CS, self.brush * CS, self.brush * CS))
        else:
            p.setPen(gold)
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(h[0] * CS, h[1] * CS, CS, CS))

    def status(self, c):
        if self.m.inside(*c):
            o = self.m.o[c[1]][c[0]]
            self.statusBar().showMessage(f"{c[0]}, {c[1]}  ·  {TERRAIN[self.m.t[c[1]][c[0]]]}" + (f"  ·  {self.name_of(o)}" if o else ""))

    # ---------- editing ----------
    def set_tool(self, key):
        self.tool = key
        self.tool_acts[key].setChecked(True)
        if key != "select":
            self.sel = None if key != "room" else self.sel
        self.canvas.viewport().update()

    def push_undo(self):
        self.undo_stack.append(self.m.copy())
        del self.undo_stack[:-60]
        self.redo_stack.clear()
        self.dirty = True

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.m)
            self.m = self.undo_stack.pop()
            self.full_render()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.m)
            self.m = self.redo_stack.pop()
            self.full_render()

    @staticmethod
    def norm(s):
        x0, y0, x1, y1 = s
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

    def put(self, x, y, t=None, o=None):
        if not self.m.inside(x, y):
            return False
        if t is not None:
            self.m.t[y][x] = t
            if t == VOID or t in LIQUID:
                self.m.o[y][x] = ""
        if o is not None:
            self.m.o[y][x] = o
        return True

    def brush_at(self, x, y):
        k = self.brush // 2
        for yy in range(y - k, y - k + self.brush):
            for xx in range(x - k, x - k + self.brush):
                self.put(xx, yy, VOID if self.tool == "erase" else self.terrain)
        self.redraw(x - k, y - k, x - k + self.brush - 1, y - k + self.brush - 1)

    def line(self, a, b):
        (x0, y0), (x1, y1) = a, b
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        return [(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n)) for i in range(n + 1)]

    def press(self, x, y):
        t = self.tool
        if t in ("paint", "erase"):
            self.push_undo()
            self.brush_at(x, y)
            self.last = (x, y)
        elif t == "object":
            if self.m.inside(x, y):
                self.push_undo()
                self.put(x, y, o=self.object)
                if self.m.t[y][x] == VOID and self.object:  # objects need ground under them
                    self.m.t[y][x] = FLOOR
                self.redraw(x, y, x, y)
        elif t in ("room", "select"):
            self.start, self.sel = (x, y), (x, y, x, y)
        elif t == "fill":
            self.flood_fill(x, y)
        elif t == "chunk" and self.chunk:
            self.push_undo()
            ox, oy = self.chunk_origin(x, y)
            self.m.stamp(self.chunk, ox, oy)
            self.redraw(ox, oy, ox + len(self.chunk[0]) - 1, oy + len(self.chunk) - 1)
        elif t == "pick" and self.m.inside(x, y):
            self.terrain = self.m.t[y][x]
            self.object = self.m.o[y][x] or self.object
            self.set_tool("paint")
            self.statusBar().showMessage(f"Picked {TERRAIN[self.terrain]}", 3000)

    def drag(self, x, y):
        if self.tool in ("paint", "erase") and self.last and (x, y) != self.last:
            for c in self.line(self.last, (x, y))[1:]:
                self.brush_at(*c)
            self.last = (x, y)
        elif self.tool in ("room", "select") and self.start:
            self.sel = (*self.start, x, y)
            self.canvas.viewport().update()

    def release(self, x, y):
        if self.tool == "room" and self.start:
            self.push_undo()
            x0, y0, x1, y1 = self.norm((*self.start, x, y))
            for yy in range(y0, y1 + 1):
                for xx in range(x0, x1 + 1):
                    self.put(xx, yy, self.terrain)
            self.start, self.sel = None, None
            self.redraw(x0, y0, x1, y1)
        elif self.tool == "select":
            self.start = None
        self.last = None

    def flood_fill(self, x, y):
        if not self.m.inside(x, y):
            return
        old = self.m.t[y][x]
        if old == self.terrain:
            return
        self.push_undo()
        cells = self.m.flood(x, y, lambda a, b: self.m.t[b][a] == old)
        for cx, cy in cells:
            self.put(cx, cy, self.terrain)
        xs, ys = [c[0] for c in cells], [c[1] for c in cells]
        self.redraw(min(xs), min(ys), max(xs), max(ys))

    # ---------- chunks ----------
    def pick_chunk(self, it):
        self.chunk = it.data(Qt.UserRole)["g"]
        self.chunk_img = fd.chunk_image(self.chunk, CS)
        self.set_tool("chunk")

    def chunk_origin(self, x, y):
        return x - len(self.chunk[0]) // 2, y - len(self.chunk) // 2

    def rot(self):
        if self.chunk:
            self.chunk = rotate(self.chunk)
            self.chunk_img = fd.chunk_image(self.chunk, CS)
            self.canvas.viewport().update()

    def flp(self):
        if self.chunk:
            self.chunk = flip(self.chunk)
            self.chunk_img = fd.chunk_image(self.chunk, CS)
            self.canvas.viewport().update()

    def load_custom(self):
        try:
            with open(self.custom_file, encoding="utf-8") as f:
                data = json.load(f)
            return [dict(cat=c.get("cat", "My chunks"), name=c["name"], g=[[tuple(x) if x else None for x in row] for row in c["g"]], builtin=False)
                    for c in data]
        except (OSError, ValueError, KeyError):
            return []

    def store_custom(self):
        data = [dict(cat=c["cat"], name=c["name"], g=[[list(x) if x else None for x in row] for row in c["g"]])
                for c in self.chunks if not c.get("builtin")]
        with open(self.custom_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def save_chunk(self):
        if not self.sel:
            QMessageBox.information(self, "Save chunk", "Pick an area with the Select tool first.")
            return
        name, ok = QInputDialog.getText(self, "Save chunk", "Name for this chunk:")
        if not (ok and name.strip()):
            return
        x0, y0, x1, y1 = self.norm(self.sel)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(self.m.w - 1, x1), min(self.m.h - 1, y1)
        self.chunks.append(dict(cat="My chunks", name=name.strip(), g=self.m.grab(x0, y0, x1, y1), builtin=False))
        self.store_custom()
        self.fill_chunks()

    def delete_chunk(self):
        it = self.chunk_list.currentItem()
        c = it.data(Qt.UserRole) if it else None
        if not c or c.get("builtin"):
            QMessageBox.information(self, "Delete chunk", "Only your own chunks can be deleted.")
            return
        self.chunks = [x for x in self.chunks if x is not c and not (x["name"] == c["name"] and not x.get("builtin"))]
        self.store_custom()
        self.fill_chunks()

    # ---------- generation ----------
    def generate(self, into_selection):
        name = self.kind.currentText()
        kw = {k: (box.isChecked() if hasattr(box, "isChecked") and not hasattr(box, "value") else box.value())
              for k, box in self.params[name].items()}
        for k in ("loops", "prefabs", "deco", "forest", "lakes", "fill"):
            if k in kw:
                kw[k] /= 100
        seed = self.seed.value()
        if into_selection:
            if not self.sel:
                QMessageBox.information(self, "Forge", "Pick an area with the Select tool first.")
                return
            x0, y0, x1, y1 = self.norm(self.sel)
            x0, y0, x1, y1 = max(0, x0), max(0, y0), min(self.m.w - 1, x1), min(self.m.h - 1, y1)
            part = GENERATORS[name](x1 - x0 + 1, y1 - y0 + 1, seed, **kw)
            self.push_undo()
            self.m.paste(part, x0, y0)
            self.redraw(x0, y0, x1, y1)
        else:
            self.push_undo()
            self.m = GENERATORS[name](self.w_box.value(), self.h_box.value(), seed, **kw)
            self.full_render()
            self.fit()
        self.statusBar().showMessage(f"Forged a {name.lower()} (seed {seed}).", 5000)

    # ---------- files ----------
    def new_map(self):
        d = QDialog(self)
        d.setWindowTitle("New map")
        f = QFormLayout(d)
        w, h = ispin(8, 120, self.w_box.value()), ispin(8, 120, self.h_box.value())
        fill = combo([TERRAIN[t] for t in TERRAIN], TERRAIN[VOID])
        f.addRow("Width × height", hrow(w, h))
        f.addRow("Start with", fill)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        f.addRow(bb)
        if d.exec() and self.confirm_discard():
            t = next(k for k, v in TERRAIN.items() if v == fill.currentText())
            self.push_undo()
            self.m, self.path, self.dirty = MapData(w.value(), h.value(), fill=t), None, False
            self.full_render()
            self.fit()

    def maps_dir(self):
        d = os.path.join(self.data_dir, "maps")
        os.makedirs(d, exist_ok=True)
        return d

    def open_map(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open map", self.maps_dir(), "Forge map (*.dmap)")
        if p and self.confirm_discard():
            try:
                with open(p, encoding="utf-8") as f:
                    self.m = MapData.from_dict(json.load(f))
            except (OSError, ValueError, KeyError) as e:
                QMessageBox.warning(self, "Open", f"Couldn't open {p}: {e}")
                return
            self.path, self.dirty = p, False
            self.undo_stack.clear()
            self.full_render()
            self.fit()

    def save(self, path=None):
        path = path or self.path
        if not path:
            return self.save_as()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.m.to_dict(), f)
        os.replace(tmp, path)  # atomic: never leaves half a map behind
        self.path, self.dirty = path, False
        self.setWindowTitle(f"Map Forge — {os.path.basename(path)}")
        self.statusBar().showMessage(f"Saved {path}", 4000)
        return True

    def save_as(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save map", self.maps_dir(), "Forge map (*.dmap)")
        if p:
            return self.save(p if p.endswith(".dmap") else p + ".dmap")
        return False

    def confirm_discard(self):
        if not self.dirty:
            return True
        r = QMessageBox.question(self, "Map Forge", "Save changes to this map first?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        return r == QMessageBox.Discard or (r == QMessageBox.Save and bool(self.save()))

    def export_png(self):
        d = QDialog(self)
        d.setWindowTitle("Export PNG")
        f = QFormLayout(d)
        size = combo(["50", "70", "100", "140"], str(EXPORT_CS))
        grid = check("Draw grid lines", False, lambda _: None)
        traps = check("Include traps (DM copy)", False, lambda _: None)
        f.addRow("Pixels per square", size)
        f.addRow(grid)
        f.addRow(traps)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        f.addRow(bb)
        if not d.exec():
            return
        p, _ = QFileDialog.getSaveFileName(self, "Export PNG", self.maps_dir(), "PNG image (*.png)")
        if p:
            img = fd.render(self.m, int(size.currentText()), grid.isChecked(), () if traps.isChecked() else ("trap",))
            img.save(p if p.lower().endswith(".png") else p + ".png")
            self.statusBar().showMessage(f"Exported {p}", 5000)

    def table_package(self):
        """Renders the players' map (without live objects) and lists the live objects for the table."""
        base = os.path.splitext(os.path.basename(self.path))[0] if self.path else "forged"
        png = os.path.join(self.maps_dir(), f"{base}_{time.strftime('%Y%m%d_%H%M%S')}.png")
        mine = {o for row in self.m.o for o in row if o.startswith("brew:")}
        fd.render(self.m, EXPORT_CS, False, INTERACTIVE | mine).save(png)
        assets = os.path.join(self.data_dir, "forge_assets")
        os.makedirs(assets, exist_ok=True)
        img = {}

        def asset(kind, opened=False):
            if (kind, opened) not in img:
                path = os.path.join(assets, f"{kind}{'_open' if opened else ''}.png")
                if not os.path.exists(path):
                    fd.object_image(kind, 140, opened).save(path)
                img[(kind, opened)] = path
            return img[(kind, opened)]
        for kind, opened in (("door", False), ("door", True), ("chest", False), ("chest", True), ("torch", False)):
            asset(kind, opened)
        props = []
        for y in range(self.m.h):
            for x in range(self.m.w):
                k = self.m.o[y][x]
                pos = dict(x=(x + 0.5) * EXPORT_CS, y=(y + 0.5) * EXPORT_CS)
                if k == "door":
                    props.append(dict(pos, name="Door", img=img[("door", False)], alt_img=img[("door", True)], toggle=True,
                                      rotation=90 if fd.door_vertical(self.m, x, y) else 0))
                elif k == "chest":
                    props.append(dict(pos, name="Chest", img=img[("chest", False)], alt_img=img[("chest", True)], anim="glow"))
                elif k == "torch":
                    props.append(dict(pos, name="Torch", img=img[("torch", False)], light=rules.light("Torch")))
                elif k == "trap":
                    props.append(dict(pos, icon="trap", name="Trap", notes="Placed in Map Forge"))
                elif k in mine and k[5:] in fd.CUSTOM:
                    o = fd.CUSTOM[k[5:]]
                    props.append(dict(pos, name=o["name"], img=o["img"] or asset(o["base"]), cells=o["size"],
                                      alt_img=o["alt_img"] or (asset(o["base"], True) if o["toggle"] and not o["img"] and o["base"] in ("door", "chest") else ""),
                                      toggle=o["toggle"], light=o["light"], lit=o["lit"], sound=o["sound"], anim=o["anim"],
                                      hidden=o["hidden"], above=o["above"], notes=o["notes"]))
        return png, props

    def send_to_table(self):
        png, props = self.table_package()
        if self.launcher:
            self.launcher.send_to_table(png, EXPORT_CS, props)
        else:
            QMessageBox.information(self, "Map Forge", f"Map exported to {png}")

    def closeEvent(self, e):
        if not self.confirm_discard():
            e.ignore()
            return
        e.accept()
        self.closed.emit()
