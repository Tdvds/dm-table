"""Dock panels: Inspector, Initiative tracker and Campaign journal, plus small widget helpers."""
import os, re, time, uuid
from urllib.parse import quote, unquote
from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtMultimedia import QAudioInput, QMediaCaptureSession, QMediaFormat, QMediaRecorder
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSlider, QSpinBox,
                               QSplitter, QTableWidget, QTableWidgetItem, QTabWidget, QTextBrowser, QTextEdit,
                               QVBoxLayout, QWidget)
from . import rules
from .items import KIND_COLORS, Token
from .weather import TYPES as WEATHER_TYPES

IMG_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All files (*)"
SOUND_FILTER = "Audio (*.wav *.mp3 *.ogg *.flac *.m4a *.aac *.opus);;All files (*)"
KINDS = list(KIND_COLORS)
ENTRY_TYPES = ["Location", "NPC", "Quest", "Item", "Handout", "Lore"]
GLYPH = {"Location": "⌂", "NPC": "☺", "Quest": "✦", "Item": "⚒", "Handout": "✉", "Lore": "✧"}


# ---------- tiny widget helpers ----------
def btn(text, cb, tip=""):
    b = QPushButton(text)
    b.clicked.connect(lambda checked=False: cb())
    b.setToolTip(tip)
    return b


def hrow(*ws):
    w = QWidget()
    w.setObjectName("row")
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    for x in ws:
        h.addWidget(x)
    return w


def group(title, layout):
    g = QGroupBox(title)
    layout.addWidget(g)
    return QFormLayout(g)


def hint(text):
    lab = QLabel(text)
    lab.setObjectName("hint")
    lab.setWordWrap(True)
    return lab


def line(val, cb):
    e = QLineEdit(val)
    e.textChanged.connect(cb)
    return e


def spin(lo, hi, val, step=1.0, dec=1, cb=None):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(dec)
    s.setSingleStep(step)
    s.setValue(val)
    if cb:
        s.valueChanged.connect(cb)
    return s


def ispin(lo, hi, val, cb=None):
    s = QSpinBox()
    s.setRange(lo, hi)
    s.setValue(int(val))
    if cb:
        s.valueChanged.connect(cb)
    return s


def check(text, val, cb):
    c = QCheckBox(text)
    c.setChecked(bool(val))
    c.toggled.connect(cb)
    return c


def combo(options, val, cb=None):
    c = QComboBox()
    c.addItems(options)
    c.setCurrentText(val)
    if cb:
        c.currentTextChanged.connect(cb)
    return c


def slider(lo, hi, val, cb=None):
    s = QSlider(Qt.Horizontal)
    s.setRange(lo, hi)
    s.setValue(int(val))
    if cb:
        s.valueChanged.connect(cb)
    return s


class ColorButton(QPushButton):
    def __init__(self, color, cb=None):
        super().__init__()
        self.cb = cb
        self.setFixedWidth(42)
        self.set_color(color)
        self.clicked.connect(self.pick)

    def set_color(self, c):
        self.color = c
        self.setStyleSheet(f"background: {c}; border: 1px solid #e0b84f;")

    def pick(self):
        c = QColorDialog.getColor(QColor(self.color), self)
        if c.isValid():
            self.set_color(c.name())
            if self.cb:
                self.cb(c.name())


class FileField(QWidget):
    def __init__(self, path, filt, cb):
        super().__init__()
        self.path, self.filt, self.cb = path, filt, cb
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel()
        h.addWidget(self.label, 1)
        h.addWidget(btn("…", self.pick, "Choose file"))
        h.addWidget(btn("✕", lambda: self.set(""), "Clear"))
        self.show_name()

    def show_name(self):
        self.label.setText(os.path.basename(self.path) or "(none)")
        self.label.setToolTip(self.path)

    def pick(self):
        p, _ = QFileDialog.getOpenFileName(self, "Choose file", os.path.dirname(self.path), self.filt)
        if p:
            self.set(p)

    def set(self, p):
        self.path = p
        self.show_name()
        self.cb(p)


