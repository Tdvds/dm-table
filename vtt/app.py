"""Main window, the admin + player views, tool panels and campaign save/load."""
import base64, json, os, sys, time
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, QSettings, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QGuiApplication, QIcon, QImage, QKeySequence, QMovie, QPainter, QPainterPath, QPen, QPixmap, QTransform
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import (QApplication, QComboBox, QCompleter, QDockWidget, QFileDialog, QFrame, QGraphicsPixmapItem,
                               QGraphicsScene, QGraphicsView, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem,
                               QMainWindow, QMenu, QMessageBox, QScrollArea, QTabWidget, QVBoxLayout, QWidget)
from . import brew, icons, rules, theme
from .items import Fog, Grid, Lighting, Prop, Token, pix
from .dmtools import EncounterPanel, LootPanel, ReferencePanel
from .sounds import SoundsPanel
from .panels import (IMG_FILTER, KINDS, ColorButton, CombatPanel, Inspector, JournalPanel, btn, check, combo, group, hint,
                     hrow, ispin, slider, spin)
from .weather import ENVIRONMENTS, TYPES as WEATHER_TYPES, Weather

BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_EXT = {".mp4", ".webm", ".mkv", ".mov", ".avi", ".m4v", ".ogv"}
ANIM_EXT = {".gif", ".webp"}
MAP_FILTER = "Maps (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.mp4 *.webm *.mkv *.mov *.avi *.m4v *.ogv);;All files (*)"
BOARD = QRectF(-2000, -1500, 4000, 3000)
SPEEDS = {"1 min / sec": 1, "10 min / sec": 10, "1 hour / sec": 60}
HELP = """<b>Select tool</b> (1): drag creatures and objects; drag empty map to pan; wheel zooms.<br>
<b>Ctrl+wheel</b> resizes the selection, <b>Alt+wheel</b> turns objects, <b>Delete</b> removes.<br>
<b>Interact tool</b> (2) or <b>double-click</b>: open doors, pull levers, open chests, follow journal pins.<br>
<b>Reveal / Hide fog</b> (3, 4): paint the fog of war.<br>
<b>Right-click</b> the map to add creatures, lights, notes, traps and objects; right-click a thing for more.<br>
<b>N</b>: next turn in combat."""


def img_b64(img):
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return base64.b64encode(bytes(ba)).decode()


def b64_img(s):
    img = QImage()
    img.loadFromData(base64.b64decode(s))
    return img.convertToFormat(QImage.Format_ARGB32_Premultiplied)


def setup_view(v, admin):
    v.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    v.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    v.setFrameShape(QFrame.NoFrame)
    v.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    v.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)  # overlays cover the whole screen anyway
    v.viewport().setProperty("admin", admin)


class DisplayView(QGraphicsView):
    def __init__(self, app):
        super().__init__(app.scene)
        self.app = app
        setup_view(self, False)
        self.setInteractive(False)
        self.setBackgroundBrush(Qt.black)
        self.viewport().setCursor(Qt.BlankCursor)
        self.setWindowTitle("Player Display")

    def drawForeground(self, p, rect):
        p.save()
        p.resetTransform()
        vr = QRectF(self.viewport().rect())
        self.app.weather.paint(p, vr)
        self.app.paint_handout(p, vr)
        if self.app.blackout:
            p.fillRect(vr, Qt.black)
        p.restore()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.app.apply_view()


