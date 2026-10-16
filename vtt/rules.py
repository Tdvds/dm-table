"""D&D 5e (2014) / 5.5e (2024) data and pure combat math. No Qt here, so it is easy to test."""
import random

# name: (badge, colour, 2014 summary, 2024 summary or None when unchanged). Summaries are short paraphrases.
CONDITIONS = {
    "Blinded": ("Bl", "#7f8c8d", "Can't see; fails sight checks. Attacks against it have advantage, its attacks have disadvantage.", None),
    "Charmed": ("Ch", "#e84393", "Can't attack the charmer; the charmer has advantage on social checks against it.", None),
    "Deafened": ("De", "#95a5a6", "Can't hear; fails hearing checks.", None),
    "Frightened": ("Fr", "#8e44ad", "Disadvantage on checks and attacks while the source is in sight; can't move closer to it.", None),
    "Grappled": ("Gr", "#d35400", "Speed 0.", "Speed 0; disadvantage on attacks against anyone but the grappler; can be dragged."),
    "Incapacitated": ("In", "#c0392b", "Can't take actions or reactions.",
                      "No actions, bonus actions or reactions; concentration breaks; can't speak; disadvantage on initiative."),
    "Invisible": ("Iv", "#74b9ff", "Can't be seen without magic; its attacks have advantage, attacks against it disadvantage.",
                  "As before, plus advantage on initiative; unaffected by effects that need to see it."),
    "Paralyzed": ("Pa", "#f1c40f", "Incapacitated, can't move or speak; fails Str/Dex saves; attacks have advantage; hits within 5 ft are crits.", None),
    "Petrified": ("Pe", "#636e72", "Turned to stone; incapacitated; resistance to all damage; immune to poison and disease.", None),
    "Poisoned": ("Po", "#27ae60", "Disadvantage on attack rolls and ability checks.", None),
    "Prone": ("Pr", "#a0522d", "Can only crawl; disadvantage on attacks; attacks within 5 ft have advantage, beyond that disadvantage.", None),
    "Restrained": ("Re", "#e67e22", "Speed 0; disadvantage on attacks and Dex saves; attacks against it have advantage.", None),
    "Stunned": ("St", "#fdcb6e", "Incapacitated, can't move, speaks falteringly; fails Str/Dex saves; attacks against it have advantage.",
                "Incapacitated; fails Str/Dex saves; attacks against it have advantage."),
    "Unconscious": ("Un", "#2d3436", "Incapacitated, prone, drops what it holds; fails Str/Dex saves; attacks have advantage; hits within 5 ft are crits.", None),
    "Exhaustion": ("Ex", "#6c5ce7", "Levels 1-6: disadvantage on checks, half speed, disadvantage on attacks and saves, HP max halved, speed 0, death.",
                   "Each level: -2 to d20 tests and -5 ft speed. Level 6: death."),
}
CONCENTRATION = ("Co", "#9b59b6")


def badge(name):
    c = CONDITIONS.get(name)
    return (c[0], c[1]) if c else (name[:2].title(), "#555555")  # custom conditions


def summary(name, ruleset):
    c = CONDITIONS.get(name)
    if not c:
        return "Custom condition"
    return (c[3] or c[2]) if ruleset == "2024" else c[2]


# name: (bright ft, extra dim ft, colour, flicker strength)
LIGHTS = {
    "Candle": (5, 5, "#ffb35c", 1.0), "Torch": (20, 20, "#ff9a3c", 1.0), "Lantern": (30, 30, "#ffc070", 0.3),
    "Campfire": (20, 20, "#ff7a2a", 1.2), "Light cantrip": (20, 20, "#fff1d0", 0.0), "Daylight spell": (60, 60, "#ffffff", 0.0),
    "Arcane glow": (15, 15, "#5aa0ff", 0.2), "Fey light": (10, 10, "#c070ff", 0.3), "Hellfire": (15, 15, "#ff3030", 0.8),
    "Necrotic glow": (10, 10, "#60ff90", 0.3),
}


def light(name):
    b, d, c, f = LIGHTS[name]
    return {"preset": name, "bright": b, "dim": d, "color": c, "flicker": f}