# ---------- Inspector ----------
class Inspector(QScrollArea):
    """Edits whatever single token or object is selected on the map."""

    def __init__(self, app):
        super().__init__()
        self.app, self.target = app, None
        self.setWidgetResizable(True)
        self.set_target(None)

    def reload(self):
        self.set_target(self.target)

    def set_target(self, t):
        self.target = t
        w = QWidget()
        f = QFormLayout(w)
        self.setWidget(w)
        if t is None:
            f.addRow(hint("Select a creature or object on the map to inspect it.\n\n"
                          "Right-click the map to add creatures, lights, notes, traps and objects."))
            return

        def set_(attr):
            def fn(v):
                setattr(t, attr, v)
                t.refresh()
                self.app.on_entity_changed(t)
            return fn

        f.addRow("Name", line(t.name, set_("name")))
        if isinstance(t, Token):
            f.addRow("Side", combo(KINDS, t.kind, lambda k: (set_("kind")(k), QTimer.singleShot(0, self.reload))))  # PC shows Level, others CR
            f.addRow("Image", FileField(t.img, IMG_FILTER, set_("img")))
            f.addRow("Colour / size", hrow(ColorButton(t.color, set_("color")), spin(0.25, 20, t.cells, 0.25, 2, set_("cells"))))
            f.addRow("HP / max", hrow(ispin(0, 9999, t.hp, set_("hp")), ispin(1, 9999, t.max_hp, set_("max_hp"))))
            f.addRow("Temp HP / AC", hrow(ispin(0, 999, t.temp, set_("temp")), ispin(0, 40, t.ac, set_("ac"))))
            f.addRow("Initiative mod", ispin(-10, 20, t.init_mod, set_("init_mod")))
            f.addRow(*(("Level", ispin(1, 20, t.level, set_("level"))) if t.kind == "pc" else ("Challenge (CR)", line(t.cr, set_("cr")))))
            atk, dpr = ispin(0, 30, t.atk, set_("atk")), ispin(0, 999, t.dpr, set_("dpr"))
            atk.setSpecialValueText("auto")
            dpr.setSpecialValueText("auto")
            f.addRow("Attack / dmg per round", hrow(atk, dpr))
            conds = QListWidget()
            conds.setMinimumHeight(150)
            for name in rules.CONDITIONS:
                if name == "Exhaustion":
                    continue
                it = QListWidgetItem(name)
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked if name in t.conditions else Qt.Unchecked)
                it.setToolTip(rules.summary(name, self.app.ruleset))
                it.setForeground(QColor(rules.badge(name)[1]).lighter(150))
                conds.addItem(it)

            def cond_changed(it):
                if it.checkState() == Qt.Checked:
                    t.conditions.setdefault(it.text(), 0)
                else:
                    t.conditions.pop(it.text(), None)
                t.refresh()
                self.app.on_entity_changed(t)
            conds.itemChanged.connect(cond_changed)
            f.addRow("Conditions", conds)
            f.addRow("Exhaustion", hrow(ispin(0, 6, t.exhaustion, set_("exhaustion")),
                                        check("Concentrating", t.concentrating, set_("concentrating"))))
            f.addRow(check("Dead / defeated", t.dead, set_("dead")))
        else:
            if not t.icon:
                f.addRow("Image", FileField(t.img, IMG_FILTER, set_("img")))
                f.addRow("Open image", FileField(t.alt_img, IMG_FILTER, set_("alt_img")))
                f.addRow("Size / turn", hrow(spin(0.1, 50, t.cells, 0.25, 2, set_("cells")), spin(0, 359, t.rotation, 15, 0, set_("rotation"))))
                f.addRow(check("Draw above creatures", t.above, set_("above")))
            f.addRow(check("Opens / closes when triggered", t.toggle, set_("toggle")))
            f.addRow(check("Open", t.opened, set_("opened")))
            f.addRow("Sound", FileField(t.sound, SOUND_FILTER, set_("sound")))
            f.addRow("Animation", combo(["none", "pulse", "shake", "glow"], t.anim, set_("anim")))
            f.addRow("Reveals tag", line(t.reveals, set_("reveals")))
            f.addRow("Sets weather", combo([""] + WEATHER_TYPES, t.weather, set_("weather")))
            jc = QComboBox()
            jc.addItem("(none)", "")
            for e in self.app.journal:
                jc.addItem(f"{GLYPH.get(e['type'], '')} {e['title']}", e["id"])
            jc.setCurrentIndex(max(0, jc.findData(t.journal)))
            jc.currentIndexChanged.connect(lambda i: set_("journal")(jc.itemData(i)))
            f.addRow("Journal entry", jc)
            f.addRow(btn("☝ Trigger now", lambda: self.app.trigger(t)))
        f.addRow(check("Hidden from players", t.hidden, set_("hidden")))
        f.addRow("Tag", line(t.tag, set_("tag")))

        presets = ["None"] + list(rules.LIGHTS) + ["Custom"]

        def set_preset(name):
            if name == "None":
                t.light = None
            elif name in rules.LIGHTS:
                t.light = rules.light(name)
            else:
                t.light = dict(t.light or rules.light("Torch"), preset="Custom")
            t.refresh()
            QTimer.singleShot(0, self.reload)  # rebuild the form outside this combo's own signal
        f.addRow("Light", combo(presets, (t.light or {}).get("preset", "None"), set_preset))
        if t.light:
            def set_light(key):
                def fn(v):
                    t.light[key] = v
                    t.light["preset"] = "Custom"
                    t.refresh()
                return fn
            f.addRow("Bright / dim ft", hrow(ispin(0, 300, t.light["bright"], set_light("bright")), ispin(0, 300, t.light["dim"], set_light("dim"))))
            f.addRow("Light colour", hrow(ColorButton(t.light["color"], set_light("color")),
                                          spin(0, 2, t.light.get("flicker", 0), 0.1, 1, set_light("flicker")), QLabel("flicker")))
            f.addRow(check("Lit", t.lit, set_("lit")))
        notes = QPlainTextEdit(t.notes)
        notes.setPlaceholderText("Secret DM notes (players never see these)")
        notes.setMaximumHeight(110)
        notes.textChanged.connect(lambda: set_("notes")(notes.toPlainText()))
        f.addRow("DM notes", notes)


