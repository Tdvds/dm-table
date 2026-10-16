"""Brewery: create homebrew items, custom Forge objects and homebrew enemies. Saved to the shared brewery.json,
so the Table (bestiary, loot, rules), Map Forge (object palette) and Encounter tools all see them."""
import copy, uuid
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QFormLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                               QMessageBox, QPlainTextEdit, QScrollArea, QSplitter, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)
from . import brew, encounter, forge_draw as fd, icons, rules
from .forge_gen import OBJECTS
from .panels import IMG_FILTER, SOUND_FILTER, ColorButton, FileField, btn, check, combo, hint, hrow, ispin, line, spin

LONG_HINT = "One per line, as  Name. What it does"
ITEM_SPEC = [("name", "Name", "text"), ("type", "Type", "choice", brew.ITEM_TYPES), ("subtype", "Subtype (e.g. longsword)", "text"),
             ("rarity", "Rarity", "choice", brew.RARITIES), ("attunement", "Requires attunement", "bool"),
             ("attune_by", "Attunement by", "text"), ("bonus", "Magic bonus (+)", "int", (0, 5)), ("damage", "Damage", "text"),
             ("ac", "Armor / AC", "text"), ("charges", "Charges", "int", (0, 100)), ("recharge", "Regains charges", "text"),
             ("properties", "Properties", "text"), ("value", "Value (gp)", "int", (0, 10 ** 8)),
             ("weight", "Weight (lb)", "float", (0, 10000)), ("img", "Image", "image"), ("description", "Description", "long", 170)]
OBJECT_SPEC = [("name", "Name", "text"), ("img", "Image", "image"), ("alt_img", "Open / used image", "image"),
               ("base", "Shape (if no image)", "choice", list(OBJECTS)), ("size", "Size (squares)", "float", (0.25, 10)),
               ("light", "Light", "light"), ("lit", "Lit at the start", "bool"), ("toggle", "Opens / closes when triggered", "bool"),
               ("sound", "Sound when triggered", "sound"), ("anim", "Animation when triggered", "choice", ["none", "pulse", "shake", "glow"]),
               ("hidden", "Hidden from players (DM only)", "bool"), ("above", "Draw above creatures", "bool"),
               ("notes", "DM notes", "long", 80)]
MONSTER_SPEC = [("name", "Name", "text"), ("size", "Size", "choice", list(brew.SIZES)), ("type", "Type", "choice", brew.CREATURE_TYPES),
                ("alignment", "Alignment", "text"), ("cr", "Challenge (CR)", "edit", list(encounter.CR_XP)),
                ("ac", "Armor Class", "int", (0, 40)), ("ac_note", "Armor note", "text"), ("hp", "Hit points", "int", (1, 9999)),
                ("hit_dice", "Hit dice", "text"), ("speed", "Speed", "text"), ("abilities", "Abilities", "abilities"),
                ("saves", "Saving throws", "text"), ("skills", "Skills", "text"), ("vulnerabilities", "Vulnerabilities", "text"),
                ("resistances", "Resistances", "text"), ("immunities", "Damage immunities", "text"),
                ("condition_immunities", "Condition immunities", "text"), ("senses", "Senses", "text"), ("languages", "Languages", "text"),
                ("traits", "Traits", "long", 90), ("actions", "Actions", "long", 140), ("bonus_actions", "Bonus actions", "long", 60),
                ("reactions", "Reactions", "long", 60), ("legendary", "Legendary actions", "long", 60),
                ("on the table", "On the table", "section"), ("color", "Token colour", "color"), ("img", "Token image", "image"),
                ("atk", "Attack bonus (0 = auto)", "int", (0, 30)), ("dpr", "Damage per round (0 = auto)", "int", (0, 999))]
HIT_DIE = {"Tiny": 4, "Small": 6, "Medium": 8, "Large": 10, "Huge": 12, "Gargantuan": 20}


