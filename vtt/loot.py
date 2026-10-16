"""Treasure generation by challenge, difficulty, location, enemy type and rarity, plus custom loot tables. No Qt."""
import random

RARITIES = ["common", "uncommon", "rare", "very rare", "legendary"]
VALUE = {"common": 100, "uncommon": 400, "rare": 4000, "very rare": 40000, "legendary": 200000}
TIERS = ["CR 0–4", "CR 5–10", "CR 11–16", "CR 17+"]
DIFFICULTY = {"Easy": 0.75, "Medium": 1.0, "Hard": 1.3, "Deadly": 1.6}
LOCATIONS = {"Dungeon": "combat", "Crypt": "holy undead", "Cave": "utility", "Forest": "nature", "City": "stealth social",
             "Castle": "combat social", "Dragon lair": "fire dragon", "Coast / ship": "water", "Arcane tower": "arcane",
             "Temple": "holy healing"}
ENEMIES = {"Humanoid": ("combat social", 1.0), "Beast": ("nature", 0.15), "Undead": ("holy", 0.8), "Dragon": ("dragon fire", 2.5),
           "Fiend": ("holy", 1.2), "Aberration": ("arcane", 0.7), "Fey": ("nature social", 0.9), "Construct": ("arcane", 0.4),
           "Giant": ("strength", 1.3), "Monstrosity": ("combat", 0.5), "Elemental": ("fire water", 0.3), "Celestial": ("holy", 1.0)}

