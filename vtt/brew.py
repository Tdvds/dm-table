"""The Brewery library: homebrew items, custom Forge objects and homebrew enemies, shared by every app.
Stored in one JSON file next to the program (brewery.json). No Qt here, so it is easy to test."""
import copy, json, os, re, sys, uuid

BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = os.path.join(BASE, "brewery.json")
_cache = {"mtime": None, "data": None}

ITEM_TYPES = ["Weapon", "Armor", "Shield", "Potion", "Ring", "Rod", "Scroll", "Staff", "Wand", "Wondrous item",
              "Ammunition", "Gear", "Trinket"]
RARITIES = ["common", "uncommon", "rare", "very rare", "legendary", "artifact"]
SIZES = {"Tiny": 0.5, "Small": 1, "Medium": 1, "Large": 2, "Huge": 3, "Gargantuan": 4}
CREATURE_TYPES = ["Aberration", "Beast", "Celestial", "Construct", "Dragon", "Elemental", "Fey", "Fiend", "Giant",
                  "Humanoid", "Monstrosity", "Ooze", "Plant", "Undead"]
ABILITIES = ["str", "dex", "con", "int", "wis", "cha"]

ITEM = dict(id="", name="New item", type="Wondrous item", subtype="", rarity="uncommon", attunement=False, attune_by="",
            value=0, weight=0.0, damage="", bonus=0, ac="", charges=0, recharge="", properties="", description="", img="")
OBJECT = dict(id="", name="New object", img="", alt_img="", base="statue", size=1.0, light=None, lit=True, toggle=False,
              sound="", anim="none", hidden=False, above=False, notes="")
MONSTER = dict(id="", name="New creature", size="Medium", type="Humanoid", alignment="unaligned", ac=12, ac_note="",
               hp=11, hit_dice="2d8+2", speed="30 ft.", str=10, dex=10, con=10, int=10, wis=10, cha=10, saves="", skills="",
               vulnerabilities="", resistances="", immunities="", condition_immunities="", senses="passive Perception 10",
               languages="—", cr="1/4", traits="", actions="", bonus_actions="", reactions="", legendary="",
               atk=0, dpr=0, color="#5a1a1a", img="")


def _m(name, size, typ, ac, ac_note, hp, dice, speed, ab, cr, senses, langs, actions, traits="", **kw):
    return dict(MONSTER, name=name, size=size, type=typ, ac=ac, ac_note=ac_note, hp=hp, hit_dice=dice, speed=speed,
                **dict(zip(ABILITIES, ab)), cr=cr, senses=senses, languages=langs, actions=actions, traits=traits, **kw)


