"""DM tool panels: Loot & rewards, Encounter balancing & simulation, Rules reference."""
import datetime
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QScrollArea, QFrame, QDialog, QHeaderView, QInputDialog, QLabel, QListWidget,
                               QListWidgetItem, QMessageBox, QPlainTextEdit, QTableWidget, QTableWidgetItem, QTextBrowser,
                               QVBoxLayout, QWidget, QLineEdit, QSplitter)
from . import brew, encounter as enc, loot, reference
from .items import Token
from .panels import btn, check, combo, group, hint, hrow, ispin

RARITY_COLORS = {"common": "#d8d0c0", "uncommon": "#5fd35f", "rare": "#5aa0ff", "very rare": "#c070ff", "legendary": "#ff9a3c"}


def table(cols):
    t = QTableWidget(0, len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().hide()
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.ExtendedSelection)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    return t


def fill(t, rows, colors=None):
    t.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            it = QTableWidgetItem(str(val))
            if colors and colors[r]:
                it.setForeground(QColor(colors[r]))
            t.setItem(r, c, it)


def gp(v):
    return f"{v:,.0f}" if v >= 1 else (f"{v:g}" if v else "—")


# ---------- Loot ----------
class LootPanel(QScrollArea):
    def __init__(self, app):
        super().__init__()
        self.app, self.pending = app, []
        inner = QWidget()
        self.setWidget(inner)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        v = QVBoxLayout(inner)
        f = group("Roll treasure", v)
        self.source = combo(["Individual", "Hoard"], "Individual")
        self.tier = combo(loot.TIERS, loot.TIERS[0])
        self.diff = combo(list(loot.DIFFICULTY), "Medium")
        self.loc = combo(list(loot.LOCATIONS), "Dungeon")
        self.enemy = combo(list(loot.ENEMIES), "Humanoid")
        self.rarity = combo([r.title() for r in loot.RARITIES], "Legendary")
        self.table_box = QComboBox()
        self.coins = check("Include coins, gems and art", True, lambda _: None)
        f.addRow("Treasure", hrow(self.source, self.tier))
        f.addRow("Difficulty", hrow(self.diff, btn("From encounter", self.from_encounter, "Use the CR and difficulty of the Encounter tab")))
        f.addRow("Location", self.loc)
        f.addRow("Enemy type", self.enemy)
        f.addRow("Max rarity", self.rarity)
        f.addRow("Loot table", hrow(self.table_box, btn("Edit tables…", self.edit_tables)))
        f.addRow(self.coins)
        self.brewed = check("Include Brewery items", True, lambda _: None)
        f.addRow(self.brewed)
        f.addRow(btn("🎲 Roll loot", self.roll))
        self.results = table(["Item", "Value (gp)", "Rarity"])
        self.results.setMinimumHeight(170)
        v.addWidget(self.results, 1)
        self.who = QComboBox()
        self.who.setEditable(True)
        v.addWidget(hrow(QLabel("Give to"), self.who, btn("Give selected", self.give), btn("Give all", lambda: self.give(True))))
        v.addWidget(hrow(btn("Split coins evenly among PCs", self.split), btn("Discard", self.discard)))
        f = group("Reward history", v)
        self.filter = combo(["Everyone"], "Everyone", lambda _: self.show_history())
        f.addRow("Show", self.filter)
        self.history = table(["Item", "Value", "To", "When", "From"])
        self.history.setMinimumHeight(170)
        f.addRow(self.history)
        self.totals = hint("")
        f.addRow(self.totals)
        f.addRow(btn("Undo selected", self.undo))
        self.refresh()

    def refresh(self):
        """Re-read PCs, custom tables and history (after loading a campaign or adding PCs)."""
        names = [t.name for t in self.app.tokens if t.kind == "pc"]
        cur = self.who.currentText()
        self.who.clear()
        self.who.addItems(names + ["Party stash"])
        if cur:
            self.who.setCurrentText(cur)
        cur = self.table_box.currentText()
        self.table_box.clear()
        self.table_box.addItems(["Standard (built-in)"] + list(self.app.loot_tables))
        self.table_box.setCurrentText(cur)
        self.show_history()

    def from_encounter(self):
        foes = self.app.encounter_panel.foes()
        if not foes:
            self.app.statusBar().showMessage("No enemies found for the Encounter tab's source.", 4000)
            return
        top = max(enc.cr_value(t.cr) for t in foes)
        self.tier.setCurrentIndex(0 if top <= 4 else 1 if top <= 10 else 2 if top <= 16 else 3)
        rating = self.app.encounter_panel.last_rating
        self.diff.setCurrentText({"Low": "Easy", "Moderate": "Medium", "High": "Hard", "Beyond High (deadly)": "Deadly"}.get(rating, rating)
                                 if rating in ("Easy", "Medium", "Hard", "Deadly", "Low", "Moderate", "High", "Beyond High (deadly)") else "Medium")
        self.source.setCurrentText("Hoard" if len(foes) >= 4 or top >= 5 else "Individual")

    def roll(self):
        name = self.table_box.currentText()
        custom = loot.parse_table(self.app.loot_tables[name]) if name in self.app.loot_tables else None
        self.pending = loot.generate(self.tier.currentIndex(), self.source.currentText(), self.diff.currentText(),
                                     self.loc.currentText(), self.enemy.currentText(), self.rarity.currentText().lower(),
                                     custom, self.coins.isChecked(), extra=brew.loot_items() if self.brewed.isChecked() else ())
        self.show_pending()

    def show_pending(self):
        fill(self.results, [(i["name"], gp(i["value"]), i["rarity"].title()) for i in self.pending],
             [RARITY_COLORS.get(i["rarity"]) for i in self.pending])

    def give(self, everything=False):
        rows = range(len(self.pending)) if everything else sorted({i.row() for i in self.results.selectedIndexes()})
        to = self.who.currentText().strip() or "Party stash"
        src = f"{self.source.currentText()} · {self.tier.currentText()} · {self.loc.currentText()}"
        when = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        for r in sorted(rows, reverse=True):
            i = self.pending.pop(r)
            self.app.loot_history.append(dict(item=i["name"], value=i["value"], to=to, when=when, source=src, rarity=i["rarity"]))
        self.show_pending()
        self.show_history()

    def split(self):
        pcs = [t.name for t in self.app.tokens if t.kind == "pc"]
        coins = [i for i in self.pending if i["kind"] == "coins"]
        if not pcs or not coins:
            self.app.statusBar().showMessage("Need PC creatures on the map and coins in the loot.", 4000)
            return
        total = sum(i["value"] for i in coins)
        share = round(total / len(pcs), 2)
        when = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        for name in pcs:
            self.app.loot_history.append(dict(item=f"{share:,.2f} gp (coin share)", value=share, to=name, when=when, source="Coin split", rarity=""))
        self.pending = [i for i in self.pending if i["kind"] != "coins"]
        self.show_pending()
        self.show_history()

    def discard(self):
        self.pending = []
        self.show_pending()

    def shown(self):
        who = self.filter.currentText()
        return [h for h in self.app.loot_history if who == "Everyone" or h["to"] == who]

    def show_history(self):
        names = sorted({h["to"] for h in self.app.loot_history})
        cur = self.filter.currentText()
        self.filter.blockSignals(True)
        self.filter.clear()
        self.filter.addItems(["Everyone"] + names)
        self.filter.setCurrentText(cur if cur in names else "Everyone")
        self.filter.blockSignals(False)
        rows = self.shown()
        fill(self.history, [(h["item"], gp(h["value"]), h["to"], h["when"], h["source"]) for h in rows],
             [RARITY_COLORS.get(h.get("rarity")) for h in rows])
        sums = {}
        for h in self.app.loot_history:
            sums[h["to"]] = sums.get(h["to"], 0) + h["value"]
        self.totals.setText("  ·  ".join(f"{k}: {v:,.0f} gp" for k, v in sorted(sums.items())) or "No rewards handed out yet.")

    def undo(self):
        rows = self.shown()
        for r in sorted({i.row() for i in self.history.selectedIndexes()}, reverse=True):
            self.app.loot_history.remove(rows[r])
        self.show_history()

    def edit_tables(self):
        TableEditor(self.app, self).exec()
        self.refresh()