class Form(QScrollArea):
    """Builds an editor from a field list and writes every change straight into the entry dict."""
    changed = Signal()

    def __init__(self, spec):
        super().__init__()
        self.spec, self.d = spec, None
        self.setWidgetResizable(True)
        self.load(None)

    def load(self, d):
        self.d = d
        w = QWidget()
        f = QFormLayout(w)
        self.setWidget(w)
        if d is None:
            f.addRow(hint("Nothing selected. Use ✚ New to brew something."))
            return
        for key, label, kind, *opt in self.spec:
            self.add(f, d, key, label, kind, opt[0] if opt else None)

    def setter(self, key):
        def fn(v):
            self.d[key] = v
            self.changed.emit()
        return fn

    def add(self, f, d, key, label, kind, opt):
        s = self.setter(key)
        if kind == "section":
            lab = QLabel(label)
            lab.setObjectName("title")
            f.addRow(lab)
        elif kind == "text":
            f.addRow(label, line(str(d[key]), s))
        elif kind == "long":
            e = QPlainTextEdit(d[key])
            e.setMinimumHeight(opt or 80)
            e.setPlaceholderText(LONG_HINT if key in ("traits", "actions", "bonus_actions", "reactions", "legendary") else "")
            e.textChanged.connect(lambda: s(e.toPlainText()))
            f.addRow(label, e)
        elif kind == "int":
            f.addRow(label, ispin(*opt, int(d[key]), s))
        elif kind == "float":
            f.addRow(label, spin(*opt, float(d[key]), 0.25, 2, s))
        elif kind == "choice":
            f.addRow(label, combo(opt, d[key], s))
        elif kind == "edit":
            c = combo(opt, str(d[key]))
            c.setEditable(True)
            c.setCurrentText(str(d[key]))
            c.currentTextChanged.connect(s)
            f.addRow(label, c)
        elif kind == "bool":
            f.addRow(check(label, d[key], s))
        elif kind == "color":
            f.addRow(label, ColorButton(d[key], s))
        elif kind in ("image", "sound"):
            f.addRow(label, FileField(d[key], IMG_FILTER if kind == "image" else SOUND_FILTER, s))
        elif kind == "abilities":
            boxes = []
            for a in brew.ABILITIES:
                box = QWidget()
                col = QVBoxLayout(box)
                col.setContentsMargins(0, 0, 0, 0)
                col.addWidget(QLabel(a.upper()), alignment=Qt.AlignCenter)
                col.addWidget(ispin(1, 30, d[a], self.setter(a)))
                boxes.append(box)
            f.addRow(label, hrow(*boxes))
        elif kind == "light":
            L = d[key]

            def preset(name):
                d[key] = None if name == "None" else rules.light(name) if name in rules.LIGHTS else dict(L or rules.light("Torch"), preset="Custom")
                self.changed.emit()
                QTimer.singleShot(0, lambda: self.load(self.d))  # show/hide the detail rows, outside this combo's signal
            f.addRow(label, combo(["None"] + list(rules.LIGHTS) + ["Custom"], (L or {}).get("preset", "None"), preset))
            if L:
                def part(k):
                    def fn(v):
                        L[k], L["preset"] = v, "Custom"
                        self.changed.emit()
                    return fn
                f.addRow("Bright / dim ft", hrow(ispin(0, 300, L["bright"], part("bright")), ispin(0, 300, L["dim"], part("dim"))))
                f.addRow("Light colour", hrow(ColorButton(L["color"], part("color")), spin(0, 2, L.get("flicker", 0), 0.1, 1, part("flicker")),
                                              QLabel("flicker")))