# Starting points from the 5e SRD (CC-BY-4.0). Pick one, then change anything.
TEMPLATES = [
    _m("Kobold", "Small", "Humanoid", 12, "", 5, "2d6-2", "30 ft.", (7, 15, 9, 8, 7, 8), "1/8", "darkvision 60 ft., passive Perception 8",
       "Common, Draconic", "Dagger. +4 to hit, reach 5 ft. Hit: 4 (1d4 + 2) piercing.\nSling. +4 to hit, range 30/120 ft. Hit: 4 (1d4 + 2) bludgeoning.",
       "Sunlight Sensitivity. Disadvantage on attacks and sight Perception in sunlight.\nPack Tactics. Advantage on attacks if an ally is within 5 ft of the target."),
    _m("Bandit", "Medium", "Humanoid", 12, "leather armor", 11, "2d8+2", "30 ft.", (11, 12, 12, 10, 10, 10), "1/8", "passive Perception 10",
       "any one language", "Scimitar. +3 to hit, reach 5 ft. Hit: 4 (1d6 + 1) slashing.\nLight Crossbow. +3 to hit, range 80/320 ft. Hit: 5 (1d8 + 1) piercing."),
    _m("Cultist", "Medium", "Humanoid", 12, "leather armor", 9, "2d8", "30 ft.", (11, 12, 10, 10, 11, 10), "1/8", "passive Perception 10",
       "any one language", "Scimitar. +3 to hit, reach 5 ft. Hit: 4 (1d6 + 1) slashing.",
       "Dark Devotion. Advantage on saves against being charmed or frightened.", skills="Deception +2, Religion +2"),
    _m("Guard", "Medium", "Humanoid", 16, "chain shirt, shield", 11, "2d8+2", "30 ft.", (13, 12, 12, 10, 11, 10), "1/8",
       "passive Perception 12", "any one language", "Spear. +3 to hit, reach 5 ft. or range 20/60 ft. Hit: 4 (1d6 + 1) piercing, or 5 (1d8 + 1) two-handed.",
       skills="Perception +2"),
    _m("Goblin", "Small", "Humanoid", 15, "leather armor, shield", 7, "2d6", "30 ft.", (8, 14, 10, 10, 8, 8), "1/4",
       "darkvision 60 ft., passive Perception 9", "Common, Goblin",
       "Scimitar. +4 to hit, reach 5 ft. Hit: 5 (1d6 + 2) slashing.\nShortbow. +4 to hit, range 80/320 ft. Hit: 5 (1d6 + 2) piercing.",
       "Nimble Escape. Disengage or Hide as a bonus action.", skills="Stealth +6"),
    _m("Skeleton", "Medium", "Undead", 13, "armor scraps", 13, "2d8+4", "30 ft.", (10, 14, 15, 6, 8, 5), "1/4",
       "darkvision 60 ft., passive Perception 9", "understands the languages it knew in life but can't speak",
       "Shortsword. +4 to hit, reach 5 ft. Hit: 5 (1d6 + 2) piercing.\nShortbow. +4 to hit, range 80/320 ft. Hit: 5 (1d6 + 2) piercing.",
       vulnerabilities="bludgeoning", immunities="poison", condition_immunities="exhaustion, poisoned"),
    _m("Zombie", "Medium", "Undead", 8, "", 22, "3d8+9", "20 ft.", (13, 6, 16, 3, 6, 5), "1/4", "darkvision 60 ft., passive Perception 8",
       "understands the languages it knew in life but can't speak", "Slam. +3 to hit, reach 5 ft. Hit: 4 (1d6 + 1) bludgeoning.",
       "Undead Fortitude. If damage drops it to 0 HP, Con save (DC 5 + damage) to drop to 1 HP instead, unless radiant or a crit.",
       saves="Wis +0", immunities="poison", condition_immunities="poisoned"),
    _m("Wolf", "Medium", "Beast", 13, "natural armor", 11, "2d8+2", "40 ft.", (12, 15, 12, 3, 12, 6), "1/4", "passive Perception 13", "—",
       "Bite. +4 to hit, reach 5 ft. Hit: 7 (2d4 + 2) piercing. Target must succeed on a DC 11 Str save or be knocked prone.",
       "Keen Hearing and Smell. Advantage on Perception relying on hearing or smell.\nPack Tactics. Advantage on attacks if an ally is within 5 ft of the target.",
       skills="Perception +3, Stealth +4"),
    _m("Orc", "Medium", "Humanoid", 13, "hide armor", 15, "2d8+6", "30 ft.", (16, 12, 16, 7, 11, 10), "1/2",
       "darkvision 60 ft., passive Perception 10", "Common, Orc",
       "Greataxe. +5 to hit, reach 5 ft. Hit: 9 (1d12 + 3) slashing.\nJavelin. +5 to hit, reach 5 ft. or range 30/120 ft. Hit: 6 (1d6 + 3) piercing.",
       "Aggressive. As a bonus action, move up to its speed toward a hostile creature it can see.", skills="Intimidation +2"),
    _m("Hobgoblin", "Medium", "Humanoid", 18, "chain mail, shield", 11, "2d8+2", "30 ft.", (13, 12, 12, 10, 10, 9), "1/2",
       "darkvision 60 ft., passive Perception 10", "Common, Goblin",
       "Longsword. +3 to hit, reach 5 ft. Hit: 5 (1d8 + 1) slashing.\nLongbow. +3 to hit, range 150/600 ft. Hit: 5 (1d8 + 1) piercing.",
       "Martial Advantage. Once per turn, +7 (2d6) damage if an ally is within 5 ft of the target."),
    _m("Gnoll", "Medium", "Humanoid", 15, "hide armor, shield", 22, "5d8", "30 ft.", (14, 12, 11, 6, 10, 7), "1/2",
       "darkvision 60 ft., passive Perception 10", "Gnoll",
       "Bite. +4 to hit, reach 5 ft. Hit: 4 (1d4 + 2) piercing.\nSpear. +4 to hit, reach 5 ft. Hit: 5 (1d6 + 2) piercing.\n"
       "Longbow. +3 to hit, range 150/600 ft. Hit: 5 (1d8 + 1) piercing.",
       "Rampage. After dropping a creature to 0 HP with a melee attack, move half speed and bite as a bonus action."),
    _m("Bugbear", "Medium", "Humanoid", 16, "hide armor, shield", 27, "5d8+5", "30 ft.", (15, 14, 13, 8, 11, 9), "1",
       "darkvision 60 ft., passive Perception 10", "Common, Goblin",
       "Morningstar. +4 to hit, reach 5 ft. Hit: 11 (2d8 + 2) piercing.\nJavelin. +4 to hit, reach 5 ft. or range 30/120 ft. Hit: 9 (2d6 + 2) piercing in melee, 5 (1d6 + 2) at range.",
       "Brute. Melee weapons deal one extra die of damage (included).\nSurprise Attack. +7 (2d6) damage against a surprised creature in the first round.",
       skills="Stealth +6, Survival +2"),
    _m("Ghoul", "Medium", "Undead", 12, "", 22, "5d8", "30 ft.", (13, 15, 10, 7, 10, 6), "1", "darkvision 60 ft., passive Perception 10",
       "Common", "Bite. +2 to hit, reach 5 ft. Hit: 9 (2d8 + 2) piercing.\nClaws. +4 to hit, reach 5 ft. Hit: 7 (2d4 + 2) slashing. "
       "Non-elf, non-undead targets: DC 10 Con save or paralyzed for 1 minute (repeat at end of each turn).",
       immunities="poison", condition_immunities="charmed, exhaustion, poisoned"),
    _m("Giant Spider", "Large", "Beast", 14, "natural armor", 26, "4d10+4", "30 ft., climb 30 ft.", (14, 16, 12, 2, 11, 4), "1",
       "blindsight 10 ft., darkvision 60 ft., passive Perception 10", "—",
       "Bite. +5 to hit, reach 5 ft. Hit: 7 (1d8 + 3) piercing, plus DC 11 Con save: 9 (2d8) poison, half on a success.\n"
       "Web (Recharge 5–6). +5 to hit, range 30/60 ft. Hit: restrained (DC 12 Str to escape; web AC 10, 5 HP).",
       "Spider Climb. Climbs any surface, even ceilings.\nWeb Sense. Knows where anything touching its web is.\nWeb Walker. Ignores webs.",
       skills="Stealth +7"),
    _m("Ogre", "Large", "Giant", 11, "hide armor", 59, "7d10+21", "40 ft.", (19, 8, 16, 5, 7, 7), "2", "darkvision 60 ft., passive Perception 8",
       "Common, Giant", "Greatclub. +6 to hit, reach 5 ft. Hit: 13 (2d8 + 4) bludgeoning.\nJavelin. +6 to hit, reach 5 ft. or range 30/120 ft. Hit: 11 (2d6 + 4) piercing."),
    _m("Owlbear", "Large", "Monstrosity", 13, "natural armor", 59, "7d10+21", "40 ft.", (20, 12, 17, 3, 12, 7), "3",
       "darkvision 60 ft., passive Perception 13", "—",
       "Multiattack. One beak and one claws attack.\nBeak. +7 to hit, reach 5 ft. Hit: 10 (1d10 + 5) piercing.\nClaws. +7 to hit, reach 5 ft. Hit: 14 (2d8 + 5) slashing.",
       "Keen Sight and Smell. Advantage on Perception relying on sight or smell.", skills="Perception +3"),
    _m("Knight", "Medium", "Humanoid", 18, "plate", 52, "8d8+16", "30 ft.", (16, 11, 14, 11, 11, 15), "3", "passive Perception 10",
       "any one language", "Multiattack. Two melee attacks.\nGreatsword. +5 to hit, reach 5 ft. Hit: 10 (2d6 + 3) slashing.\n"
       "Heavy Crossbow. +2 to hit, range 100/400 ft. Hit: 5 (1d10) piercing.",
       "Brave. Advantage on saves against being frightened.", saves="Con +4, Wis +2",
       reactions="Parry. +2 AC against one melee attack that would hit, if wielding a melee weapon."),
    _m("Veteran", "Medium", "Humanoid", 17, "splint", 58, "9d8+18", "30 ft.", (16, 13, 14, 10, 11, 10), "3", "passive Perception 12",
       "any one language", "Multiattack. Two longsword attacks (and a shortsword attack if it has one drawn).\n"
       "Longsword. +5 to hit, reach 5 ft. Hit: 7 (1d8 + 3) slashing.\nShortsword. +5 to hit, reach 5 ft. Hit: 6 (1d6 + 3) piercing.\n"
       "Heavy Crossbow. +3 to hit, range 100/400 ft. Hit: 6 (1d10 + 1) piercing.", skills="Athletics +5, Perception +2"),
    _m("Wight", "Medium", "Undead", 14, "studded leather", 45, "6d8+18", "30 ft.", (15, 14, 16, 10, 13, 15), "3",
       "darkvision 60 ft., passive Perception 13", "the languages it knew in life",
       "Multiattack. Two longsword attacks or two longbow attacks; it can use Life Drain in place of one longsword attack.\n"
       "Life Drain. +4 to hit, reach 5 ft. Hit: 5 (1d6 + 2) necrotic; DC 13 Con save or its HP maximum drops by that much.\n"
       "Longsword. +4 to hit, reach 5 ft. Hit: 6 (1d8 + 2) slashing.\nLongbow. +4 to hit, range 150/600 ft. Hit: 6 (1d8 + 2) piercing.",
       "Sunlight Sensitivity. Disadvantage on attacks and sight Perception in sunlight.", skills="Perception +3, Stealth +4",
       resistances="necrotic; bludgeoning, piercing and slashing from nonmagical attacks that aren't silvered",
       immunities="poison", condition_immunities="exhaustion, poisoned"),
    _m("Troll", "Large", "Giant", 15, "natural armor", 84, "8d10+40", "30 ft.", (18, 13, 20, 7, 9, 7), "5",
       "darkvision 60 ft., passive Perception 12", "Giant",
       "Multiattack. One bite and two claw attacks.\nBite. +7 to hit, reach 5 ft. Hit: 7 (1d6 + 4) piercing.\nClaw. +7 to hit, reach 5 ft. Hit: 11 (2d6 + 4) slashing.",
       "Keen Smell. Advantage on Perception relying on smell.\nRegeneration. Regains 10 HP at the start of its turn unless it took acid or fire damage; dies only if it starts its turn at 0 HP and doesn't regenerate.",
       skills="Perception +2"),
    _m("Mage", "Medium", "Humanoid", 12, "15 with mage armor", 40, "9d8", "30 ft.", (9, 14, 11, 17, 12, 11), "6", "passive Perception 11",
       "any four languages", "Dagger. +5 to hit, reach 5 ft. or range 20/60 ft. Hit: 4 (1d4 + 2) piercing.",
       "Spellcasting. 9th-level caster (spell save DC 14, +6 to hit). Cantrips: fire bolt, light, mage hand, prestidigitation. "
       "1st (4): detect magic, mage armor, magic missile, shield. 2nd (3): misty step, suggestion. 3rd (3): counterspell, fireball, fly. "
       "4th (3): greater invisibility, ice storm. 5th (1): cone of cold.", saves="Int +6, Wis +4", skills="Arcana +6, History +6"),
    _m("Young Red Dragon", "Large", "Dragon", 18, "natural armor", 178, "17d10+85", "40 ft., climb 40 ft., fly 80 ft.",
       (23, 10, 21, 14, 11, 19), "10", "blindsight 30 ft., darkvision 120 ft., passive Perception 18", "Common, Draconic",
       "Multiattack. One bite and two claw attacks.\nBite. +10 to hit, reach 10 ft. Hit: 17 (2d10 + 6) piercing plus 3 (1d6) fire.\n"
       "Claw. +10 to hit, reach 5 ft. Hit: 13 (2d6 + 6) slashing.\n"
       "Fire Breath (Recharge 5–6). 30-ft cone, DC 17 Dex save: 56 (16d6) fire, half on a success.",
       saves="Dex +4, Con +9, Wis +4, Cha +8", skills="Perception +8, Stealth +4", immunities="fire", alignment="chaotic evil"),
]