# (name, rarity, tags, one-line summary in our own words)
MAGIC_ITEMS = [
    ("Potion of Healing", "common", "healing", "Drink to regain 2d4 + 2 HP."),
    ("Potion of Climbing", "common", "utility", "Climbing speed equal to walking speed for 1 hour; advantage on climbing checks."),
    ("Spell Scroll (cantrip)", "common", "arcane", "Cast the cantrip written on it once."),
    ("Spell Scroll (1st level)", "common", "arcane", "Cast the 1st-level spell written on it once."),
    ("Moon-Touched Sword", "common", "combat", "Sheds moonlight (bright 15 ft, dim 15 ft) when drawn in darkness."),
    ("Driftglobe", "uncommon", "arcane utility", "Glass orb that casts Light or Daylight and can float after its owner."),
    ("Bag of Holding", "uncommon", "utility", "Holds up to 500 lb in a 64 cubic foot extradimensional space; weighs 15 lb."),
    ("Boots of Elvenkind", "uncommon", "stealth nature", "Silent footsteps; advantage on Stealth checks to move silently."),
    ("Cloak of Elvenkind", "uncommon", "stealth nature", "Hood up: Perception checks to see you have disadvantage, you have advantage on Stealth to hide."),
    ("Cloak of Protection", "uncommon", "combat", "Attunement. +1 to AC and saving throws."),
    ("Gauntlets of Ogre Power", "uncommon", "strength combat", "Attunement. Strength becomes 19."),
    ("Goggles of Night", "uncommon", "utility", "Darkvision 60 ft (or +60 ft if you already have it)."),
    ("Immovable Rod", "uncommon", "utility", "Press the button and it locks in place, holding up to 8,000 lb."),
    ("Pearl of Power", "uncommon", "arcane", "Attunement (spellcaster). Once per day regain a spent spell slot up to 3rd level."),
    ("Potion of Greater Healing", "uncommon", "healing", "Drink to regain 4d4 + 4 HP."),
    ("Potion of Water Breathing", "uncommon", "water", "Breathe underwater for 1 hour."),
    ("Ring of Jumping", "uncommon", "utility", "Attunement. Cast Jump on yourself at will."),
    ("Sending Stones", "uncommon", "social arcane", "Paired stones; once per day send a short message to the holder of the other."),
    ("Wand of Magic Missiles", "uncommon", "arcane", "7 charges; spend charges to cast Magic Missile, more charges for more darts."),
    ("Weapon +1", "uncommon", "combat", "+1 to attack and damage rolls."),
    ("Shield +1", "uncommon", "combat", "+1 AC on top of the shield's normal bonus."),
    ("Wand of the War Mage +1", "uncommon", "arcane combat", "Attunement (spellcaster). +1 to spell attack rolls; ignores half cover."),
    ("Rope of Climbing", "uncommon", "utility", "60 ft of silk rope that moves, knots and fastens itself on command."),
    ("Periapt of Wound Closure", "uncommon", "healing", "Attunement. You stabilize automatically at 0 HP and regain double from Hit Dice."),
    ("Lantern of Revealing", "uncommon", "holy undead", "While lit, invisible creatures and objects in its bright light become visible."),
    ("Bracers of Archery", "uncommon", "nature combat", "Attunement. Longbow/shortbow proficiency and +2 damage with them."),
    ("Eyes of the Eagle", "uncommon", "utility", "Attunement. Advantage on sight-based Perception; see far detail clearly."),
    ("Hat of Disguise", "uncommon", "stealth social", "Attunement. Cast Disguise Self at will."),
    ("Headband of Intellect", "uncommon", "arcane", "Attunement. Intelligence becomes 19."),
    ("Javelin of Lightning", "uncommon", "combat", "Once per dawn, throw to become a 120 ft line of lightning (4d6, Dex save half)."),
    ("Spell Scroll (2nd–3rd level)", "uncommon", "arcane", "Cast the spell written on it once."),
    ("Amulet of Health", "rare", "healing", "Attunement. Constitution becomes 19."),
    ("Belt of Dwarvenkind", "rare", "strength", "Attunement. +2 Con (max 20), darkvision, advantage vs poison, speak Dwarvish."),
    ("Boots of Speed", "rare", "combat", "Attunement. Click heels: speed doubles and opportunity attacks against you have disadvantage."),
    ("Bracers of Defense", "rare", "combat", "Attunement. +2 AC while wearing no armor and no shield."),
    ("Cloak of Displacement", "rare", "combat stealth", "Attunement. Attacks against you have disadvantage until you take damage."),
    ("Flame Tongue", "rare", "fire combat", "Attunement. Command the blade to burst into flame for +2d6 fire damage."),
    ("Necklace of Fireballs", "rare", "fire arcane", "Detach a bead and throw it as a Fireball (more beads, bigger blast)."),
    ("Ring of Protection", "rare", "combat", "Attunement. +1 to AC and saving throws."),
    ("Ring of Spell Storing", "rare", "arcane", "Attunement. Stores up to 5 levels of spells for the wearer to cast."),
    ("Potion of Superior Healing", "rare", "healing", "Drink to regain 8d4 + 8 HP."),
    ("Wand of Fireballs", "rare", "fire arcane", "Attunement (spellcaster). 7 charges to cast Fireball."),
    ("Wand of Lightning Bolts", "rare", "arcane", "Attunement (spellcaster). 7 charges to cast Lightning Bolt."),
    ("Weapon +2", "rare", "combat", "+2 to attack and damage rolls."),
    ("Armor +1", "rare", "combat", "+1 AC on top of the armor's normal AC."),
    ("Mace of Disruption", "rare", "holy undead", "Attunement. +2d6 radiant to fiends and undead; may destroy weakened ones outright."),
    ("Sun Blade", "rare", "holy undead", "Attunement. Blade of radiance, +2 weapon, extra damage to undead, sheds sunlight."),
    ("Dagger of Venom", "rare", "combat stealth", "+1 dagger; once a day coat it in poison (2d10 poison, poisoned on a failed save)."),
    ("Periapt of Proof against Poison", "rare", "healing", "Immune to poison damage and the poisoned condition."),
    ("Ring of Resistance", "rare", "combat", "Attunement. Resistance to one damage type set by its gem."),
    ("Trident of Fish Command", "uncommon", "water", "Attunement. Cast Dominate Beast on swimming beasts."),
    ("Cape of the Mountebank", "rare", "stealth", "Once per day cast Dimension Door, vanishing in a puff of smoke."),
    ("Spell Scroll (4th–5th level)", "rare", "arcane", "Cast the spell written on it once."),
    ("Animated Shield", "very rare", "combat", "Attunement. Command it to float and guard you, leaving your hands free."),
    ("Belt of Fire Giant Strength", "very rare", "strength fire", "Attunement. Strength becomes 25."),
    ("Dancing Sword", "very rare", "combat", "Attunement. Toss it into the air and it fights on its own for a while."),
    ("Dwarven Thrower", "very rare", "strength combat", "Attunement (dwarf). +3 warhammer that returns when thrown; extra damage to giants."),
    ("Frost Brand", "very rare", "water combat", "Attunement. +1d6 cold damage, fire resistance, puts out nearby flames."),
    ("Manual of Bodily Health", "very rare", "healing", "Study it for 48 hours: Constitution +2 and maximum +2."),
    ("Potion of Supreme Healing", "very rare", "healing", "Drink to regain 10d4 + 20 HP."),
    ("Ring of Regeneration", "very rare", "healing", "Attunement. Regain 1d6 HP every 10 minutes; lost limbs regrow."),
    ("Staff of Fire", "very rare", "fire arcane", "Attunement (druid, sorcerer, warlock, wizard). Fire resistance; charges for Burning Hands, Fireball, Wall of Fire."),
    ("Weapon +3", "very rare", "combat", "+3 to attack and damage rolls."),
    ("Armor +2", "very rare", "combat", "+2 AC on top of the armor's normal AC."),
    ("Nine Lives Stealer", "very rare", "combat undead", "Attunement. +2 sword; on a crit it can slay a creature below 100 HP outright."),
    ("Spellguard Shield", "very rare", "arcane combat", "Attunement. Advantage on saves against spells; spell attacks against you have disadvantage."),
    ("Rod of Absorption", "very rare", "arcane", "Attunement. Absorb a spell targeting only you and store its energy for your own spells."),
    ("Wand of Polymorph", "very rare", "arcane", "Attunement (spellcaster). 7 charges to cast Polymorph."),
    ("Spell Scroll (6th–8th level)", "very rare", "arcane", "Cast the spell written on it once."),
    ("Holy Avenger", "legendary", "holy undead combat", "Attunement (paladin). +3 sword, +2d10 radiant vs fiends and undead, aura of spell protection."),
    ("Vorpal Sword", "legendary", "combat", "Attunement. +3 sword that ignores slashing resistance; a natural 20 can behead."),
    ("Ring of Three Wishes", "legendary", "arcane", "Holds three castings of Wish."),
    ("Staff of the Magi", "legendary", "arcane", "Attunement (sorcerer, warlock, wizard). Powerful staff of many spells; can absorb spells and retributively explode."),
    ("Robe of the Archmagi", "legendary", "arcane", "Attunement (sorcerer, warlock, wizard). AC 15 + Dex, advantage vs spells, +2 spell DC and attack."),
    ("Cloak of Invisibility", "legendary", "stealth", "Attunement. Pull up the hood to become invisible for up to 2 hours a day."),
    ("Defender", "legendary", "combat", "Attunement. +3 sword; move some of the bonus to your AC each turn."),
    ("Luck Blade", "legendary", "combat", "Attunement. +1 sword, +1 to saves, reroll once per day; may hold Wish charges."),
    ("Armor of Invulnerability", "legendary", "combat", "Attunement. Resistance to nonmagical damage; once a day become immune to it for 10 minutes."),
    ("Rod of Lordly Might", "legendary", "strength combat", "Attunement. +3 mace that transforms into other weapons and tools; paralyzes, terrifies, drains."),
    ("Talisman of Pure Good", "legendary", "holy", "Attunement (good). Holy symbol; charges to send evil creatures into a fiery pit."),
    ("Spell Scroll (9th level)", "legendary", "arcane", "Cast the 9th-level spell written on it once."),
    ("Belt of Storm Giant Strength", "legendary", "strength", "Attunement. Strength becomes 29."),
]
RARITY_ODDS = [  # per tier: weights for common, uncommon, rare, very rare, legendary
    (60, 35, 5, 0, 0), (25, 50, 22, 3, 0), (0, 30, 45, 22, 3), (0, 0, 30, 45, 25)]