class Shelf(QWidget):
    """One tab: a searchable list, the editor form and a live preview."""

    def __init__(self, win, kind, spec, extras=()):
        super().__init__()
        self.win, self.kind = win, kind
        split = QSplitter()
        left = QWidget()
        lv = QVBoxLayout(left)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search…")
        self.search.textChanged.connect(lambda _: self.fill())
        self.list = QListWidget()
        self.list.currentItemChanged.connect(lambda *_: self.open_current())
        lv.addWidget(self.search)
        lv.addWidget(self.list, 1)
        lv.addWidget(hrow(btn("✚ New", self.new), btn("Duplicate", self.duplicate), btn("Delete", self.delete)))
        for text, fn, tip in extras:
            lv.addWidget(btn(text, fn, tip))
        self.form = Form(spec)
        self.form.changed.connect(self.edited)
        right = QWidget()
        rv = QVBoxLayout(right)
        self.picture = QLabel()
        self.picture.setAlignment(Qt.AlignCenter)
        self.view = QTextBrowser()
        self.view.setStyleSheet("QTextBrowser { background: #efe3c4; color: #2a1d10; border: 2px solid #8b6b3d; }")
        rv.addWidget(self.picture)
        rv.addWidget(self.view, 1)
        for w in (left, self.form, right):
            split.addWidget(w)
        split.setSizes([240, 720, 400])  # the form needs room for the six ability boxes
        QVBoxLayout(self).addWidget(split)
        self.fill()

    def entries(self):
        return self.win.data[self.kind]

    def current(self):
        it = self.list.currentItem()
        return next((e for e in self.entries() if it and e["id"] == it.data(Qt.UserRole)), None)

    def label(self, e):
        extra = {"items": lambda: e["rarity"], "monsters": lambda: f"CR {e['cr']}", "objects": lambda: ""}[self.kind]()
        return f"{e['name']}" + (f"   ·  {extra}" if extra else "")

    def fill(self, select=None):
        keep = select or (self.current() or {}).get("id")
        q = self.search.text().lower()
        self.list.blockSignals(True)
        self.list.clear()
        for e in sorted(self.entries(), key=lambda e: e["name"].lower()):
            if q and q not in e["name"].lower():
                continue
            it = QListWidgetItem(self.label(e))
            it.setData(Qt.UserRole, e["id"])
            self.list.addItem(it)
            if e["id"] == keep:
                self.list.setCurrentItem(it)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)
        self.list.blockSignals(False)
        self.open_current()

    def open_current(self):
        e = self.current()
        self.form.load(e)
        self.preview(e)

    def preview(self, e):
        self.picture.clear()
        if e is None:
            self.view.setMarkdown("")
            return
        if self.kind == "items":
            self.view.setMarkdown(brew.itemcard(e))
            pm = QPixmap(e["img"]) if e["img"] else QPixmap()
        elif self.kind == "monsters":
            self.view.setMarkdown(brew.statblock(e))
            pm = QPixmap(e["img"]) if e["img"] else QPixmap()
        else:
            fd.CUSTOM[e["id"]] = e  # draw it exactly as Map Forge will
            pm = QPixmap.fromImage(fd.object_image("brew:" + e["id"], 160))
            L = e["light"]
            self.view.setMarkdown(f"## {e['name']}\n" + (f"Light: **{L['preset']}**, {L['bright']} ft bright + {L['dim']} ft dim, colour {L['color']}\n\n" if L else "")
                                  + ("Opens / closes when triggered.  \n" if e["toggle"] else "") + ("Hidden from players.  \n" if e["hidden"] else "")
                                  + f"\nAppears in Map Forge → Objects. Sent to the table it becomes a live object.\n\n{e['notes']}")
        if not pm.isNull():
            self.picture.setPixmap(pm.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def edited(self):
        e, it = self.current(), self.list.currentItem()
        if e and it:
            it.setText(self.label(e))
            self.preview(e)
        self.win.touched()

    def add(self, e):
        self.entries().append(e)
        self.search.clear()
        self.fill(select=e["id"])
        self.win.touched()

    def new(self):
        self.add(brew.new(self.kind))

    def duplicate(self):
        e = self.current()
        if e:
            self.add(dict(copy.deepcopy(e), id=uuid.uuid4().hex[:8], name=e["name"] + " (copy)"))

    def delete(self):
        e = self.current()
        if e and QMessageBox.question(self, "Brewery", f"Pour out '{e['name']}'? This can't be undone.") == QMessageBox.Yes:
            self.entries().remove(e)
            self.fill()
            self.win.touched()


class Brewery(QMainWindow):
    closed, saved = Signal(), Signal()

    def __init__(self, launcher=None):
        super().__init__()
        self.setWindowTitle("Brewery")
        self.setWindowIcon(icons.icon("brewery"))
        self.data = copy.deepcopy(brew.load())
        self.timer = QTimer(self, singleShot=True, interval=700)  # save shortly after typing stops
        self.timer.timeout.connect(self.flush)
        tabs = QTabWidget()
        self.items = Shelf(self, "items", ITEM_SPEC)
        self.objects = Shelf(self, "objects", OBJECT_SPEC)
        self.monsters = Shelf(self, "monsters", MONSTER_SPEC, (
            ("⎘ New from template…", self.from_template, "Start from an SRD monster or one of your own"),
            ("⚖ Fill stats for its CR", self.auto_stats, "AC, HP, hit dice, attack and damage typical for the CR"),
            ("⟳ HP = average of hit dice", self.hp_from_dice, "")))
        tabs.addTab(self.items, "⚗ Items")
        tabs.addTab(self.objects, "⚒ Forge objects")
        tabs.addTab(self.monsters, "☠ Bestiary")
        self.setCentralWidget(tabs)
        self.statusBar().showMessage("Everything saves by itself and is shared with the Table and Map Forge.")
        self.resize(1400, 860)

    def focus(self, kind, eid=None, new=False):
        """Opened from another app: show this entry, or start a new one (a 'homebrew weapon' is an item of type Weapon)."""
        self.centralWidget().setCurrentIndex(["items", "objects", "monsters"].index(kind))
        shelf = getattr(self, kind)
        if new:
            shelf.add(brew.new(kind, type="Weapon", name="New weapon") if kind == "items" else brew.new(kind))
        elif eid:
            shelf.search.clear()
            shelf.fill(select=eid)

    def touched(self):
        self.timer.start()

    def flush(self):
        try:
            brew.save(self.data)
        except OSError as e:
            QMessageBox.warning(self, "Brewery", f"Couldn't save the library: {e}")
            return
        self.statusBar().showMessage(f"Saved to {brew.FILE}", 3000)
        self.saved.emit()

    def from_template(self):
        names = [t["name"] for t in brew.TEMPLATES] + [f"{m['name']} (yours)" for m in self.data["monsters"]]
        name, ok = QInputDialog.getItem(self, "New from template", "Start from:", names, 0, False)
        if ok:
            src = (brew.TEMPLATES + self.data["monsters"])[names.index(name)]
            self.monsters.add(dict(copy.deepcopy(src), id=uuid.uuid4().hex[:8], name=src["name"] + " (variant)"))

    def auto_stats(self):
        m = self.monsters.current()
        if not m:
            return
        s = encounter.monster_stats(m["cr"])
        die, cm = HIT_DIE.get(m["size"], 8), brew.mod(m["con"])
        n = max(1, round(s["hp"] / max(1, (die + 1) / 2 + cm)))
        m.update(ac=s["ac"], atk=s["atk"], dpr=round(s["dpr"]), hit_dice=f"{n}d{die}" + (f"{n * cm:+d}" if cm else ""))
        m["hp"] = max(1, brew.avg_dice(m["hit_dice"]))
        self.monsters.open_current()
        self.monsters.edited()

    def hp_from_dice(self):
        m = self.monsters.current()
        hp = brew.avg_dice(m["hit_dice"]) if m else None
        if hp is None:
            self.statusBar().showMessage("Hit dice should look like 4d10+8.", 4000)
            return
        m["hp"] = max(1, hp)
        self.monsters.open_current()
        self.monsters.edited()

    def closeEvent(self, e):
        if self.timer.isActive():
            self.timer.stop()
            self.flush()
        self.closed.emit()