class TableEditor(QDialog):
    def __init__(self, app, parent):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("Custom loot tables")
        self.resize(700, 460)
        v = QVBoxLayout(self)
        v.addWidget(hint("One item per line:  weight | name | rarity | value in gp   — only the name is required. "
                         "Higher weight = more likely. Lines starting with # are comments."))
        split = QSplitter()
        self.list = QListWidget()
        self.list.addItems(list(app.loot_tables))
        self.list.currentTextChanged.connect(self.load)
        self.text = QPlainTextEdit()
        self.text.textChanged.connect(self.save)
        split.addWidget(self.list)
        split.addWidget(self.text)
        split.setSizes([180, 520])
        v.addWidget(split, 1)
        v.addWidget(hrow(btn("New table", self.new), btn("Delete", self.delete), btn("Close", self.accept)))
        self.text.setEnabled(False)
        if self.list.count():
            self.list.setCurrentRow(0)

    def load(self, name):
        self.text.blockSignals(True)
        self.text.setPlainText(self.app.loot_tables.get(name, ""))
        self.text.blockSignals(False)
        self.text.setEnabled(bool(name))

    def save(self):
        it = self.list.currentItem()
        if it:
            self.app.loot_tables[it.text()] = self.text.toPlainText()

    def new(self):
        name, ok = QInputDialog.getText(self, "New loot table", "Name (e.g. Underdark mushrooms)")
        if ok and name.strip() and name not in self.app.loot_tables:
            self.app.loot_tables[name.strip()] = ("# weight | name | rarity | value\n5 | Glowing mushroom | | 2\n"
                                                  "2 | Drow hand crossbow | uncommon | 150\n1 | Spider-silk cloak | rare | 2000\n")
            self.list.addItem(name.strip())
            self.list.setCurrentRow(self.list.count() - 1)

    def delete(self):
        it = self.list.currentItem()
        if it and QMessageBox.question(self, "Delete", f"Delete table '{it.text()}'?") == QMessageBox.Yes:
            del self.app.loot_tables[it.text()]
            self.list.takeItem(self.list.row(it))