def new(kind, **kw):
    return dict(copy.deepcopy({"items": ITEM, "objects": OBJECT, "monsters": MONSTER}[kind]), **kw, id=uuid.uuid4().hex[:8])


def load():
    """The whole library; re-read only when the file changed (other apps may have saved it)."""
    try:
        mtime = os.path.getmtime(FILE)
    except OSError:
        return {"items": [], "objects": [], "monsters": []}
    if _cache["mtime"] != (FILE, mtime):
        try:
            with open(FILE, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        defaults = {"items": ITEM, "objects": OBJECT, "monsters": MONSTER}
        _cache["data"] = {k: [dict(defaults[k], **e) for e in data.get(k, [])] for k in defaults}  # old files gain new fields
        _cache["mtime"] = (FILE, mtime)
    return _cache["data"]


def save(data):
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, FILE)  # atomic: a crash never leaves a half-written library
    _cache["mtime"] = None


def mod(score):
    return (int(score) - 10) // 2


def avg_dice(expr):
    """'17d10+85' -> 178 (the stat-block average). None if it can't be read."""
    m = re.fullmatch(r"\s*(\d+)\s*d\s*(\d+)\s*(?:([+-])\s*(\d+))?\s*", expr or "")
    if not m:
        return None
    n, d, sign, k = m.groups()
    return int(n) * (int(d) + 1) // 2 + (int(k) if k and sign == "+" else -int(k) if k else 0)


