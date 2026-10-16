"""Self-check: python test_vtt.py  (runs headless)"""
import json, os, sys, tempfile, types
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
errors = []
import traceback
sys.excepthook = lambda *exc: (errors.append(exc), traceback.print_exception(*exc))  # Qt override errors land here too
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from vtt import brew, rules
brew.FILE = os.path.join(tempfile.mkdtemp(), "brewery.json")  # never touch the real library
from vtt.app import App

# ---- rules (pure) ----
mk = lambda **kw: types.SimpleNamespace(**{**dict(name="X", hp=20, max_hp=20, temp=0, kind="enemy", concentrating=False,
                                                conditions={}, dead=False), **kw})
t = mk(temp=5, concentrating=True)
log = rules.damage(t, 14, "normal")
assert t.temp == 0 and t.hp == 11 and any("DC 10" in m for m in log), log
t = mk(concentrating=True, hp=200, max_hp=200)
assert any("DC 30" in m for m in rules.damage(t, 70, "normal", "2024"))
t = mk(concentrating=True, hp=200, max_hp=200)
assert any("DC 35" in m for m in rules.damage(t, 70, "normal", "2014"))
t = mk()
rules.damage(t, 9, "resistant")
assert t.hp == 16
pc = mk(kind="pc", hp=5, max_hp=20, concentrating=True)
rules.damage(pc, 10)
assert pc.hp == 0 and "Unconscious" in pc.conditions and not pc.dead and not pc.concentrating
rules.heal(pc, 3)
assert pc.hp == 3 and "Unconscious" not in pc.conditions
pc = mk(kind="pc", hp=5, max_hp=10)
rules.damage(pc, 15)
assert pc.dead  # 10 left over after 0 HP >= max HP: massive damage
t = mk(temp=8)
rules.temp_hp(t, 5)
assert t.temp == 8
t = mk(conditions={"Poisoned": 2, "Prone": 0})
rules.start_turn(t)
assert t.conditions == {"Poisoned": 1, "Prone": 0}
rules.start_turn(t)
assert t.conditions == {"Prone": 0}
assert rules.sky(12)[0] == 0 and rules.sky(0)[0] > 0.7 and rules.sky(6.5)[1] == "#ff783c"

# ---- encounter maths ----
from vtt import encounter as enc, loot, reference
assert enc.cr_norm("0.25") == "1/4" and enc.xp_for("1/4") == 50 and enc.cr_norm("banana") is None
r = enc.rate([3, 3, 3, 3], ["1/4"] * 6, "2014")  # 6 goblins: 300 XP x2 = 600 vs 4x lvl3 (300/600/900/1600)
assert r["adjusted"] == 600 and r["rating"] == "Medium", r
r = enc.rate([3, 3, 3, 3], ["1/4"] * 6, "2024")  # 300 XP vs 600/900/1600 -> below Low
assert r["adjusted"] == 300 and r["rating"] == "Trivial", r
assert enc.rate([1], ["5"], "2014")["rating"] == "Deadly"
pcs = [enc.combatant(f"P{i}", "party", **{k: v for k, v in enc.pc_stats(5).items()}) for i in range(4)]
easy = enc.simulate(pcs, [enc.combatant("G", "foe", **enc.monster_stats("1/4"))] * 3, 300, seed=1)
dead = enc.simulate(pcs, [enc.combatant("D", "foe", **enc.monster_stats("13"))], 300, seed=1)
assert easy["win"] > 0.99 and enc.verdict(easy) in ("Trivial", "Easy"), easy
assert dead["win"] < 0.3 and enc.verdict(dead) == "Lethal", dead

# ---- loot ----
for tier in range(4):
    for src in ("Individual", "Hoard"):
        items = loot.generate(tier, src, "Hard", "Crypt", "Undead", seed=tier)
        assert all(i["rarity"] in ("",) + tuple(loot.RARITIES) for i in items)
hoard = loot.generate(1, "Hoard", "Medium", "Dungeon", "Dragon", max_rarity="uncommon", seed=5)
assert any(i["kind"] == "coins" for i in hoard) and all(i["rarity"] in ("", "common", "uncommon") for i in hoard), hoard
t = loot.parse_table("# comment\n5 | Glow shroom | | 2\nRusty key\n2 | Drow crossbow | uncommon | x")
assert [(r["name"], r["weight"], r["value"]) for r in t] == [("Glow shroom", 5, 2), ("Rusty key", 1, 0), ("Drow crossbow", 2, 0)]
custom = loot.generate(0, "Hoard", custom=t, coins=False, seed=2)
assert custom and all(i["name"] in ("Glow shroom", "Rusty key", "Drow crossbow") or i["kind"] == "trinket" for i in custom), custom