# hour, darkness 0..1, tint colour of the darkness
SKY = [(0, .85, (10, 16, 48)), (5, .8, (16, 20, 56)), (6.5, .4, (255, 120, 60)), (8, 0, (255, 220, 180)),
       (17, 0, (255, 220, 180)), (19, .4, (255, 100, 40)), (20.5, .75, (20, 22, 64)), (24, .85, (10, 16, 48))]


def sky(hour):
    h = hour % 24
    for (h0, d0, c0), (h1, d1, c1) in zip(SKY, SKY[1:]):
        if h0 <= h <= h1:
            t = (h - h0) / (h1 - h0)
            return d0 + (d1 - d0) * t, "#%02x%02x%02x" % tuple(round(a + (b - a) * t) for a, b in zip(c0, c1))


def time_name(hour):
    h = hour % 24
    for limit, name in ((5, "Deep night"), (7, "Dawn"), (11, "Morning"), (14, "Midday"), (18, "Afternoon"), (20.5, "Dusk"), (23, "Evening")):
        if h < limit:
            return name
    return "Deep night"


def roll_init(t):
    return random.randint(1, 20) + t.init_mod


def bloodied(t):
    return 0 < t.hp <= t.max_hp / 2


def damage(t, amount, mode="normal", ruleset="2024"):
    """Apply damage to anything with hp/max_hp/temp/kind/concentrating/conditions/dead/name. Returns log lines."""
    amt = {"normal": amount, "resistant": amount // 2, "vulnerable": amount * 2, "immune": 0}[mode]
    soak = min(t.temp, amt)
    t.temp -= soak
    rest = amt - soak
    before = t.hp
    t.hp = max(0, t.hp - rest)
    log = [f"{t.name} takes {amt} damage" + (f" ({mode})" if mode != "normal" else "")
           + (f", {soak} absorbed by temp HP" if soak else "") + f" → {t.hp}/{t.max_hp} HP"]
    if amt and t.concentrating and t.hp > 0:
        dc = max(10, amt // 2)
        if ruleset == "2024":
            dc = min(dc, 30)
        log.append(f"⚠ {t.name}: Constitution save DC {dc} to keep concentration")
    if t.hp == 0 and before > 0:
        if t.kind == "pc":
            if rest - before >= t.max_hp:
                t.dead = True
                log.append(f"☠ {t.name} is killed outright by massive damage")
            else:
                t.conditions["Unconscious"] = 0
                log.append(f"{t.name} falls unconscious - death saving throws begin")
        else:
            t.dead = True
            log.append(f"☠ {t.name} is slain")
        if t.concentrating:
            t.concentrating = False
            log.append(f"{t.name} loses concentration")
    elif before == 0 and amt and t.kind == "pc" and not t.dead:
        log.append(f"⚠ {t.name} is hit at 0 HP: one failed death save (two on a critical hit)")
    return log


def heal(t, amount):
    if t.dead:
        return [f"{t.name} is dead and can't be healed"]
    was_down = t.hp == 0
    t.hp = min(t.max_hp, t.hp + amount)
    log = [f"{t.name} heals {amount} → {t.hp}/{t.max_hp} HP"]
    if was_down and t.hp > 0 and t.conditions.pop("Unconscious", None) is not None:
        log.append(f"{t.name} regains consciousness")
    return log


def temp_hp(t, amount):
    if amount <= t.temp:
        return [f"{t.name} keeps {t.temp} temp HP (temp HP doesn't stack)"]
    t.temp = amount
    return [f"{t.name} gains {amount} temp HP"]


def start_turn(t):
    """Counts down timed conditions (0 = no duration) and returns reminders."""
    log = []
    for name, left in list(t.conditions.items()):
        if left > 0:
            if left == 1:
                del t.conditions[name]
                log.append(f"{name} ends on {t.name}")
            else:
                t.conditions[name] = left - 1
    if t.kind == "pc" and t.hp == 0 and not t.dead:
        log.append(f"🎲 {t.name} makes a death saving throw")
    if t.concentrating:
        log.append(f"{t.name} is concentrating")
    return log