# ---------- Initiative ----------
class CombatPanel(QWidget):
    COLS = ["Init", "Name", "HP", "Temp", "AC", "Conditions"]

    def __init__(self, app):
        super().__init__()
        self.app, self.rows = app, []
        v = QVBoxLayout(self)
        self.round_label = QLabel()
        self.round_label.setObjectName("title")
        self.round_label.setAlignment(Qt.AlignCenter)
        v.addWidget(self.round_label)
        v.addWidget(hrow(btn("Add selected", self.add_selected), btn("Add all", self.add_all),
                         btn("Roll NPCs", self.roll_npcs, "Roll d20 + mod for every non-PC")))
        v.addWidget(hrow(btn("◀ Prev", self.prev_turn), btn("Next turn ▶", self.next_turn, "Shortcut: N"), btn("End", self.end_combat)))
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(self.edited)
        self.table.itemSelectionChanged.connect(self.select_on_map)
        v.addWidget(self.table, 1)
        self.amount = ispin(0, 9999, 0)
        self.mode = combo(["normal", "resistant", "vulnerable", "immune"], "normal")
        v.addWidget(hrow(QLabel("Amount"), self.amount, self.mode))
        v.addWidget(hrow(btn("⚔ Damage", lambda: self.apply(rules.damage)), btn("✚ Heal", lambda: self.apply(rules.heal)),
                         btn("◈ Temp HP", lambda: self.apply(rules.temp_hp))))
        self.cond = combo([n for n in rules.CONDITIONS if n != "Exhaustion"], "Poisoned")
        self.cond.setEditable(True)  # type anything for custom effects (Blessed, Hasted...)
        self.rounds = ispin(0, 100, 0)
        self.rounds.setSpecialValueText("∞")
        self.rounds.setSuffix(" rnd")
        v.addWidget(hrow(self.cond, self.rounds))
        v.addWidget(hrow(btn("Apply", self.add_cond), btn("Remove", self.remove_cond), btn("Concentration", self.toggle_conc)))
        self.logbox = QTextEdit()
        self.logbox.setReadOnly(True)
        self.logbox.setMaximumHeight(160)
        v.addWidget(self.logbox)
        self.refresh()

    def combatants(self):
        return sorted((t for t in self.app.tokens if t.in_combat),
                      key=lambda t: (-(t.init if t.init is not None else -99), -t.init_mod, t.name))

    def refresh(self):
        self.rows = self.combatants()
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.rows))
        for r, t in enumerate(self.rows):
            conds = [f"{n}{f' ({x})' if x else ''}" for n, x in t.conditions.items()]
            conds += [f"Exh {t.exhaustion}"] * bool(t.exhaustion) + ["Conc."] * t.concentrating
            vals = ["" if t.init is None else str(t.init), t.name, f"{t.hp}/{t.max_hp}", str(t.temp), str(t.ac), ", ".join(conds)]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c in (1, 5):
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if t.id == self.app.active_id:
                    it.setBackground(QColor("#7a2020"))
                if t.dead:
                    it.setForeground(QColor("#6b5a44"))
                elif c == 1:
                    it.setForeground(QColor(KIND_COLORS.get(t.kind, "#ccc")).lighter(160))
                it.setToolTip(t.tooltip())
                self.table.setItem(r, c, it)
        self.table.blockSignals(False)
        self.round_label.setText(f"⚔ Round {self.app.round}" if self.app.active_id else "Out of combat")

    def log(self, msg):
        self.logbox.append(msg)

    def edited(self, it):
        t, txt = self.rows[it.row()], it.text().strip()
        try:
            if it.column() == 0:
                t.init = int(txt) if txt else None
            elif it.column() == 2:
                hp, _, mx = txt.partition("/")
                t.hp = max(0, int(hp))
                if mx:
                    t.max_hp = max(1, int(mx))
            elif it.column() == 3:
                t.temp = max(0, int(txt))
            elif it.column() == 4:
                t.ac = int(txt)
        except ValueError:
            pass
        t.refresh()
        QTimer.singleShot(0, self.refresh)

    def selected(self):
        return [self.rows[i.row()] for i in self.table.selectionModel().selectedRows()]

    def select_on_map(self):
        sel = self.selected()
        if sel:
            self.app.scene.clearSelection()
            for t in sel:
                t.setSelected(True)

    def changed(self, tokens):
        for t in tokens:
            t.refresh()
        if self.app.inspector.target in tokens:
            self.app.inspector.reload()
        self.refresh()

    def need(self):
        sel = self.selected()
        if not sel:
            self.app.statusBar().showMessage("Select one or more combatants in the list first.", 4000)
        return sel

    def apply(self, fn):
        sel = self.need()
        for t in sel:
            lines = fn(t, self.amount.value(), self.mode.currentText(), self.app.ruleset) if fn is rules.damage else fn(t, self.amount.value())
            for m in lines:
                self.log(m)
        self.changed(sel)

    def add_cond(self):
        sel, name = self.need(), self.cond.currentText().strip()
        for t in sel:
            if name:
                t.conditions[name] = self.rounds.value()
                self.log(f"{t.name} is {name}" + (f" for {self.rounds.value()} rounds" if self.rounds.value() else ""))
        self.changed(sel)

    def remove_cond(self):
        sel, name = self.need(), self.cond.currentText().strip()
        for t in sel:
            if t.conditions.pop(name, None) is not None:
                self.log(f"{name} removed from {t.name}")
        self.changed(sel)

    def toggle_conc(self):
        sel = self.need()
        for t in sel:
            t.concentrating = not t.concentrating
            self.log(f"{t.name} {'starts' if t.concentrating else 'stops'} concentrating")
        self.changed(sel)

    def toggle(self, t):
        t.in_combat = not t.in_combat
        if t.in_combat and t.init is None and t.kind != "pc":
            t.init = rules.roll_init(t)
        self.refresh()

    def add_selected(self):
        for t in self.app.scene.selectedItems():
            if isinstance(t, Token) and not t.in_combat:
                self.toggle(t)

    def add_all(self):
        for t in self.app.tokens:
            if not t.in_combat:
                self.toggle(t)

    def roll_npcs(self):
        for t in self.combatants():
            if t.kind != "pc":
                t.init = rules.roll_init(t)
                self.log(f"{t.name} rolls {t.init} initiative")
        self.refresh()

    def step(self, d):
        a, allc = self.app, self.combatants()
        alive = [t for t in allc if not (t.dead and t.kind != "pc")]  # slain monsters are skipped, downed PCs are not
        if not alive:
            return None
        ids = [t.id for t in allc]
        i = ids.index(a.active_id) if a.active_id in ids else -1
        if a.round == 0 or a.active_id is None:
            a.round, i = 1, -1
        for _ in range(len(allc)):
            i += d
            if i >= len(allc):
                i, a.round = 0, a.round + 1
            elif i < 0:
                i, a.round = len(allc) - 1, max(1, a.round - 1)
            if allc[i] in alive:
                break
        t = allc[i]
        a.active_id = t.id
        for x in a.tokens:
            x.update()
        if a.follow:
            a.center = t.pos()
            a.apply_view()
        return t

    def next_turn(self):
        t = self.step(1)
        if t:
            self.log(f"<b>— Round {self.app.round}: {t.name}'s turn —</b>")
            for m in rules.start_turn(t):
                self.log(m)
            self.changed([t])

    def prev_turn(self):
        if self.step(-1):
            self.refresh()

    def end_combat(self):
        a = self.app
        a.active_id, a.round = None, 0
        for t in a.tokens:
            t.in_combat, t.init = False, None
            t.update()
        self.log("<b>Combat ends.</b>")
        self.refresh()