# ---- reference ----
assert reference.search("fireball")[0]["name"] == "Fireball"
assert reference.search("", "Conditions")[0]["cat"] == "Conditions"
assert reference.search("moonshine", homebrew=[{"name": "Moonshine rule", "text": "Drunk."}])[0]["cat"] == "Homebrew rules"

# ---- app ----
app = QApplication([])
d = tempfile.mkdtemp()
img = QImage(1000, 500, QImage.Format_RGB32)
img.fill(Qt.darkGreen)
mp = os.path.join(d, "map.png")
img.save(mp)

w = App(d, load_last=False)
w.show()
w.display.show()
w.display.resize(800, 600)
app.processEvents()

# real mouse events, before any map is loaded (the reported bugs)
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QMouseEvent
vp = w.admin.viewport()


def mouse(kind, pos, btn=Qt.LeftButton, btns=Qt.LeftButton):
    p = QPointF(pos)
    QApplication.sendEvent(vp, QMouseEvent(kind, p, vp.mapToGlobal(p), btn, btns, Qt.NoModifier))


def drag(a, b):
    mouse(QEvent.MouseButtonPress, a)
    for i in range(1, 6):
        mouse(QEvent.MouseMove, a + (b - a) * i / 5, Qt.NoButton)
    mouse(QEvent.MouseButtonRelease, b, Qt.LeftButton, Qt.NoButton)


gob = w.add_token({"name": "Gob"}, QPointF(0, 0))
start = QPointF(gob.pos())
at = w.admin.mapFromScene(gob.pos())
drag(at, at + QPoint(80, 0))
assert gob.pos() != start and gob.isSelected(), "enemy can't be dragged"
c0 = QPointF(w.center)
drag(QPoint(30, 30), QPoint(70, 50))
assert w.center != c0, "map can't be panned after adding an enemy"
w.set_tool("reveal")
at = w.admin.mapFromScene(QPointF(300, 0))
drag(at, at + QPoint(10, 0))
px = (QPointF(300, 0) - w.fog.rect.topLeft()) * w.fog.f()
assert w.fog.on and w.fog.img.pixelColor(int(px.x()), int(px.y())).alpha() == 0, "fog brush does nothing without a map"
w.set_tool("select")
w.set_darkness(70)
w.lighting.rebuild(0)
assert w.lighting.enabled and w.lighting.img.pixelColor(5, 5).alpha() > 150, "darkness slider does nothing"
g2, g3 = w.add_token({"name": "G"}), w.add_token({"name": "G"})
assert g2.pos() != g3.pos(), "new creatures stack on top of each other"
w.delete([gob, g2, g3])
w.fog.on = False
w.set_lighting(False)
w.open_map(mp)
assert w.map_rect() == QRectF(0, 0, 1000, 500)
assert abs(w.s - 0.8) < 1e-9 and w.center == QPointF(500, 250)
P = QPointF(100, 100)
before = (P - w.center) * w.s
w.zoom_at(P, 2)
after = (P - w.center) * w.s
assert abs(before.x() - after.x()) < 1e-6 and abs(before.y() - after.y()) < 1e-6
w.fit()
w.grid.size, w.grid.ox = 50, 10
assert w.snapped(QPointF(37, 80), 1) == QPointF(35, 75) and w.snapped(QPointF(37, 80), 2) == QPointF(60, 100)

# fog + secret passage: lever reveals hidden wall section and lifts fog over it
w.fog.on = True
w.fog.fill(True)
wall = w.add_prop({"name": "Secret door", "hidden": True, "tag": "secret"}, QPointF(500, 250))
lever = w.add_prop({"name": "Lever", "reveals": "secret", "anim": "shake"}, QPointF(100, 100))
door = w.add_prop({"name": "Door", "toggle": True}, QPointF(300, 300))
w.trigger(lever)
assert not wall.hidden and w.fog.img.pixelColor(500, 250).alpha() == 0 and w.fog.img.pixelColor(5, 5).alpha() == 255
w.trigger(door)
assert door.opened and door.gone()

# initiative
w.ruleset = "2024"
a = w.add_token({"name": "Hero", "kind": "pc", "hp": 12, "max_hp": 12, "init": 18, "in_combat": True})
b = w.add_token({"name": "Orc", "hp": 15, "max_hp": 15, "init": 12, "in_combat": True, "conditions": {"Poisoned": 1}})
c = w.add_token({"name": "Rat", "hp": 1, "max_hp": 1, "init": 5, "in_combat": True, "dead": True})
w.combat.next_turn()
assert w.active_id == a.id and w.round == 1
w.combat.next_turn()
assert w.active_id == b.id and "Poisoned" not in b.conditions
w.combat.next_turn()  # dead rat is skipped, wraps to round 2
assert w.active_id == a.id and w.round == 2, (w.active_id, w.round)