GEMS = [(10, "Azurite Banded-agate Blue-quartz Eye-agate Hematite Lapis-lazuli Malachite Moss-agate Obsidian Tiger-eye Turquoise"),
        (50, "Bloodstone Carnelian Chalcedony Chrysoprase Citrine Jasper Moonstone Onyx Sardonyx Star-rose-quartz Zircon"),
        (100, "Amber Amethyst Chrysoberyl Coral Garnet Jade Jet Pearl Spinel Tourmaline"),
        (500, "Alexandrite Aquamarine Black-pearl Blue-spinel Peridot Topaz"),
        (1000, "Black-opal Blue-sapphire Emerald Fire-opal Opal Star-ruby Star-sapphire Yellow-sapphire"),
        (5000, "Black-sapphire Diamond Jacinth Ruby")]
ART = [(25, ["Silver ewer", "Carved bone statuette", "Small gold bracelet", "Embroidered silk handkerchief"]),
       (250, ["Gold ring set with bloodstones", "Carved ivory statuette", "Brass mug with jade inlay", "Silver chalice"]),
       (750, ["Silver-plated steel longsword with jet hilt", "Carved harp of exotic wood", "Small gold idol"]),
       (2500, ["Fine gold chain with a fire opal", "Old masterpiece painting", "Embroidered silk and velvet mantle"]),
       (7500, ["Jeweled gold crown", "Jeweled platinum ring", "Gold cup set with emeralds"])]