def token(mon):
    """Turns a homebrew enemy into token data for the table."""
    notes = "\n".join(x for x in (mon["traits"], mon["actions"], mon["bonus_actions"] and "Bonus: " + mon["bonus_actions"],
                                    mon["reactions"] and "Reactions: " + mon["reactions"], mon["legendary"] and "Legendary: " + mon["legendary"]) if x)
    return dict(name=mon["name"], kind="enemy", hp=int(mon["hp"]), max_hp=max(1, int(mon["hp"])), ac=int(mon["ac"]),
                init_mod=mod(mon["dex"]), cr=str(mon["cr"]), cells=SIZES.get(mon["size"], 1), color=mon["color"], img=mon["img"],
                atk=int(mon["atk"]), dpr=int(mon["dpr"]), notes=notes)


def bestiary():
    """Everything placeable on the table: your homebrew first (marked ✦), then the SRD templates."""
    key = lambda m: m["name"].lower()
    return [(f"✦ {m['name']}  ·  CR {m['cr']}", m) for m in sorted(load()["monsters"], key=key)] + \
           [(f"{m['name']}  ·  CR {m['cr']}", m) for m in sorted(TEMPLATES, key=key)]


def statblock(mon):
    """Markdown stat block for previews and the rules reference."""
    m = mon
    ab = " | ".join(f"**{a.upper()}** {m[a]} ({mod(m[a]):+d})" for a in ABILITIES)
    line = lambda label, key: f"**{label}** {m[key]}  \n" if m[key] else ""
    note = f" ({m['ac_note']})" if m["ac_note"] else ""
    out = (f"## {m['name']}\n*{m['size']} {m['type'].lower()}, {m['alignment']}*\n\n"
           f"**Armor Class** {m['ac']}{note}  \n"
           f"**Hit Points** {m['hp']} ({m['hit_dice']})  \n**Speed** {m['speed']}\n\n{ab}\n\n"
           + line("Saving Throws", "saves") + line("Skills", "skills") + line("Damage Vulnerabilities", "vulnerabilities")
           + line("Damage Resistances", "resistances") + line("Damage Immunities", "immunities")
           + line("Condition Immunities", "condition_immunities") + line("Senses", "senses") + line("Languages", "languages")
           + f"**Challenge** {m['cr']}\n")
    for title, key in (("", "traits"), ("Actions", "actions"), ("Bonus Actions", "bonus_actions"), ("Reactions", "reactions"),
                       ("Legendary Actions", "legendary")):
        if m[key].strip():
            out += (f"\n### {title}\n" if title else "\n") + "\n\n".join(f"***{p.split('.', 1)[0]}.***{p.split('.', 1)[1]}" if "." in p else p
                                                                         for p in m[key].strip().split("\n") if p.strip()) + "\n"
    return out


def itemcard(it):
    head = it["type"] + (f" ({it['subtype']})" if it["subtype"] else "")
    att = f" (requires attunement{' by ' + it['attune_by'] if it['attune_by'] else ''})" if it["attunement"] else ""
    facts = [f"**Bonus** +{it['bonus']}" if it["bonus"] else "", f"**Damage** {it['damage']}" if it["damage"] else "",
             f"**AC** {it['ac']}" if it["ac"] else "", f"**Charges** {it['charges']}" + (f" (regains {it['recharge']})" if it["recharge"] else "") if it["charges"] else "",
             f"**Properties** {it['properties']}" if it["properties"] else "", f"**Value** {it['value']:,} gp" if it["value"] else "",
             f"**Weight** {it['weight']:g} lb" if it["weight"] else ""]
    return f"## {it['name']}\n*{head}, {it['rarity']}{att}*\n\n" + "  \n".join(f for f in facts if f) + f"\n\n{it['description']}\n"


def loot_items():
    """Homebrew items in the loot generator's (name, rarity, tags, summary) shape. Artifacts never drop randomly."""
    return [(i["name"], i["rarity"], i["type"].lower(), i["description"][:120]) for i in load()["items"] if i["rarity"] in RARITIES[:5]]