# lighting: torch cuts the darkness near it
w.set_lighting(True)
w.auto_sky = False
w.lighting.darkness = 0.9
torch = w.add_prop({"icon": "light", "light": rules.light("Torch")}, QPointF(800, 250))
w.lighting.rebuild(0)
f = w.lighting.img.width() / 1000
assert w.lighting.img.pixelColor(int(800 * f), int(250 * f)).alpha() < 30 < w.lighting.img.pixelColor(5, 5).alpha()

# weather + journal + handout, then paint everything once
w.set_weather("Storm", 0.8)
w.weather.step(0.1)
assert len(w.weather.parts) == int(700 * 0.8)
w.journal_panel.make("Old Tom", "NPC")["body"] = "Gives the [[Lost Ring]] quest."
w.show_handout(mp)
for kind in ("Rain", "Snow", "Fog", "Ash", "Magic", "Sandstorm", "Storm"):
    w.set_weather(kind)
    w.weather.step(0.05)
    w.admin.grab()
    w.display.grab()
w.show_handout(None)

# DM tool panels: encounter from initiative, loot handed out, homebrew rule
b.cr = "2"
w.encounter_panel.evaluate()
assert "Orc (CR 2)" in w.encounter_panel.out.toPlainText()
w.encounter_panel.simulate()
assert "Party wins" in w.encounter_panel.out.toPlainText()
w.loot_panel.from_encounter()
w.loot_panel.roll()
assert w.loot_panel.pending
w.loot_panel.who.setCurrentText("Hero")
w.loot_panel.give(True)
assert w.loot_history and all(h["to"] == "Hero" for h in w.loot_history) and not w.loot_panel.pending
w.loot_tables["Mushrooms"] = "3 | Glow shroom | | 2"
w.homebrew.append({"name": "Flanking", "text": "Advantage when flanking.", "meta": "Homebrew"})

# Sounds tab: playlists, track flow and soundboard pads
import wave
from PySide6.QtMultimedia import QMediaPlayer
waves = []
for k in range(3):
    wp = os.path.join(d, f"tone{k}.wav")
    with wave.open(wp, "wb") as wf:
        wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(8000), wf.writeframes(b"\x00\x10" * 800)
    waves.append(wp)
S = w.sounds_panel
src = lambda: os.path.normpath(S.music.source().toLocalFile())  # Qt gives forward slashes
S.add_tracks(waves[:2])
S.playlists["Battle"] = []
S.current = "Battle"
S.fill_playlists()
S.add_tracks([waves[2]])
S.play_index(0, "Battle")
assert S.playing_list == "Battle" and src() == waves[2]
S.current = "Ambience"
S.fill_playlists()
S.play_index(0, "Ambience")
S.next()
assert S.index == 1 and src() == waves[1]
S.repeat.setCurrentText("Repeat track")
S.media_status(QMediaPlayer.MediaStatus.EndOfMedia)
assert S.index == 1  # same song again
S.repeat.setCurrentText("Repeat playlist")
S.media_status(QMediaPlayer.MediaStatus.EndOfMedia)
assert S.index == 0  # wrapped around
S.show_playlist("Ambience")
S.tracks.addItem(S.tracks.takeItem(0))  # like dragging the first song to the end
S.sync_order()
assert S.playlists["Ambience"][S.index] == waves[0]  # reordering keeps pointing at the playing song
S.add_pads([waves[0], waves[1]])
S.edit_pad(S.pads[1], "loop", True)
S.play_pad(S.pads[0])
S.play_pad(S.pads[1])
assert len(S.pad_players) == 2 and S.pad_players[S.pads[1]["id"]][0].loops() == QMediaPlayer.Loops.Infinite
assert S.pad_buttons[S.pads[1]["id"]].text().startswith("↻")
S.stop_all()