FLAVOR = {"Humanoid": ["Map fragment", "Signet ring of a minor house", "Letter of credit (50 gp)", "Set of loaded dice"],
          "Beast": ["Fine pelt (10 gp)", "Fangs and claws (2 gp)", "Pearl in a stomach (100 gp)"],
          "Undead": ["Tarnished burial jewelry (25 gp)", "Coins from a forgotten kingdom", "Crumbling funeral mask"],
          "Dragon": ["Shed dragon scale (100 gp)", "Melted gold lump (40 gp)", "Ancient elven goblet"],
          "Fiend": ["Infernal contract (bound soul)", "Black iron key", "Brimstone vial"],
          "Aberration": ["Strange non-euclidean idol", "Jar of unsettling ichor", "Mind-flayer tadpole jar (empty?)"],
          "Fey": ["Bottled starlight", "Flower that never wilts", "Silver acorn"],
          "Construct": ["Arcane gear core (50 gp)", "Glowing rune plate", "Spare automaton finger"],
          "Giant": ["Oversized copper coin (5 gp)", "Giant's knucklebone dice", "Rope as thick as an arm"],
          "Monstrosity": ["Trophy horn (20 gp)", "Undigested adventurer's pack", "Venom gland (50 gp)"],
          "Elemental": ["Ever-warm ember", "Shard of living stone", "Vial of storm water"],
          "Celestial": ["Feather of pure light", "Blessed holy water (25 gp)", "Silver halo fragment"]}
COIN_MIX = [  # share of value in cp, sp, gp, pp per tier
    (0.3, 0.4, 0.3, 0), (0, 0.1, 0.7, 0.2), (0, 0, 0.6, 0.4), (0, 0, 0.4, 0.6)]
COIN_BASE = {"Individual": [30, 300, 3000, 25000], "Hoard": [400, 5000, 40000, 300000]}