# ---------- Encounter ----------
class EncounterPanel(QWidget):
    SOURCES = ["Creatures in initiative", "Selected creatures", "All creatures on the map"]

    def __init__(self, app):
        super().__init__()
        self.app, self.last_rating = app, ""
        v = QVBoxLayout(self)
        f = group("Party", v)
        self.use_pcs = check("Use the PC creatures on the map", True, lambda on: (self.size.setEnabled(not on), self.level.setEnabled(not on)))
        self.size, self.level = ispin(1, 10, 4), ispin(1, 20, 3)
        self.size.setEnabled(False)
        self.level.setEnabled(False)
        f.addRow(self.use_pcs)
        f.addRow("Or: size / level", hrow(self.size, self.level))
        f = group("Opposition", v)
        self.source = combo(self.SOURCES, self.SOURCES[0])
        f.addRow("Enemies from", self.source)
        f.addRow(hint("Set CR (monsters) and level (PCs) in the Inspector. Attack bonus and damage per round are "
                      "estimated from CR / level unless you fill them in. Allies fight on the party's side."))
        f = group("Simulation", v)
        self.res = combo(["fresh", "some used", "depleted"], "fresh")
        self.runs = ispin(100, 10000, 1000)
        f.addRow("Party resources", self.res)
        f.addRow("Battles to simulate", self.runs)
        v.addWidget(hrow(btn("⚖ Evaluate difficulty", self.evaluate), btn("⚔ Simulate", self.simulate)))
        self.out = QTextBrowser()
        v.addWidget(self.out, 1)

    def pool(self):
        src = self.source.currentText()
        if src == self.SOURCES[0]:
            return [t for t in self.app.tokens if t.in_combat and not t.dead]
        if src == self.SOURCES[1]:
            return [t for t in self.app.scene.selectedItems() if isinstance(t, Token) and not t.dead]
        return [t for t in self.app.tokens if not t.dead]

    def foes(self):
        return [t for t in self.pool() if t.kind == "enemy"]

    def party(self):
        """(levels for XP maths, combatants for the simulation)"""
        if not self.use_pcs.isChecked():
            s = enc.pc_stats(self.level.value())
            pcs = [enc.combatant(f"PC {i + 1}", "party", s["hp"], s["ac"], s["atk"], s["dpr"], s["attacks"]) for i in range(self.size.value())]
            return [self.level.value()] * self.size.value(), pcs
        pcs = [t for t in self.app.tokens if t.kind == "pc" and not t.dead]
        allies = [t for t in self.pool() if t.kind == "ally"]
        return [t.level for t in pcs], [self.fighter(t, "party") for t in pcs + allies]

    def fighter(self, t, side):
        s = enc.pc_stats(t.level) if t.kind == "pc" else enc.monster_stats(t.cr)
        return enc.combatant(t.name, side, t.hp, t.ac, t.atk or s["atk"], t.dpr or s["dpr"], s["attacks"])

    def evaluate(self):
        levels, _ = self.party()
        foes = self.foes()
        if not levels or not foes:
            self.out.setMarkdown("*Need at least one PC (or the manual party) and one enemy.*")
            return
        r = enc.rate(levels, [t.cr for t in foes], self.app.ruleset)
        self.last_rating = r["rating"]
        lines = [f"## {r['rating']}", f"*{self.app.ruleset} rules · party levels {', '.join(map(str, levels))}*", "",
                 f"**Monster XP:** {r['xp']:,}" + (f" × {r['mult']} for numbers = **{r['adjusted']:,.0f}**" if self.app.ruleset == "2014" else ""), ""]
        lines += [f"- {lab}: {val:,} XP" + ("  ◀" if lab == r["rating"] else "") for lab, val in r["thresholds"]]
        lines += ["", "**Enemies:** " + ", ".join(f"{t.name} (CR {enc.cr_norm(t.cr) or '?'})" for t in foes)]
        bad = [t.name for t in foes if enc.cr_norm(t.cr) is None]
        if bad:
            lines.append(f"\n⚠ No valid CR for: {', '.join(bad)} (counted as 0 XP)")
        self.out.setMarkdown("\n".join(lines))

    def simulate(self):
        _, party = self.party()
        foes = [self.fighter(t, "foe") for t in self.foes()]
        if not party or not foes:
            self.out.setMarkdown("*Need at least one PC (or the manual party) and one enemy.*")
            return
        s = enc.simulate(party, foes, self.runs.value(), self.res.currentText())
        v = enc.verdict(s)
        pct = lambda x: f"{x * 100:.0f}%"
        self.out.setMarkdown("\n".join([
            f"## Simulated: {v}", f"*{self.runs.value():,} battles · resources {self.res.currentText()}*", "",
            f"- Party wins: **{pct(s['win'])}**", f"- Total party kill: **{pct(s['tpk'])}**",
            f"- At least one PC drops: {pct(s['any_down'])} (avg {s['downs']:.1f} PCs)",
            f"- Average length: {s['rounds']:.1f} rounds", f"- Party HP left: {pct(s['hp_left'])}", "",
            "*A rough model: average stats, focus fire from the party, random monster targets, no healing, "
            "spells or tactics. Treat it as a smoke alarm for lethal or trivial fights.*"]))