# save / load round trip
path = os.path.join(d, "camp.json")
w.save_campaign(path)
w2 = App(d, load_last=False)
w2.load_campaign(path)
assert w2.map_path == mp and len(w2.tokens) == 3 and len(w2.props) == 4 and w2.fog.on
assert w2.fog.img.pixelColor(500, 250).alpha() == 0 and w2.fog.img.pixelColor(5, 5).alpha() == 255
assert w2.active_id == a.id and w2.round == 2 and w2.journal[0]["title"] == "Old Tom" and w2.weather.kind == "Storm"
assert next(p for p in w2.props if p.name == "Door").opened and w2.lighting.enabled
assert len(w2.loot_history) == len(w.loot_history) and "Mushrooms" in w2.loot_tables and w2.homebrew[0]["name"] == "Flanking"
assert next(t for t in w2.tokens if t.name == "Orc").cr == "2"
S2 = w2.sounds_panel
assert set(S2.playlists) == {"Ambience", "Battle"} and len(S2.pads) == 2 and S2.pads[1]["loop"] and S2.pl_box.count() == 2
w2.admin.grab()

# ---- Map Forge ----
from vtt import forge_gen as fg, forge_draw as fdraw
from vtt.launcher import Launcher
g = fg.parse(["ab"[0:0] + ".#", "~.", "D "])
assert len(fg.rotate(g)) == 2 and len(fg.rotate(g)[0]) == 3
r4 = g
for _ in range(4):
    r4 = fg.rotate(r4)
assert r4 == g and fg.flip(fg.flip(g)) == g and g[2][1] is None and g[2][0] == (fg.FLOOR, "door")
walk = lambda m: (lambda x, y: m.t[y][x] not in (fg.VOID, fg.LAVA, fg.PIT, fg.WATER))
for seed in range(12):
    m = fg.gen_dungeon(40, 30, seed)
    objs = [o for row in m.o for o in row]
    assert "stairs_up" in objs and "stairs_down" in objs, seed
    start = next((x, y) for y in range(m.h) for x in range(m.w) if m.o[y][x] == "stairs_up")
    reach = m.flood(*start, walk(m))
    open_cells = {(x, y) for y in range(m.h) for x in range(m.w) if walk(m)(x, y)}
    assert open_cells <= set(reach) | {start}, f"dungeon seed {seed}: {len(open_cells - set(reach))} unreachable cells"
    c = fg.gen_caves(40, 30, seed)
    cells = [(x, y) for y in range(c.h) for x in range(c.w) if c.t[y][x] != fg.VOID]
    assert cells and len(c.flood(*cells[0], lambda x, y: c.t[y][x] != fg.VOID)) == len(cells), f"caves seed {seed} split"
wl = fg.gen_wilds(40, 30, 3)
kinds = {t for row in wl.t for t in row}
assert {fg.WATER, fg.DIRT, fg.WOOD} <= kinds, kinds
assert fg.MapData.from_dict(json.loads(json.dumps(wl.to_dict()))).t == wl.t
assert fg.gen_dungeon(20, 15, 5).t == fg.gen_dungeon(20, 15, 5).t  # same seed, same map
fdraw.render(fg.gen_dungeon(20, 15, 1), 12, True)
for k in fg.OBJECTS:
    fdraw.object_image(k, 32)
for c in fg.BUILTIN:
    fdraw.chunk_image(c["g"], 8)

L = Launcher(d, {"data_dir": d, "load_last": False})
F = L.open_forge()
F.kind.setCurrentText("Dungeon")
F.seed.setValue(7)
F.generate(False)
F.set_tool("erase")
F.press(1, 1); F.drag(5, 1); F.release(5, 1)
F.set_tool("room")
F.terrain = fg.FLOOR
F.press(1, 1); F.drag(4, 3); F.release(4, 3)
assert all(F.m.t[y][x] == fg.FLOOR for y in range(1, 4) for x in range(1, 5))
F.undo()
assert F.m.t[2][2] == fg.VOID
F.redo()
F.chunk = next(c["g"] for c in fg.BUILTIN if c["name"] == "Treasure vault")
F.set_tool("chunk")
F.press(10, 10)
assert any(F.m.o[y][x] == "chest" for y in range(7, 14) for x in range(7, 14))
live = sum(o in ("door", "chest", "torch", "trap") for row in F.m.o for o in row)
F.send_to_table()
T = L.table
assert T is not None and T.map_path.endswith(".png") and T.grid.size == 70 and T.grid.on
assert len(T.props) == live, (len(T.props), live)
door = next((p for p in T.props if p.name == "Door"), None)
if door:
    T.trigger(door)
    assert door.opened