def parse_table(text):
    """Lines: 'weight | name | rarity | value in gp'. Only the name is required; # starts a comment."""
    rows = []
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        try:
            weight = float(parts[0])
            parts = parts[1:]
        except ValueError:
            weight = 1.0
        if not parts or not parts[0]:
            continue
        try:
            value = float(parts[2]) if len(parts) > 2 else 0.0
        except ValueError:
            value = 0.0
        rows.append(dict(weight=max(0.0, weight), name=parts[0], rarity=parts[1] if len(parts) > 1 else "", value=value))
    return rows


def generate(tier=0, source="Individual", difficulty="Medium", location="Dungeon", enemy="Humanoid",
             max_rarity="legendary", custom=None, coins=True, seed=None, extra=()):
    """Returns a list of {name, kind, rarity, value} items. `custom` is a parsed custom table (replaces magic items)."""
    rng = random.Random(seed)
    hoard, mult = source == "Hoard", DIFFICULTY.get(difficulty, 1.0)
    tags, coin_factor = ENEMIES.get(enemy, ("", 1.0))
    tags = set(tags.split()) | set(LOCATIONS.get(location, "").split())
    out = []
    if coins:
        total = COIN_BASE[source][tier] * mult * coin_factor * rng.uniform(0.6, 1.4)
        for share, (coin, per_gp) in zip(COIN_MIX[tier], (("cp", 100), ("sp", 10), ("gp", 1), ("pp", 0.1))):
            n = int(total * share * per_gp)
            if n:
                out.append(dict(name=f"{n:,} {coin}", kind="coins", rarity="", value=round(n / per_gp, 2)))
    n_gems = 0 if not coins else rng.randint(1, 4) + tier if hoard else int(rng.random() < 0.3 * mult)
    for _ in range(n_gems):
        if rng.random() < 0.5:
            value, names = GEMS[min(len(GEMS) - 1, tier + rng.randint(0, 2))]
            out.append(dict(name=f"{rng.choice(names.split()).replace('-', ' ')} ({value} gp gem)", kind="gem", rarity="", value=value))
        else:
            value, names = ART[min(len(ART) - 1, tier + rng.randint(0, 1))]
            out.append(dict(name=f"{rng.choice(names)} (art, {value} gp)", kind="art", rarity="", value=value))
    n_items = (rng.randint(0, 2) + tier + (difficulty in ("Hard", "Deadly"))) if hoard else int(rng.random() < 0.12 * (tier + 1) * mult)
    if custom:
        pool = [r for r in custom if r["weight"] > 0]
        for _ in range(max(n_items, 1) if pool else 0):
            r = rng.choices(pool, weights=[x["weight"] for x in pool])[0]
            out.append(dict(name=r["name"], kind="custom", rarity=r["rarity"], value=r["value"]))
    else:
        cap = RARITIES.index(max_rarity) if max_rarity in RARITIES else 4
        odds = [w if i <= cap else 0 for i, w in enumerate(RARITY_ODDS[tier])]
        if not any(odds):
            odds = [1 if i == cap else 0 for i in range(5)]
        for _ in range(n_items):
            rarity = rng.choices(RARITIES, weights=odds)[0]
            pool = [m for m in MAGIC_ITEMS + list(extra) if m[1] == rarity]  # extra: Brewery items
            if not pool:
                continue
            m = rng.choices(pool, weights=[3 if tags & set(m[2].split()) else 1 for m in pool])[0]  # fits the place and foe
            out.append(dict(name=m[0], kind="magic", rarity=rarity,
                            value=VALUE[rarity] // (2 if "Potion" in m[0] or "Scroll" in m[0] else 1)))
    if not custom and rng.random() < 0.6:  # custom tables stay purely homebrew
        out.append(dict(name=rng.choice(FLAVOR.get(enemy, FLAVOR["Humanoid"])), kind="trinket", rarity="", value=0))
    return out