# ---------- Rules reference ----------
class ReferencePanel(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        v = QVBoxLayout(self)
        self.q = QLineEdit()
        self.q.setPlaceholderText("Search spells, conditions, items, rules…")
        self.q.textChanged.connect(self.search)
        self.cat = combo(reference.CATEGORIES, "All", lambda _: self.search())
        v.addWidget(hrow(self.q, self.cat))
        split = QSplitter(Qt.Vertical)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.show)
        self.view = QTextBrowser()
        split.addWidget(self.list)
        split.addWidget(self.view)
        split.setSizes([260, 340])
        v.addWidget(split, 1)
        v.addWidget(hrow(btn("✚ Homebrew weapon", lambda: self.app.open_brewery("items", new=True), "Opens the Brewery"),
                         btn("✚ Homebrew creature", lambda: self.app.open_brewery("monsters", new=True), "Opens the Brewery")))
        v.addWidget(hrow(btn("✚ House rule", self.add), btn("Edit", self.edit, "Weapons and creatures open in the Brewery"),
                         btn("Delete", self.delete)))
        self.hits = []
        self.search()

    def search(self, *_):
        self.hits = reference.search(self.q.text(), self.cat.currentText(), self.app.homebrew)
        self.list.blockSignals(True)
        self.list.clear()
        for e in self.hits:
            it = QListWidgetItem(f"{e['name']}    ·  {e['meta'].split(' · ')[0]}")
            if e["cat"] == "Magic items":
                it.setForeground(QColor(RARITY_COLORS.get(e["meta"].split(" magic")[0].lower(), "#ccc")))
            self.list.addItem(it)
        self.list.blockSignals(False)
        self.list.setCurrentRow(0 if self.hits else -1)
        self.show(self.list.currentRow())

    def show(self, row):
        if not (0 <= row < len(self.hits)):
            self.view.setMarkdown("*Nothing found.*")
            return
        e = self.hits[row]
        md = f"## {e['name']}\n*{e['meta']}*\n\n{e['text']}\n"
        if e["note"]:
            md += f"\n**2024 rules:** {e['note']}\n"
        self.view.setMarkdown(md)

    def current_homebrew(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.hits) and self.hits[row]["cat"] == "Homebrew rules":
            return next(h for h in self.app.homebrew if h["name"] == self.hits[row]["name"])
        if 0 <= row < len(self.hits) and self.hits[row].get("brew"):  # Brewery entries are edited (and deleted) there
            self.app.open_brewery(*self.hits[row]["brew"])
            return None
        self.app.statusBar().showMessage("Only homebrew can be edited or deleted.", 4000)
        return None

    def ask(self, h=None):
        name, ok = QInputDialog.getText(self, "Homebrew", "Name", text=h["name"] if h else "")
        if not ok or not name.strip():
            return None
        text, ok = QInputDialog.getMultiLineText(self, "Homebrew", f"Rule text for {name}", h["text"] if h else "")
        return (name.strip(), text) if ok else None

    def add(self):
        got = self.ask()
        if got:
            self.app.homebrew.append(dict(name=got[0], text=got[1], meta="Homebrew rule"))
            self.q.setText(got[0])

    def edit(self):
        h = self.current_homebrew()
        got = h and self.ask(h)
        if got:
            h["name"], h["text"] = got
            self.search()

    def delete(self):
        h = self.current_homebrew()
        if h and QMessageBox.question(self, "Delete", f"Delete homebrew '{h['name']}'?") == QMessageBox.Yes:
            self.app.homebrew.remove(h)
            self.search()