F.dirty = False
F.close()
assert L.forge is None
# ---- Brewery ----
from vtt import loot as lt, reference as ref
from vtt.brewery import Brewery
assert brew.avg_dice("17d10+85") == 178 and brew.avg_dice("2d6") == 7 and brew.avg_dice("3d8-2") == 11 and brew.avg_dice("x") is None
assert brew.mod(14) == 2 and brew.mod(7) == -2
gob = next(t for t in brew.TEMPLATES if t["name"] == "Goblin")
tk = brew.token(gob)
assert (tk["hp"], tk["ac"], tk["init_mod"], tk["cr"], tk["cells"]) == (7, 15, 2, "1/4", 1) and "Nimble Escape" in tk["notes"]
assert all(brew.avg_dice(t["hit_dice"]) == t["hp"] for t in brew.TEMPLATES), [t["name"] for t in brew.TEMPLATES if brew.avg_dice(t["hit_dice"]) != t["hp"]]
assert "***Scimitar.***" in brew.statblock(gob) and "**Challenge** 1/4" in brew.statblock(gob)

L2 = Launcher(d, {"data_dir": d, "load_last": False})
T2, F2, B = L2.open_table(), L2.open_forge(), L2.open_brewery()
B.items.new()
it = B.items.current()
it.update(name="Frostbite Dagger", rarity="rare", type="Weapon", description="Cold as the grave.")
B.objects.new()
ob = B.objects.current()
ob.update(name="Blue brazier", base="campfire", light=dict(rules.light("Arcane glow"), color="#3366ff"), toggle=True)
B.monsters.add(dict(gob, id="g0b11n", name="Goblin Boss"))
mon = B.monsters.current()
mon["cr"], mon["size"] = "5", "Large"
B.auto_stats()
assert mon["ac"] == 14 and mon["hp"] == brew.avg_dice(mon["hit_dice"]) and mon["hit_dice"].startswith("") and "d10" in mon["hit_dice"]
B.flush()  # saves and tells the other open apps
assert os.path.isfile(brew.FILE)
lib = brew.load()
assert [i["name"] for i in lib["items"]] == ["Frostbite Dagger"] and lib["objects"][0]["light"]["color"] == "#3366ff"
assert any(e["name"] == "Goblin Boss" and e["cat"] == "Homebrew creatures" for e in ref.search("goblin boss"))
assert any(e["name"] == "Frostbite Dagger" and e["cat"] == "Homebrew weapons" for e in ref.search("frostbite"))
assert any(x["name"] == "Frostbite Dagger" for s_ in range(40)
           for x in lt.generate(2, "Hoard", "Deadly", max_rarity="rare", seed=s_, extra=brew.loot_items()))
assert any(F2.object_list.item(i).data(Qt.UserRole) == "brew:" + ob["id"] for i in range(F2.object_list.count()))
F2.m = fg.MapData(10, 8, fill=fg.FLOOR, seed=1)
F2.m.o[3][3] = "brew:" + ob["id"]
F2.full_render()
labels = [T2.beasts.itemText(i) for i in range(T2.beasts.count())]
assert labels[0] == "✦ Goblin Boss  ·  CR 5" and "Troll  ·  CR 5" in labels  # homebrew first, then SRD
T2.beasts.completer().setCompletionPrefix("boss")  # search matches the middle of names
assert T2.beasts.completer().completionCount() == 1
T2.beasts.setCurrentText("Troll  ·  CR 5")
T2.place_beast()
assert T2.tokens[-1].name == "Troll" and T2.tokens[-1].max_hp == 84 and not T2.tokens[-1].img
T2.library["tokens"] = [mp]
T2.fill_lib("tokens")
T2.lib_widgets["tokens"].setCurrentRow(0)  # pick an image first...
T2.place_beast()
assert T2.tokens[-1].name == "Troll 2" and T2.tokens[-1].img == mp  # ...and the placed monster wears it
T2.add_token(T2.quick_token())
assert T2.tokens[-1].img == mp
T2.lib_widgets["tokens"].clearSelection()
T2.place_beast()
assert not T2.tokens[-1].img
T2.add_beast(mon)
boss = T2.tokens[-1]
assert boss.name == "Goblin Boss" and boss.cr == "5" and boss.cells == 2 and boss.max_hp == mon["hp"]
F2.send_to_table()
brazier = next(p for p in T2.props if p.name == "Blue brazier")
assert brazier.light["color"] == "#3366ff" and brazier.toggle and brazier.cells == 1
T2.trigger(brazier)
assert not brazier.lit  # triggering the light switches it off
RP = T2.reference_panel
RP.cat.setCurrentText("Homebrew creatures")
RP.q.setText("goblin boss")
RP.edit()  # Edit on a Brewery entry jumps to it in the Brewery
assert B.centralWidget().currentIndex() == 2 and B.monsters.current()["id"] == mon["id"]
RP.app.open_brewery("items", new=True)
assert B.centralWidget().currentIndex() == 0 and B.items.current()["type"] == "Weapon"
B.timer.stop()
B.close()
T2.admin.grab()
assert not errors, errors
print("ok")