class AdminView(QGraphicsView):
    def __init__(self, app):
        super().__init__(app.scene)
        self.app, self.drag, self.mouse = app, None, None
        setup_view(self, True)
        self.setBackgroundBrush(QColor(18, 13, 10))
        self.setMouseTracking(True)  # for the fog brush outline

    def entity_at(self, pos):
        return next((i for i in self.items(pos) if isinstance(i, (Token, Prop))), None)

    def mousePressEvent(self, e):
        a, pos = self.app, e.position().toPoint()
        sp = self.mapToScene(pos)
        ent = self.entity_at(pos)
        if e.button() == Qt.RightButton:
            return a.context_menu(ent, sp, e.globalPosition().toPoint())
        if e.button() == Qt.MiddleButton:  # middle-drag pans whatever tool is active
            self.drag = ("pan", e.position())
            return
        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        if a.tool in ("reveal", "hide"):
            a.ensure_fog(a.tool == "reveal")
            self.drag = ("fog", sp)
            a.fog.stroke(sp, sp, a.brush_r(), a.tool == "reveal")
        elif a.tool == "interact" and isinstance(ent, Prop):
            a.trigger(ent)
        elif ent:
            super().mousePressEvent(e)  # Qt selects and drags it
        else:
            a.scene.clearSelection()
            self.drag = ("pan", e.position())

    def mouseDoubleClickEvent(self, e):
        ent = self.entity_at(e.position().toPoint())
        if isinstance(ent, Prop):
            self.app.trigger(ent)
        elif not ent:
            super().mouseDoubleClickEvent(e)

    def leaveEvent(self, e):
        self.mouse = None
        self.viewport().update()

    def mouseMoveEvent(self, e):
        self.mouse = e.position()
        if self.app.tool in ("reveal", "hide"):
            self.viewport().update()
        if not self.drag:
            return super().mouseMoveEvent(e)
        a, (kind, last) = self.app, self.drag
        if kind == "fog":
            p = self.mapToScene(e.position().toPoint())
            a.fog.stroke(last, p, a.brush_r(), a.tool == "reveal")
            self.drag = ("fog", p)
        else:
            d, k = e.position() - last, a.s * a.k
            a.center -= QPointF(d.x() / k, d.y() / k)
            self.drag = ("pan", e.position())
            a.apply_view()

    def mouseReleaseEvent(self, e):
        if self.drag:
            self.drag = None
        else:
            super().mouseReleaseEvent(e)

    def wheelEvent(self, e):
        a, d = self.app, e.angleDelta().y() or e.angleDelta().x()  # Alt turns the wheel horizontal on some systems
        sel, mods = [i for i in a.scene.selectedItems() if isinstance(i, (Token, Prop))], e.modifiers()
        if sel and mods & Qt.ControlModifier:
            for i in sel:
                i.cells = max(0.1, round(i.cells * (1.1 if d > 0 else 1 / 1.1), 2))
                i.refresh()
            a.inspector.reload()
        elif sel and mods & Qt.AltModifier:
            for i in sel:
                if isinstance(i, Prop):
                    i.rotation = (i.rotation + (15 if d > 0 else -15)) % 360
                    i.refresh()
            a.inspector.reload()
        else:
            a.zoom_at(self.mapToScene(e.position().toPoint()), 1.15 if d > 0 else 1 / 1.15)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            return self.app.delete(self.app.selected())
        if e.key() == Qt.Key_Escape:
            return self.app.set_tool("select")
        d = (100 if e.modifiers() & Qt.ShiftModifier else 15) / self.app.s
        mv = {Qt.Key_Left: (d, 0), Qt.Key_Right: (-d, 0), Qt.Key_Up: (0, d), Qt.Key_Down: (0, -d)}.get(e.key())
        if not mv:
            return super().keyPressEvent(e)
        self.app.center += QPointF(*mv)
        self.app.apply_view()

    def drawBackground(self, p, rect):
        super().drawBackground(p, rect)
        p.fillRect(self.app.display_rect(), Qt.black)  # players' area is black, like the real display

    def drawForeground(self, p, rect):
        a, vis = self.app, self.app.display_rect()
        path = QPainterPath()
        path.addRect(rect.united(vis))
        path.addRect(vis)  # odd-even fill: dims only what's outside the players' view
        p.fillPath(path, QColor(10, 7, 5, 170))
        pen = QPen(QColor(theme.GOLD), 2)
        pen.setCosmetic(True)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRect(vis)
        p.save()
        p.resetTransform()
        vr = QRectF(self.mapFromScene(vis).boundingRect())
        a.weather.paint(p, vr)
        a.paint_handout(p, vr)
        if a.blackout:
            p.fillRect(vr, QColor(0, 0, 0, 180))
            p.setPen(QColor(theme.GOLD))
            p.drawText(vr, Qt.AlignCenter, "BLACKOUT — players see nothing")
        if a.tool in ("reveal", "hide") and self.mouse is not None:  # brush outline, sized as on the player screen
            r = a.brush.value() * a.k
            p.setPen(QPen(QColor(theme.GOLD if a.tool == "reveal" else "#c0392b"), 1.5, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(self.mouse, r, r)
        if a.tool != "select":  # make the active mode impossible to miss
            text = {"interact": "☝ Interact: click objects to trigger them", "reveal": "☀ Reveal fog: paint to uncover",
                    "hide": "☁ Hide fog: paint to cover"}[a.tool] + "    ·    Esc = back to Select"
            box = QRectF(12, 12, p.fontMetrics().horizontalAdvance(text) + 24, 30)
            p.setPen(QPen(QColor(theme.GOLD), 1))
            p.setBrush(QColor(20, 14, 10, 225))
            p.drawRoundedRect(box, 6, 6)
            p.setPen(QColor(theme.PARCHMENT))
            p.drawText(box, Qt.AlignCenter, text)
        p.restore()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.app.apply_view()


class App(QMainWindow):
    closed = Signal()  # the launcher reappears when the table closes

    def __init__(self, data_dir=BASE, load_last=True):
        super().__init__()
        self.data_dir, self.campaign_path = data_dir, None
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-1e5, -1e5, 2e5, 2e5)  # large so centerOn is never clamped
        self.grid, self.fog, self.lighting = Grid(), Fog(self), Lighting(self)
        for it in (self.grid, self.fog, self.lighting):
            self.scene.addItem(it)
        self.tokens, self.props, self.journal = [], [], []
        self.library = {"tokens": [], "objects": []}
        self.loot_history, self.loot_tables, self.homebrew = [], {}, []
        self.map_item, self.map_path, self.movie, self.fit_pending = None, None, None, False
        self.player, self.audio = QMediaPlayer(), QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setLoops(-1)
        self.audio.setMuted(True)
        self.sfx, self.sfx_audio = QMediaPlayer(), QAudioOutput()
        self.sfx.setAudioOutput(self.sfx_audio)
        self.s, self.center, self.k = 1.0, QPointF(), 1.0
        self.tool, self.blackout, self.snap, self.handout = "select", False, True, None
        self.active_id, self.round, self.ruleset, self.follow, self.pc_hp = None, 0, "2024", True, True
        self.hour, self.auto_sky, self.advance, self.speed = 12.0, True, False, 10
        self.weather, self.animating, self.last = Weather(), set(), time.monotonic()
        self.admin, self.display = AdminView(self), DisplayView(self)
        self.map_sized()
        self.inspector, self.combat, self.journal_panel = Inspector(self), CombatPanel(self), JournalPanel(self)
        self.loot_panel, self.encounter_panel, self.reference_panel = LootPanel(self), EncounterPanel(self), ReferencePanel(self)
        self.sounds_panel = SoundsPanel(self)

        self.setWindowTitle("Dungeon Master's Table")
        self.setWindowIcon(icons.icon("table"))
        self.display.setWindowIcon(self.windowIcon())
        self.table_page = QMainWindow()  # the map page keeps its own side panels: the Realm and the Inspector
        self.table_page.setWindowFlags(Qt.Widget)
        self.table_page.setCentralWidget(self.admin)
        self.left_dock = self.dock("⚜ The Realm", QWidget(), Qt.LeftDockWidgetArea)
        self.inspector_dock = self.dock("⌕ Inspector", self.inspector, Qt.RightDockWidgetArea)
        self.table_page.resizeDocks([self.inspector_dock], [400], Qt.Horizontal)
        self.pages = QTabWidget()  # browser-style tabs: one full page per tool
        self.pages.setObjectName("pages")
        self.pages.setDocumentMode(True)
        for w, title in ((self.table_page, "🗺  Table"), (self.combat, "⚔  Combat"), (self.journal_panel, "✒  Journal"),
                         (self.encounter_panel, "⚖  Encounter"), (self.loot_panel, "⚱  Loot"), (self.reference_panel, "❦  Rules"),
                         (self.sounds_panel, "♫  Sounds")):
            self.pages.addTab(w, title)
        self.setCentralWidget(self.pages)
        self.build_toolbar()
        self.build_menus()
        self.statusBar().showMessage("Welcome, Dungeon Master.", 5000)
        self.scene.selectionChanged.connect(self.on_selection)
        QGuiApplication.instance().screenAdded.connect(self.fill_screens)
        QGuiApplication.instance().screenRemoved.connect(self.fill_screens)
        self.remember = load_last  # tests run with False so they never touch the real settings
        if load_last:
            last = QSettings("DMTable", "VTT").value("campaign", "")
            last = last if last and os.path.isfile(last) else os.path.join(data_dir, "campaign.json")
            if os.path.isfile(last):
                self.load_campaign(last)
        self.rebuild_left()
        self.resize(1600, 950)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)

    # ---------- layout ----------
    def dock(self, title, widget, area):
        d = QDockWidget(title, self.table_page)
        d.setObjectName(title)
        d.setWidget(widget)
        d.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.table_page.addDockWidget(area, d)
        return d

    def build_toolbar(self):
        tb = self.addToolBar("Tools")
        tb.setObjectName("Tools")
        tb.setMovable(False)
        grp, self.tool_acts = QActionGroup(self), {}
        for i, (key, label, tip) in enumerate((("select", "✋ Select", "Select, move, pan"), ("interact", "☝ Interact", "Click objects to trigger them"),
                                               ("reveal", "☀ Reveal fog", "Paint fog away"), ("hide", "☁ Hide fog", "Paint fog back"))):
            act = QAction(label, self, checkable=True, checked=i == 0, toolTip=f"{tip} ({i + 1})")
            act.setShortcut(QKeySequence(str(i + 1)))
            act.triggered.connect(lambda _=False, k=key: self.set_tool(k))
            grp.addAction(act)
            tb.addAction(act)
            self.tool_acts[key] = act
        tb.addWidget(QLabel("  Brush "))
        self.brush = slider(10, 400, 80)
        self.brush.setFixedWidth(110)
        tb.addWidget(self.brush)
        tb.addSeparator()
        self.act(tb, "⤢ Fit", self.fit)
        self.zoom_label = QLabel(" 100% ")
        tb.addWidget(self.zoom_label)
        tb.addSeparator()
        self.act(tb, "▣ Show display", self.show_display)
        self.blackout_act = QAction("■ Blackout", self, checkable=True)
        self.blackout_act.toggled.connect(self.set_blackout)
        tb.addAction(self.blackout_act)
        self.act(tb, "✉ Hide handout", lambda: self.show_handout(None))
        tb.addSeparator()
        nxt = QAction("⚔ Next turn", self, shortcut=QKeySequence("N"))
        nxt.triggered.connect(self.combat.next_turn)
        tb.addAction(nxt)

    def set_tool(self, key):
        self.tool = key
        self.tool_acts[key].setChecked(True)
        self.admin.viewport().update()

    def act(self, bar, text, fn):
        a = QAction(text, self)
        a.triggered.connect(lambda _=False: fn())
        bar.addAction(a)
        return a

    def build_menus(self):
        m = self.menuBar().addMenu("&Campaign")
        for text, fn, key in (("New", self.new_campaign, "Ctrl+N"), ("Open…", self.open_dialog, "Ctrl+O"),
                              ("Save", self.save_campaign, "Ctrl+S"), ("Save as…", self.save_as, "Ctrl+Shift+S")):
            act = m.addAction(text)
            act.triggered.connect(lambda _=False, f=fn: f())
            act.setShortcut(QKeySequence(key))
        m.addSeparator()
        m.addAction("Quit").triggered.connect(self.close)
        v = self.menuBar().addMenu("&View")
        for d in (self.left_dock, self.inspector_dock):
            v.addAction(d.toggleViewAction())
        v.addSeparator()
        for i in range(self.pages.count()):  # Ctrl+1..6 jump between the tabs, like a browser
            act = v.addAction(self.pages.tabText(i).split(maxsplit=1)[-1])
            act.setShortcut(QKeySequence(f"Ctrl+{i + 1}"))
            act.triggered.connect(lambda _=False, i=i: self.pages.setCurrentIndex(i))
        self.menuBar().addMenu("&Help").addAction("Controls").triggered.connect(
            lambda: QMessageBox.information(self, "Controls", HELP))

    def rebuild_left(self):
        old = self.left_dock.widget()
        idx = old.currentIndex() if isinstance(old, QTabWidget) else 0
        tabs = QTabWidget()
        for title, build in (("Map", self.tab_map), ("Place", self.tab_place), ("Light", self.tab_light),
                             ("Weather", self.tab_weather), ("Rules", self.tab_rules)):
            w = QWidget()
            v = QVBoxLayout(w)
            build(v)
            v.addStretch()
            sc = QScrollArea()
            sc.setWidget(w)
            sc.setWidgetResizable(True)
            sc.setFrameShape(QFrame.NoFrame)
            tabs.addTab(sc, title)
        tabs.setCurrentIndex(idx)
        tabs.setMinimumWidth(330)
        self.left_dock.setWidget(tabs)
        old.deleteLater()
        self.fill_screens()

    def tab_map(self, v):
        f = group("Battle map", v)
        self.map_label = QLabel(os.path.basename(self.map_path or "") or "(none)")
        f.addRow(self.map_label)
        f.addRow(btn("Open map (image, GIF or video)…", self.pick_map))
        f.addRow(check("Mute video sound", self.audio.isMuted(), self.audio.setMuted))
        f = group("Player display", v)
        self.screen_box = QComboBox()
        f.addRow("Screen", self.screen_box)
        f.addRow(hrow(btn("Show", self.show_display), btn("Hide", self.display.hide), btn("Fit map", self.fit)))
        g = self.grid
        f = group("Grid", v)
        f.addRow(check("Show grid", g.on, lambda on: self.set_grid("on", on)))
        f.addRow("Cell size", spin(5, 2000, g.size, 0.5, 1, lambda x: self.set_grid("size", x)))
        f.addRow("Offset", hrow(spin(-2000, 2000, g.ox, 0.5, 1, lambda x: self.set_grid("ox", x)),
                                spin(-2000, 2000, g.oy, 0.5, 1, lambda x: self.set_grid("oy", x))))
        f.addRow("Colour", hrow(ColorButton(g.color, lambda c: self.set_grid("color", c)),
                                slider(0, 100, int(g.alpha * 100), lambda x: self.set_grid("alpha", x / 100))))
        f.addRow(check("Snap creatures to grid", self.snap, lambda on: setattr(self, "snap", on)))
        f = group("Fog of war", v)
        self.w_fog = check("Enabled", self.fog.on, lambda on: (setattr(self.fog, "on", on), self.fog.update()))
        f.addRow(self.w_fog)
        f.addRow(hrow(btn("Cover all", lambda: self.fog.fill(True)), btn("Reveal all", lambda: self.fog.fill(False))))
        f.addRow(hint("Paint it with the Reveal / Hide fog tools. You see through it; players don't."))

    def tab_place(self, v):
        f = group("New creature", v)
        self.q_name = QLineEdit("Goblin")
        self.q_kind = combo(KINDS, "enemy")
        self.q_hp, self.q_ac, self.q_init = ispin(1, 9999, 7), ispin(0, 40, 15), ispin(-10, 20, 2)
        self.q_size, self.q_color = spin(0.25, 20, 1, 0.25, 2), ColorButton("#5a1a1a")
        self.q_cr = QLineEdit("1/4")
        self.q_cr.setToolTip("Challenge rating for monsters, character level for PCs")
        self.beasts = QComboBox()
        self.beasts.setEditable(True)
        self.beasts.setInsertPolicy(QComboBox.NoInsert)
        self.beasts.completer().setFilterMode(Qt.MatchContains)  # type any part of the name
        self.beasts.completer().setCompletionMode(QCompleter.PopupCompletion)
        for label, mon in brew.bestiary():
            self.beasts.addItem(label, mon)
        self.beasts.setCurrentIndex(-1)
        self.beasts.lineEdit().setPlaceholderText("Search monsters…")
        self.lib_widgets = {}
        f.addRow("Image", self.lib_list("tokens"))
        f.addRow(hrow(btn("Add images…", lambda: self.lib_add("tokens")), btn("Remove", lambda: self.lib_remove("tokens")),
                      btn("No image", lambda: self.lib_widgets["tokens"].clearSelection())))
        f.addRow("Monster", hrow(self.beasts, btn("Place monster", self.place_beast)))
        f.addRow(hint("Click an image first to use it for the next creature. Type to search monsters, then press Place monster "
                      "(✦ = your Brewery homebrew). Or build one below:"))
        f.addRow("Name", self.q_name)
        f.addRow("Side", self.q_kind)
        f.addRow("HP / AC", hrow(self.q_hp, self.q_ac))
        f.addRow("Init mod / size", hrow(self.q_init, self.q_size))
        f.addRow("CR (or PC level)", self.q_cr)
        f.addRow("Colour", self.q_color)
        f.addRow(btn("✚ Add creature", lambda: self.add_token(self.quick_token(), select=True)))
        f = group("Objects", v)
        objs = self.lib_list("objects")
        objs.itemDoubleClicked.connect(lambda it: self.add_prop({"img": it.data(Qt.UserRole), "name": stem(it.data(Qt.UserRole))}, select=True))
        f.addRow(objs)
        f.addRow(hrow(btn("Add images…", lambda: self.lib_add("objects")), btn("Remove", lambda: self.lib_remove("objects"))))
        f.addRow(hint("Double-click to place. Ctrl+wheel resizes, Alt+wheel turns."))
        f = group("DM-only markers", v)
        f.addRow(hrow(btn("☀ Light", lambda: self.add_prop({"icon": "light", "name": "Torch", "light": rules.light("Torch")}, select=True)),
                      btn("✎ Note", lambda: self.add_prop({"icon": "note", "name": "Note"}, select=True)),
                      btn("☠ Trap", lambda: self.add_prop({"icon": "trap", "name": "Trap"}, select=True)),
                      btn("⚑ Pin", lambda: self.add_prop({"icon": "pin", "name": "Pin"}, select=True))))

    def tab_light(self, v):
        L = self.lighting
        f = group("Dynamic lighting", v)
        self.w_light = check("Enabled", L.enabled, self.set_lighting)
        f.addRow(self.w_light)
        f = group("Time of day", v)
        self.w_hour_label = QLabel()
        self.w_hour = slider(0, 96, int(self.hour * 4), lambda x: (self.set_lighting(True), self.set_hour(x / 4)))
        f.addRow(self.w_hour_label)
        f.addRow(self.w_hour)
        self.w_auto = check("Sky follows the time of day", self.auto_sky, lambda on: (setattr(self, "auto_sky", on), self.set_hour(self.hour)))
        f.addRow(self.w_auto)
        f.addRow(hrow(check("Time passes", self.advance, lambda on: setattr(self, "advance", on)),
                      combo(list(SPEEDS), next((k for k, s in SPEEDS.items() if s == self.speed), "10 min / sec"),
                            lambda k: setattr(self, "speed", SPEEDS[k]))))
        f = group("Darkness", v)
        self.w_dark = slider(0, 100, int(L.darkness * 100), self.set_darkness)
        self.w_tint = ColorButton(L.tint, self.set_tint)
        f.addRow("Darkness", self.w_dark)
        f.addRow("Tint", self.w_tint)
        f.addRow(hint("Torches and magic: select a creature or object and pick a Light in the Inspector, "
                      "or place a ☀ Light marker. Lights flicker, glow in colour and cut through the dark."))
        self.set_hour(self.hour)

    def tab_weather(self, v):
        W = self.weather
        f = group("Weather", v)
        self.w_weather = combo(WEATHER_TYPES, W.kind, self.set_weather)
        self.w_intensity = slider(5, 100, int(W.intensity * 100), lambda x: setattr(W, "intensity", x / 100))
        f.addRow("Effect", self.w_weather)
        f.addRow("Intensity", self.w_intensity)
        f.addRow("Wind", slider(-100, 100, int(W.wind * 100), lambda x: setattr(W, "wind", x / 100)))
        f = group("Environments", v)
        names = list(ENVIRONMENTS)
        for i in range(0, len(names), 2):
            f.addRow(hrow(*(btn(n, lambda n=n: self.set_weather(*ENVIRONMENTS[n])) for n in names[i:i + 2])))
        f.addRow(hint("Objects can change the weather when triggered (Inspector → Sets weather)."))

    def tab_rules(self, v):
        f = group("Rules", v)
        rs = QComboBox()
        rs.addItem("2024 rules (5.5e)", "2024")
        rs.addItem("2014 rules (5e)", "2014")
        rs.setCurrentIndex(rs.findData(self.ruleset))
        rs.currentIndexChanged.connect(lambda i: self.set_ruleset(rs.itemData(i)))
        f.addRow("Edition", rs)
        f.addRow(check("Camera follows whose turn it is", self.follow, lambda on: setattr(self, "follow", on)))
        f.addRow(check("Players see PC hit points", self.pc_hp, lambda on: (setattr(self, "pc_hp", on), self.scene.update())))
        f = group("Controls", v)
        lab = QLabel(HELP)
        lab.setWordWrap(True)
        f.addRow(lab)

    # ---------- view math: display shows the scene at scale s around center; admin shows the same, shrunk by k ----------
    def display_rect(self):
        vp = self.display.viewport()
        w, h = vp.width() / self.s, vp.height() / self.s
        return QRectF(self.center.x() - w / 2, self.center.y() - h / 2, w, h)

    def apply_view(self):
        if not hasattr(self, "display"):
            return
        dv, av = self.display.viewport(), self.admin.viewport()
        self.k = min(av.width() / max(1, dv.width()), av.height() / max(1, dv.height()))
        for view, sc in ((self.display, self.s), (self.admin, self.s * self.k)):
            view.setTransform(QTransform.fromScale(sc, sc))
            view.centerOn(self.center)
        av.update()
        if hasattr(self, "zoom_label"):
            self.zoom_label.setText(f" {self.s * 100:.0f}% ")

    def zoom_at(self, p, f):
        ns = min(50.0, max(0.02, self.s * f))
        self.center = p - (p - self.center) * (self.s / ns)  # keeps p at the same spot on the display
        self.s = ns
        self.apply_view()

    def fit(self):
        r, vp = self.map_rect(), self.display.viewport()
        if r.isEmpty():
            return
        self.s = min(vp.width() / r.width(), vp.height() / r.height())
        self.center = r.center()
        self.apply_view()

    def brush_r(self):
        return self.brush.value() / self.s  # brush size is in display pixels

    def snapped(self, pos, cells):
        g, off = self.grid, 0.5 if round(cells) % 2 == 1 else 0  # odd sizes sit in cell centres, even ones on corners
        f = lambda v, o: o + (round((v - o) / g.size - off) + off) * g.size
        return QPointF(f(pos.x(), g.ox), f(pos.y(), g.oy))

    # ---------- map ----------
    def map_rect(self):
        return self.map_item.mapRectToScene(self.map_item.boundingRect()) if self.map_item else QRectF()

    def clear_map(self):
        self.player.stop()
        if self.movie:
            self.movie.stop()
            self.movie = None
        if self.map_item:
            self.scene.removeItem(self.map_item)
            self.map_item = None

    def open_map(self, path, fit=True):
        self.clear_map()
        ext = os.path.splitext(path)[1].lower()
        if ext in VIDEO_EXT:
            item = QGraphicsVideoItem()
            item.nativeSizeChanged.connect(lambda sz: (item.setSize(sz), self.map_sized()))
            self.player.setVideoOutput(item)
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()
        elif ext in ANIM_EXT:
            m = self.movie = QMovie(path)
            item = QGraphicsPixmapItem()
            m.frameChanged.connect(lambda _: item.setPixmap(m.currentPixmap()))
            m.jumpToFrame(0)
            item.setPixmap(m.currentPixmap())
            m.start()
        else:
            item = QGraphicsPixmapItem(QPixmap(path))
        if ext not in VIDEO_EXT and item.boundingRect().isEmpty():
            QMessageBox.warning(self, "Map", f"Can't open {path}")
            return
        if isinstance(item, QGraphicsPixmapItem):
            item.setTransformationMode(Qt.SmoothTransformation)
        self.scene.addItem(item)
        self.map_item, self.map_path, self.fit_pending = item, path, fit
        if hasattr(self, "map_label"):
            self.map_label.setText(os.path.basename(path))
        if ext not in VIDEO_EXT:
            self.map_sized()  # video calls this once its real size is known
        self.journal_panel.fill()

    def board_rect(self):
        r = self.map_rect()
        return r if not r.isEmpty() else BOARD  # fog, light and grid still work before a map is loaded

    def map_sized(self):
        r = self.board_rect()
        self.grid.set_rect(r)
        self.fog.set_rect(r)  # resets fog only if the map size changed
        self.lighting.set_rect(r)
        if self.fit_pending:
            self.fit_pending = False
            self.fit()

    def pick_map(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open map", "", MAP_FILTER)
        if path:
            self.fog.rect = QRectF()  # force fresh fog for a new map
            self.open_map(path)

    # ---------- player display ----------
    def fill_screens(self, *_):
        self.screens = QGuiApplication.screens()
        if not hasattr(self, "screen_box"):
            return
        primary = QGuiApplication.primaryScreen()
        self.screen_box.clear()
        for i, s in enumerate(self.screens):
            g = s.geometry()
            self.screen_box.addItem(f"{i + 1}: {g.width()}×{g.height()}{' (main)' if s is primary else ''}")
        self.screen_box.setCurrentIndex(next((i for i, s in enumerate(self.screens) if s is not primary), 0))

    def show_display(self):
        d = self.display
        if len(self.screens) == 1:  # one monitor: a normal window so you can still test
            d.setWindowFlags(Qt.Window)
            d.resize(1280, 720)
            d.showNormal()
            return
        scr = self.screens[self.screen_box.currentIndex()]
        d.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        d.setGeometry(scr.geometry())
        d.show()  # must be shown on the target screen first, else fullscreen lands on the primary
        d.windowHandle().setScreen(scr)
        d.showFullScreen()

    def set_blackout(self, on):
        self.blackout = on
        self.scene.update()

    def show_handout(self, path):
        self.handout = path or None
        self.scene.update()

    def paint_handout(self, p, rect):
        pm = pix(self.handout)
        if not pm:
            return
        p.fillRect(rect, QColor(0, 0, 0, 215))
        k = min(rect.width() * 0.86 / pm.width(), rect.height() * 0.86 / pm.height())
        w, h = pm.width() * k, pm.height() * k
        target = QRectF(rect.center().x() - w / 2, rect.center().y() - h / 2, w, h)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(target, pm, QRectF(pm.rect()))
        p.setPen(QPen(QColor(theme.GOLD), max(2.0, rect.height() / 250)))
        p.setBrush(Qt.NoBrush)
        p.drawRect(target.adjusted(-4, -4, 4, 4))

    # ---------- creatures & objects ----------
    def entities(self):
        return self.tokens + self.props

    def selected(self):
        return [i for i in self.scene.selectedItems() if isinstance(i, (Token, Prop))]

    def unique_name(self, base):
        names, n = {t.name for t in self.tokens}, 2
        if base not in names:
            return base
        while f"{base} {n}" in names:
            n += 1
        return f"{base} {n}"

    def quick_token(self):
        hp = self.q_hp.value()
        return {"name": self.unique_name(self.q_name.text().strip() or "Creature"), "kind": self.q_kind.currentText(),
                "hp": hp, "max_hp": hp, "ac": self.q_ac.value(), "init_mod": self.q_init.value(),
                "cells": self.q_size.value(), "color": self.q_color.color, "img": self.chosen_img(),
                **({"level": int(self.q_cr.text())} if self.q_kind.currentText() == "pc" and self.q_cr.text().isdigit()
                   else {"cr": self.q_cr.text().strip() or "0"})}

    def place(self, e, at, select):
        pos = at if at is not None else self.center
        if at is None and isinstance(e, Token):  # step to the next free square instead of stacking on the last one
            for _ in range(60):
                if not any(t is not e and (t.pos() - pos).manhattanLength() < self.grid.size * 0.5 for t in self.tokens):
                    break
                pos += QPointF(self.grid.size, 0)
        e.setPos(self.snapped(pos, e.cells) if self.snap and isinstance(e, Token) else pos)
        self.scene.addItem(e)
        if select:
            self.scene.clearSelection()
            e.setSelected(True)
        self.lighting.dirty = True
        self.combat.refresh()
        self.loot_panel.refresh()
        return e

    def add_token(self, data, at=None, select=False):
        t = Token(self, data)
        self.tokens.append(t)
        return self.place(t, at, select)

    def add_prop(self, data, at=None, select=False):
        p = Prop(self, data)
        self.props.append(p)
        return self.place(p, at, select)

    def duplicate(self, e):
        d = e.to_dict()
        d["id"] = ""
        if isinstance(e, Token):
            d["name"], d["in_combat"], d["init"] = self.unique_name(e.name.rstrip("0123456789 ") or e.name), False, None
            return self.add_token(d, e.pos() + QPointF(self.grid.size, 0), True)
        return self.add_prop(d, e.pos() + QPointF(self.grid.size, 0), True)

    def delete(self, items):
        for e in items:
            (self.tokens if isinstance(e, Token) else self.props).remove(e)
            self.scene.removeItem(e)
            if e.id == self.active_id:
                self.active_id = None
        if items:
            self.inspector.set_target(None)
            self.combat.refresh()
            self.lighting.dirty = True

    def reveal_tag(self, tag):
        n = 0
        for e in self.entities():
            if e.tag == tag:
                e.hidden = not e.hidden
                if not e.hidden:
                    self.fog.clear_rect(e.sceneBoundingRect())  # secret passage appears: lift the fog over it too
                e.refresh()
                n += 1
        return n

    def trigger(self, prop):
        self.statusBar().showMessage(prop.trigger(), 5000)
        if self.inspector.target is prop:
            self.inspector.reload()

    def on_entity_changed(self, e):
        self.lighting.dirty = True
        self.combat.refresh()
        if isinstance(e, Token):
            self.loot_panel.refresh()  # PC names feed the 'give to' list

    def on_selection(self):
        try:
            sel = self.selected()
        except RuntimeError:  # Qt fires this while tearing the scene down at exit
            return
        self.inspector.set_target(sel[0] if len(sel) == 1 else None)

    def context_menu(self, ent, sp, gp):
        m = QMenu(self)

        def add(menu, text, fn):
            menu.addAction(text).triggered.connect(lambda _=False: fn())
        if ent:
            if isinstance(ent, Prop):
                add(m, "☝ Trigger", lambda: self.trigger(ent))
            add(m, "Reveal to players" if ent.hidden else "Hide from players",
                lambda: (setattr(ent, "hidden", not ent.hidden), ent.refresh(), self.inspector.reload()))
            if isinstance(ent, Token):
                add(m, "Remove from initiative" if ent.in_combat else "⚔ Add to initiative", lambda: self.combat.toggle(ent))
            add(m, "Duplicate", lambda: self.duplicate(ent))
            add(m, "Delete", lambda: self.delete([ent]))
        else:
            add(m, "✚ Add creature here", lambda: self.add_token(self.quick_token(), sp, True))
            lm = m.addMenu("☀ Add light here")
            for name in rules.LIGHTS:
                add(lm, name, lambda n=name: self.add_prop({"icon": "light", "name": n, "light": rules.light(n)}, sp, True))
            add(m, "✎ Add DM note here", lambda: self.add_prop({"icon": "note", "name": "Note"}, sp, True))
            add(m, "☠ Add trap here", lambda: self.add_prop({"icon": "trap", "name": "Trap"}, sp, True))
            bm = m.addMenu("☠ Bestiary creature here")
            for label, mon in brew.bestiary():
                add(bm, label, lambda mon=mon: self.add_beast(mon, sp))
            om = m.addMenu("▤ Place object here")
            om.setEnabled(bool(self.library["objects"]))
            for path in self.library["objects"]:
                add(om, stem(path), lambda p=path: self.add_prop({"img": p, "name": stem(p)}, sp, True))
        m.exec(gp)

    # ---------- libraries ----------
    def lib_list(self, kind):
        lw = QListWidget()
        lw.setViewMode(QListView.IconMode)
        lw.setIconSize(QSize(56, 56))
        lw.setResizeMode(QListView.Adjust)
        lw.setMovement(QListView.Static)
        lw.setMinimumHeight(140)
        self.lib_widgets[kind] = lw
        self.fill_lib(kind)
        return lw

    def chosen_img(self):
        """The creature image clicked in Place → New creature, or '' to keep the creature's own."""
        it = self.lib_widgets["tokens"].currentItem()
        return it.data(Qt.UserRole) if it and it.isSelected() else ""

    def fill_lib(self, kind):
        lw = self.lib_widgets[kind]
        lw.clear()
        for path in self.library[kind]:
            it = QListWidgetItem(QIcon(path), stem(path))
            it.setData(Qt.UserRole, path)
            it.setToolTip(path)
            lw.addItem(it)

    def lib_add(self, kind):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add images", "", IMG_FILTER)
        self.library[kind] += [p for p in paths if p not in self.library[kind]]
        self.fill_lib(kind)

    def lib_remove(self, kind):
        it = self.lib_widgets[kind].currentItem()
        if it:
            self.library[kind].remove(it.data(Qt.UserRole))
            self.fill_lib(kind)

    def place_beast(self):
        i = self.beasts.findText(self.beasts.currentText())
        if i < 0:
            self.statusBar().showMessage("Pick a monster from the list first.", 4000)
            return
        self.add_beast(self.beasts.itemData(i), img=self.chosen_img())

    def add_beast(self, mon, at=None, img=""):
        d = brew.token(mon)
        d["name"] = self.unique_name(d["name"])
        if img:  # the picked image replaces the monster's own
            d["img"] = img
        return self.add_token(d, at, select=True)

    def open_brewery(self, kind, eid=None, new=False):
        launcher = getattr(self, "launcher", None)
        if launcher is None:
            self.statusBar().showMessage("Start from the launcher to open the Brewery.", 5000)
            return None
        b = launcher.open_brewery()
        b.focus(kind, eid, new)
        return b

    def brew_changed(self):
        """The Brewery saved: refresh the bestiary and the rules reference."""
        self.rebuild_left()
        self.reference_panel.search()

    def set_grid(self, key, val):
        for e in self.entities():
            e.prepareGeometryChange()  # sizes are in grid cells
        setattr(self.grid, key, val)
        self.grid.update()
        self.lighting.dirty = True

    # ---------- sound, weather, light, journal ----------
    def play_sound(self, path):
        self.sfx.setSource(QUrl.fromLocalFile(path))
        self.sfx.play()

    def set_weather(self, kind, intensity=None):
        self.weather.set(kind)
        if intensity is not None:
            self.weather.intensity = intensity
        for w, val in ((getattr(self, "w_weather", None), kind), (getattr(self, "w_intensity", None), int(self.weather.intensity * 100))):
            if w:
                w.blockSignals(True)
                w.setCurrentText(val) if isinstance(w, QComboBox) else w.setValue(val)
                w.blockSignals(False)
        self.scene.update()

    def set_lighting(self, on):
        self.lighting.enabled = on
        self.lighting.dirty = True
        self.lighting.update()
        w = getattr(self, "w_light", None)
        if w and w.isChecked() != on:
            w.blockSignals(True)
            w.setChecked(on)
            w.blockSignals(False)

    def ensure_fog(self, reveal):
        """Using a fog brush switches fog on. Fresh fog starts fully covered for Reveal, clear for Hide."""
        if self.fog.on:
            return
        if not self.fog.touched:
            self.fog.fill(reveal)
        self.fog.on = True
        w = getattr(self, "w_fog", None)
        if w:
            w.blockSignals(True)
            w.setChecked(True)
            w.blockSignals(False)

    def set_darkness(self, x):
        self.set_lighting(True)  # moving the darkness slider should always show darkness
        self.lighting.darkness = x / 100
        self.lighting.dirty = True
        if self.auto_sky:  # touching the manual slider takes over from the clock
            self.auto_sky = False
            self.w_auto.setChecked(False)

    def set_tint(self, c):
        self.lighting.tint = c
        self.lighting.dirty = True

    def set_hour(self, h):
        self.hour = h % 24
        if self.auto_sky:
            self.lighting.darkness, self.lighting.tint = rules.sky(self.hour)
            self.lighting.dirty = True
        if hasattr(self, "w_hour"):
            for w in (self.w_hour, self.w_dark):
                w.blockSignals(True)
            self.w_hour.setValue(int(self.hour * 4))
            self.w_dark.setValue(int(self.lighting.darkness * 100))
            for w in (self.w_hour, self.w_dark):
                w.blockSignals(False)
            self.w_tint.set_color(self.lighting.tint)
            self.w_hour_label.setText(f"{int(self.hour):02d}:{int(self.hour % 1 * 60):02d}  ·  {rules.time_name(self.hour)}")

    def set_ruleset(self, rs):
        self.ruleset = rs
        for e in self.entities():
            e.refresh()
        self.inspector.reload()

    def open_entry(self, eid):
        self.pages.setCurrentWidget(self.journal_panel)
        self.journal_panel.select(eid)

    # ---------- animation clock ----------
    def tick(self):
        now = time.monotonic()
        dt, self.last = min(0.1, now - self.last), now
        if self.advance:
            self.set_hour(self.hour + dt * self.speed / 60)
        self.weather.step(dt)
        L = self.lighting
        if L.enabled and (L.dirty or self.advance or L.flickers()):
            L.rebuild(now)
        for e in list(self.animating):
            if now - e.anim_t > 1.3:
                self.animating.discard(e)
            e.update()
        if self.weather.kind != "None":
            self.display.viewport().update()
            self.admin.viewport().update()

    # ---------- campaign files ----------
    def to_state(self):
        r, L, W = self.map_rect(), self.lighting, self.weather
        return dict(
            version=2, map=self.map_path, map_rect=[r.x(), r.y(), r.width(), r.height()], s=self.s,
            center=[self.center.x(), self.center.y()], muted=self.audio.isMuted(),
            grid={k: getattr(self.grid, k) for k in Grid.KEYS}, fog_on=self.fog.on,
            fog=None if self.fog.img.isNull() else img_b64(self.fog.img),
            lighting=dict(enabled=L.enabled, darkness=L.darkness, tint=L.tint, hour=self.hour, auto_sky=self.auto_sky,
                          advance=self.advance, speed=self.speed),
            weather=dict(kind=W.kind, intensity=W.intensity, wind=W.wind),
            tokens=[t.to_dict() for t in self.tokens], props=[p.to_dict() for p in self.props], journal=self.journal,
            library=self.library, loot_history=self.loot_history, loot_tables=self.loot_tables, homebrew=self.homebrew, sounds=self.sounds_panel.state(),
            combat=dict(active=self.active_id, round=self.round),
            rules=dict(ruleset=self.ruleset, follow=self.follow, pc_hp=self.pc_hp, snap=self.snap))

    def from_state(self, st):
        self.delete(self.entities())
        self.clear_map()
        self.map_path = None
        self.fog.prepareGeometryChange()
        self.fog.rect, self.fog.img = QRectF(), QImage()
        for k, v in st.get("grid", {}).items():
            if k in Grid.KEYS:
                setattr(self.grid, k, v)
        self.s, self.center = st.get("s", 1.0), QPointF(*st.get("center", [0, 0]))
        self.audio.setMuted(st.get("muted", True))
        if st.get("map") and os.path.isfile(st["map"]):
            self.open_map(st["map"], fit=False)
            r = QRectF(*st["map_rect"])
            for it in (self.grid, self.lighting):
                it.set_rect(r)
            self.fog.prepareGeometryChange()
            self.fog.rect = r
            if st.get("fog"):
                self.fog.img, self.fog.touched = b64_img(st["fog"]), True
            else:
                self.fog.fill(True, touched=False)
        else:
            self.map_sized()
        self.fog.on = st.get("fog_on", False)
        L, lt = self.lighting, st.get("lighting", {})
        L.enabled, L.darkness, L.tint = lt.get("enabled", False), lt.get("darkness", 0.0), lt.get("tint", "#0a1030")
        self.hour, self.auto_sky = lt.get("hour", 12.0), lt.get("auto_sky", True)
        self.advance, self.speed = lt.get("advance", False), lt.get("speed", 10)
        wt = st.get("weather", {})
        self.weather.set(wt.get("kind", "None"))
        self.weather.intensity, self.weather.wind = wt.get("intensity", 0.6), wt.get("wind", 0.2)
        ru = st.get("rules", {})
        self.ruleset, self.follow = ru.get("ruleset", "2024"), ru.get("follow", True)
        self.pc_hp, self.snap = ru.get("pc_hp", True), ru.get("snap", True)
        self.journal = st.get("journal", [])
        self.library = {"tokens": [], "objects": [], **st.get("library", {})}
        self.loot_history, self.loot_tables = st.get("loot_history", []), st.get("loot_tables", {})
        self.homebrew = st.get("homebrew", [])
        self.sounds_panel.load(st.get("sounds", {}))
        for d in st.get("tokens", []):
            self.add_token(d, QPointF(d["x"], d["y"]))
        for d in st.get("props", []):
            self.add_prop(d, QPointF(d["x"], d["y"]))
        cb = st.get("combat", {})
        self.active_id, self.round = cb.get("active"), cb.get("round", 0)
        L.dirty = True
        self.apply_view()
        self.combat.refresh()
        self.journal_panel.cur = None
        self.journal_panel.fill()
        self.loot_panel.refresh()
        self.reference_panel.search()
        if hasattr(self, "lib_widgets"):
            self.rebuild_left()

    def save_campaign(self, path=None):
        path = path or self.campaign_path or os.path.join(self.data_dir, "campaign.json")
        try:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.to_state(), f)
            os.replace(tmp, path)  # atomic: a crash never leaves half a campaign
        except OSError as e:
            QMessageBox.warning(self, "Save", f"Couldn't save the campaign: {e}")
            return
        self.campaign_path = path
        if self.remember:
            QSettings("DMTable", "VTT").setValue("campaign", path)
        self.setWindowTitle(f"Dungeon Master's Table — {stem(path)}")
        self.statusBar().showMessage(f"Saved {path}", 4000)

    def load_campaign(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                st = json.load(f)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Open", f"Couldn't open {path}: {e}")
            return
        self.from_state(st)
        self.campaign_path = path
        if self.remember:
            QSettings("DMTable", "VTT").setValue("campaign", path)
        self.setWindowTitle(f"Dungeon Master's Table — {stem(path)}")

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open campaign", self.data_dir, "Campaign (*.json)")
        if path:
            self.save_campaign()
            self.load_campaign(path)

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save campaign as", self.data_dir, "Campaign (*.json)")
        if path:
            self.save_campaign(path)

    def new_campaign(self):
        if QMessageBox.question(self, "New campaign", "Save the current campaign and start a new one?") == QMessageBox.Yes:
            self.save_campaign()
            self.from_state({})
            self.campaign_path = None
            self.setWindowTitle("Dungeon Master's Table")

    def receive_map(self, png, cell, props):
        """A map sent from Map Forge: grid matched to its squares, doors/chests/torches/traps as live objects."""
        old = [p for p in self.props]
        if old and QMessageBox.question(self, "New map", "Remove the objects from the previous map?") == QMessageBox.Yes:
            self.delete(old)
        self.fog.rect = QRectF()  # fresh fog for the new map
        self.open_map(png)
        self.grid.ox = self.grid.oy = 0
        self.set_grid("size", float(cell))
        self.set_grid("on", True)
        for d in props:
            self.add_prop(d, QPointF(d["x"], d["y"]))
        self.rebuild_left()
        self.statusBar().showMessage(f"Map from the Forge: {len(props)} live objects placed.", 6000)

    def closeEvent(self, e):
        self.scene.selectionChanged.disconnect(self.on_selection)  # the scene emits this while being torn down
        self.save_campaign()
        self.player.stop()
        self.sounds_panel.stop_all()
        self.timer.stop()
        self.display.close()
        self.display.deleteLater()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.closed.emit()


def stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Dungeon Master's Table")
    icons.windows_taskbar_id()
    app.setWindowIcon(icons.icon("table"))
    theme.apply(app)
    w = App()
    w.show()
    w.show_display()
    w.apply_view()
    sys.exit(app.exec())