# ---------- Journal ----------
class JournalPanel(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.cur, self.rec, self.rec_entry = app, None, None, None
        v = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search the chronicle…")
        self.search.textChanged.connect(self.fill)
        self.kind = combo(["All"] + ENTRY_TYPES, "All", lambda _: self.fill())
        self.here = check("This map only", False, lambda _: self.fill())
        v.addWidget(hrow(self.search, self.kind))
        v.addWidget(hrow(self.here, btn("✚ New", self.new), btn("Delete", self.delete)))
        split = QSplitter(Qt.Vertical)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(lambda it, _: self.open(it.data(Qt.UserRole) if it else None))
        split.addWidget(self.list)
        self.editor = QWidget()
        ev = QVBoxLayout(self.editor)
        ev.setContentsMargins(0, 0, 0, 0)
        self.title = QLineEdit()
        self.title.editingFinished.connect(lambda: self.edit("title", self.title.text().strip() or "Untitled", True))
        self.type = combo(ENTRY_TYPES, "NPC", lambda x: self.edit("type", x, True))
        ev.addWidget(hrow(self.title, self.type))
        self.portrait = QLabel()
        self.portrait.setAlignment(Qt.AlignCenter)
        self.portrait.setFixedHeight(150)
        ev.addWidget(self.portrait)
        self.linked = check("Linked to this map", False, self.link)
        ev.addWidget(hrow(btn("Image…", self.pick_image), btn("Show to players", self.show_players, "Handout on the player display"),
                          btn("Pin on map", self.pin)))
        ev.addWidget(self.linked)
        self.tabs = QTabWidget()
        self.view = QTextBrowser()
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(self.follow)
        self.body = QPlainTextEdit()
        self.body.setPlaceholderText("Write here. Link other entries with [[Their Title]]. Markdown works: **bold**, # headings, - lists.")
        self.body.textChanged.connect(lambda: self.edit("body", self.body.toPlainText()))
        self.rel = QPlainTextEdit()
        self.rel.setPlaceholderText("Relationship history: who they love, hate, owe… e.g. Sworn enemy of [[Baron Vex]].")
        self.rel.textChanged.connect(lambda: self.edit("relations", self.rel.toPlainText()))
        voice = QWidget()
        vv = QVBoxLayout(voice)
        self.voices = QListWidget()
        self.voices.itemDoubleClicked.connect(lambda it: self.app.play_sound(it.data(Qt.UserRole)))
        self.rec_btn = btn("● Record", self.record)
        vv.addWidget(self.voices)
        vv.addWidget(hrow(self.rec_btn, btn("Attach…", self.attach), btn("▶ Play", self.play), btn("Remove", self.remove_voice)))
        for w, name in ((self.view, "Read"), (self.body, "Write"), (self.rel, "Relationships"), (voice, "Voice notes")):
            self.tabs.addTab(w, name)
        self.tabs.currentChanged.connect(lambda i: i == 0 and self.render())
        ev.addWidget(self.tabs, 1)
        split.addWidget(self.editor)
        split.setSizes([160, 500])
        v.addWidget(split, 1)
        self.fill()

    def entry(self, eid):
        return next((e for e in self.app.journal if e["id"] == eid), None)

    def fill(self):
        q, typ, here = self.search.text().lower(), self.kind.currentText(), self.here.isChecked()
        self.list.blockSignals(True)
        self.list.clear()
        for e in sorted(self.app.journal, key=lambda e: (e["type"], e["title"].lower())):
            if (typ != "All" and e["type"] != typ) or (q and q not in (e["title"] + e["body"] + e["relations"]).lower()) \
                    or (here and self.app.map_path not in e["maps"]):
                continue
            it = QListWidgetItem(f"{GLYPH.get(e['type'], '•')}  {e['title']}")
            it.setData(Qt.UserRole, e["id"])
            self.list.addItem(it)
            if self.cur is e:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        self.show_entry()

    def open(self, eid):
        self.cur = self.entry(eid)
        self.show_entry()

    def select(self, eid):
        self.cur = self.entry(eid)
        self.search.clear()
        self.kind.setCurrentText("All")
        self.here.setChecked(False)
        self.fill()
        self.tabs.setCurrentIndex(0)

    def show_entry(self):
        e = self.cur
        self.editor.setEnabled(e is not None)
        widgets = (self.title, self.type, self.body, self.rel, self.linked)
        for w in widgets:
            w.blockSignals(True)
        self.title.setText(e["title"] if e else "")
        self.type.setCurrentText(e["type"] if e else "NPC")
        self.body.setPlainText(e["body"] if e else "")
        self.rel.setPlainText(e["relations"] if e else "")
        self.linked.setChecked(bool(e and self.app.map_path in e["maps"]))
        for w in widgets:
            w.blockSignals(False)
        pm = QPixmap(e["img"]) if e and e["img"] else QPixmap()
        self.portrait.setPixmap(pm.scaledToHeight(150, Qt.SmoothTransformation) if not pm.isNull() else QPixmap())
        self.portrait.setText("" if not pm.isNull() else "(no portrait)")
        self.voices.clear()
        for path in (e["voice"] if e else []):
            it = QListWidgetItem("♪ " + os.path.basename(path))
            it.setData(Qt.UserRole, path)
            self.voices.addItem(it)
        self.render()

    def render(self):
        e = self.cur
        if not e:
            self.view.setMarkdown("*Select or create an entry.*")
            return
        link = lambda s: re.sub(r"\[\[([^\]]+)\]\]", lambda m: f"[{m[1]}](entry:{quote(m[1])})", s)
        me = f"[[{e['title']}]]".lower()
        backlinks = [x for x in self.app.journal if x is not e and me in (x["body"] + x["relations"]).lower()]
        md = f"# {e['title']}\n*{e['type']}*\n\n{link(e['body'])}\n"
        if e["relations"].strip():
            md += f"\n## Relationships\n{link(e['relations'])}\n"
        if backlinks:  # quests, places and people that mention this entry
            md += "\n## Mentioned in\n" + "\n".join(f"- {GLYPH.get(x['type'], '')} [{x['title']}](entry:{quote(x['title'])})" for x in backlinks)
        self.view.setMarkdown(md)

    def follow(self, url):
        title = unquote(url.toString()[len("entry:"):])
        e = next((x for x in self.app.journal if x["title"].lower() == title.lower()), None)
        if e is None:  # wiki-style: following a link to a missing page creates it
            e = self.make(title, "NPC")
        self.select(e["id"])

    def edit(self, key, val, relist=False):
        if self.cur is None:
            return
        self.cur[key] = val
        if relist:
            self.fill()

    def make(self, title, typ):
        e = dict(id=uuid.uuid4().hex[:8], type=typ, title=title, img="", body="", relations="", voice=[], maps=[])
        self.app.journal.append(e)
        return e

    def new(self):
        typ = self.kind.currentText()
        e = self.make("New entry", typ if typ in ENTRY_TYPES else "NPC")
        self.select(e["id"])
        self.tabs.setCurrentIndex(1)
        self.title.setFocus()
        self.title.selectAll()

    def delete(self):
        if self.cur and QMessageBox.question(self, "Journal", f"Delete '{self.cur['title']}'?") == QMessageBox.Yes:
            self.app.journal.remove(self.cur)
            self.cur = None
            self.fill()

    def link(self, on):
        e, m = self.cur, self.app.map_path
        if e and m:
            if on and m not in e["maps"]:
                e["maps"].append(m)
            elif not on and m in e["maps"]:
                e["maps"].remove(m)

    def pick_image(self):
        p, _ = QFileDialog.getOpenFileName(self, "Portrait or handout image", "", IMG_FILTER)
        if p and self.cur:
            self.cur["img"] = p
            self.show_entry()

    def show_players(self):
        if self.cur and self.cur["img"]:
            self.app.show_handout(self.cur["img"])
        else:
            self.app.statusBar().showMessage("Give this entry an image first.", 4000)

    def pin(self):
        if self.cur:
            self.app.add_prop({"icon": "pin", "name": self.cur["title"], "journal": self.cur["id"]}, select=True)

    def attach(self):
        p, _ = QFileDialog.getOpenFileName(self, "Voice note", "", SOUND_FILTER)
        if p and self.cur:
            self.cur["voice"].append(p)
            self.show_entry()

    def play(self):
        it = self.voices.currentItem()
        if it:
            self.app.play_sound(it.data(Qt.UserRole))

    def remove_voice(self):
        it = self.voices.currentItem()
        if it and self.cur:
            self.cur["voice"].remove(it.data(Qt.UserRole))
            self.show_entry()

    def record(self):
        if self.rec is None:  # created on first use so the mic isn't touched at startup
            self.session, self.mic, self.rec = QMediaCaptureSession(), QAudioInput(), QMediaRecorder()
            self.session.setAudioInput(self.mic)
            self.session.setRecorder(self.rec)
            fmt = QMediaFormat(QMediaFormat.FileFormat.Mpeg4Audio)
            fmt.setAudioCodec(QMediaFormat.AudioCodec.AAC)
            self.rec.setMediaFormat(fmt)
            self.rec.recorderStateChanged.connect(self.rec_state)
            self.rec.errorOccurred.connect(lambda err, msg: QMessageBox.warning(self, "Recording", msg))
        if self.rec.recorderState() == QMediaRecorder.RecorderState.RecordingState:
            self.rec.stop()
            return
        if not self.cur:
            return
        folder = os.path.join(self.app.data_dir, "voice")
        os.makedirs(folder, exist_ok=True)
        self.rec_entry = self.cur
        self.rec.setOutputLocation(QUrl.fromLocalFile(os.path.join(folder, f"{self.cur['id']}_{int(time.time())}.m4a")))
        self.rec.record()

    def rec_state(self, state):
        recording = state == QMediaRecorder.RecorderState.RecordingState
        self.rec_btn.setText("■ Stop" if recording else "● Record")
        if not recording and self.rec_entry is not None:
            path = self.rec.actualLocation().toLocalFile()
            if path and os.path.exists(path):
                self.rec_entry["voice"].append(path)
            self.rec_entry = None
            self.show_entry()
