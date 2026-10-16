"""Searchable rules reference: core rules, spells, conditions, magic items and the DM's homebrew.
All text is short paraphrase, meant as a reminder at the table, not a replacement for the books."""
from . import rules
from . import brew
from .loot import MAGIC_ITEMS

CATEGORIES = ["All", "Rules", "Spells", "Conditions", "Magic items", "Homebrew weapons", "Homebrew creatures", "Homebrew rules"]

# (name, summary, what changed in 2024 or "")
RULES = [
    ("Actions in combat", "Attack, Cast a Spell, Dash, Disengage, Dodge, Help, Hide, Ready, Search, Use an Object. "
     "One action, one bonus action (only if something grants it), movement, one free object interaction and one reaction per round.",
     "Actions are renamed/added: Magic (cast a spell or use a magic item), Influence, Study, Utilize, Search; Hide needs a DC 15 Stealth check."),
    ("Opportunity attack", "When a hostile creature you can see leaves your reach, use your reaction for one melee attack. "
     "Disengage, teleporting or being moved without using movement avoids it.", ""),
    ("Advantage and disadvantage", "Roll two d20s and take the higher (advantage) or lower (disadvantage). "
     "Any amount of both cancels out; they never stack.", ""),
    ("Critical hits", "A natural 20 on an attack always hits and is a critical: roll all the attack's damage dice twice. "
     "A natural 1 always misses.", ""),
    ("Cover", "Half cover: +2 AC and Dex saves. Three-quarters cover: +5. Total cover: can't be targeted directly.", ""),
    ("Grappling", "Replace one attack: Athletics vs the target's Athletics or Acrobatics. On a win the target is Grappled. "
     "Escape with an action using the same contest.",
     "Unarmed Strike option: the target makes a Str or Dex save (DC 8 + Str mod + proficiency) or is Grappled; escape is an action check vs that DC."),
    ("Shoving", "Replace one attack: Athletics vs Athletics/Acrobatics. Push 5 ft away or knock Prone.",
     "Unarmed Strike option: Str or Dex save (DC 8 + Str mod + proficiency) or be pushed 5 ft or knocked Prone."),
    ("Two-weapon fighting", "Attack with a light melee weapon, then a bonus-action attack with another light weapon; no ability modifier to its damage unless negative.",
     "The extra attack works through the Light weapon property and weapon masteries such as Nick."),
    ("Death saving throws", "At 0 HP and not killed: at the start of each turn roll a d20. 10+ success, 9- failure. "
     "3 successes stabilize, 3 failures kill. Natural 20: regain 1 HP. Natural 1: two failures. Damage at 0 HP is a failure (crit = two).", ""),
    ("Massive damage", "If damage reduces you to 0 HP and the remaining damage equals or exceeds your HP maximum, you die instantly.", ""),
    ("Stabilizing", "A DC 10 Wisdom (Medicine) check or Spare the Dying stabilizes a creature at 0 HP. A stable creature regains 1 HP after 1d4 hours.", ""),
    ("Concentration", "One concentration spell at a time. Taking damage: Con save DC 10 or half the damage, whichever is higher. "
     "Incapacitated or killed ends it.", "The save DC is capped at 30."),
    ("Short rest", "At least 1 hour of light activity. Spend Hit Dice: roll each, add Con modifier, regain that many HP.", ""),
    ("Long rest", "At least 8 hours, mostly sleep, at most once per 24 hours. Regain all HP and half your total Hit Dice; reduce Exhaustion by 1.",
     "Regain all HP and all Hit Dice; Exhaustion is reduced by 1."),
    ("Exhaustion", rules.CONDITIONS["Exhaustion"][2], rules.CONDITIONS["Exhaustion"][3]),
    ("Light and vision", "Bright light: normal. Dim light: lightly obscured (disadvantage on sight Perception). "
     "Darkness: heavily obscured (effectively Blinded when trying to see into it).", ""),
    ("Darkvision", "Within its range, see dim light as bright and darkness as dim light, in shades of grey.", ""),
    ("Surprise", "Anyone who didn't notice a threat is surprised: no move or action on their first turn and no reaction until it ends.",
     "Surprised creatures simply have disadvantage on their initiative roll."),
    ("Hiding", "Dexterity (Stealth) contested by passive Perception; you need to be heavily obscured or out of sight.",
     "Hide action: DC 15 Stealth while heavily obscured or behind cover; you gain the Invisible condition until found or you attack."),
    ("Falling", "1d6 bludgeoning per 10 ft fallen, maximum 20d6. You land Prone unless you avoid all the damage.", ""),
    ("Suffocating", "Hold breath for 1 + Con modifier minutes (min 30 seconds). Then survive Con modifier rounds (min 1) before dropping to 0 HP.", ""),
    ("Jumping", "Long jump: up to your Strength score in feet with a 10 ft run-up (half from standing). "
     "High jump: 3 + Strength modifier feet with a run-up (half from standing).", ""),
    ("Travel pace", "Fast: 4 mi/hour, 30 mi/day, −5 passive Perception. Normal: 3 mi/hour, 24 mi/day. Slow: 2 mi/hour, 18 mi/day, can use Stealth.", ""),
    ("Difficulty classes", "Very easy 5, easy 10, medium 15, hard 20, very hard 25, nearly impossible 30.", ""),
    ("Passive checks", "10 + all modifiers that normally apply (+5 for advantage, −5 for disadvantage).", ""),
    ("Spell save DC and attack", "Save DC = 8 + proficiency bonus + spellcasting modifier. Spell attack = proficiency bonus + spellcasting modifier.", ""),
    ("Bonus action spells", "If you cast a spell with a bonus action, the only other spell you can cast that turn is a cantrip with a casting time of 1 action.",
     "Replaced: you can expend only one spell slot per turn."),
    ("Ritual casting", "A spell with the ritual tag can be cast without a slot by adding 10 minutes to its casting time.", ""),
    ("Temporary hit points", "A buffer lost before real HP. They don't stack: keep the higher amount. Healing doesn't restore them.", ""),
    ("Resistance and vulnerability", "Resistance halves damage (round down), vulnerability doubles it, immunity negates it. "
     "Apply other modifiers first, then resistance, then vulnerability.", ""),
    ("Inspiration", "DM-awarded; spend it for advantage on one attack, save or check.",
     "Heroic Inspiration: spend it to reroll any die immediately and use the new roll."),
    ("Proficiency bonus", "+2 at levels 1–4, +3 at 5–8, +4 at 9–12, +5 at 13–16, +6 at 17–20.", ""),
    ("Carrying capacity", "Strength score × 15 pounds. Push, drag or lift up to twice that.", ""),
    ("Mounted combat", "Mounting or dismounting costs half your speed. A controlled mount can only Dash, Disengage or Dodge.", ""),
    ("Underwater combat", "Without a swim speed, melee attacks have disadvantage unless using a dagger, javelin, shortsword, spear or trident. "
     "Ranged weapon attacks beyond normal range miss; within range have disadvantage (except crossbows, nets, thrown javelins etc.).", ""),
    ("Objects", "Typical AC: cloth 11, wood 15, stone 17, iron 19, adamantine 23. Immune to poison and psychic damage.", ""),
    ("Encounter difficulty", "2014: sum monster XP, multiply for group size, compare with the party's Easy/Medium/Hard/Deadly thresholds. "
     "Use the Encounter tab to calculate.", "2024: sum monster XP and compare with the party's Low/Moderate/High budget; no multiplier."),
]

# (name, level, school, casting time, range, duration, summary, 2024 note)
SPELLS = [
    ("Fire Bolt", 0, "Evocation", "1 action", "120 ft", "Instant", "Ranged spell attack, 1d10 fire. More dice at levels 5, 11, 17.", ""),
    ("Eldritch Blast", 0, "Evocation", "1 action", "120 ft", "Instant", "Ranged spell attack beam, 1d10 force. Extra beams at levels 5, 11, 17.", ""),
    ("Sacred Flame", 0, "Evocation", "1 action", "60 ft", "Instant", "Dex save or 1d8 radiant; cover doesn't help the target.", ""),
    ("Ray of Frost", 0, "Evocation", "1 action", "60 ft", "Instant", "Ranged spell attack, 1d8 cold and −10 ft speed until your next turn.", ""),
    ("Shocking Grasp", 0, "Evocation", "1 action", "Touch", "Instant", "Melee spell attack, 1d8 lightning; target can't take reactions. Advantage vs metal armor.",
     "No longer gives advantage against metal armor."),
    ("Vicious Mockery", 0, "Enchantment", "1 action", "60 ft", "Instant", "Wis save or 1d4 psychic and disadvantage on its next attack roll.", "Damage is 1d6."),
    ("Chill Touch", 0, "Necromancy", "1 action", "120 ft", "1 round", "Ranged spell attack, 1d8 necrotic; target can't regain HP; undead get disadvantage attacking you.",
     "Becomes a touch attack dealing 1d10 necrotic."),
    ("Guidance", 0, "Divination", "1 action", "Touch", "Conc, 1 min", "Target adds 1d4 to one ability check of its choice.", "Choose a skill: the target adds 1d4 to checks with it for the duration."),
    ("Light", 0, "Evocation", "1 action", "Touch", "1 hour", "An object sheds bright light 20 ft and dim light 20 ft more.", ""),
    ("Mage Hand", 0, "Conjuration", "1 action", "30 ft", "1 min", "A spectral hand manipulates objects up to 10 lb.", ""),
    ("Minor Illusion", 0, "Illusion", "1 action", "30 ft", "1 min", "Create a sound or a still image up to a 5 ft cube. Investigation reveals it.", ""),
    ("Prestidigitation", 0, "Transmutation", "1 action", "10 ft", "Up to 1 hour", "Small magical tricks: clean, flavor, warm, chill, light candles, tiny marks.", ""),
    ("Spare the Dying", 0, "Necromancy", "1 action", "Touch", "Instant", "A creature at 0 HP becomes stable.", "Range 15 ft, growing at higher levels."),
    ("Thorn Whip", 0, "Transmutation", "1 action", "30 ft", "Instant", "Melee spell attack, 1d6 piercing; pull a Large or smaller target 10 ft closer.", ""),
    ("Magic Missile", 1, "Evocation", "1 action", "120 ft", "Instant", "Three darts that always hit, 1d4 + 1 force each. One more dart per higher slot.", ""),
    ("Shield", 1, "Abjuration", "1 reaction", "Self", "1 round", "+5 AC until the start of your next turn (including vs the trigger); no Magic Missile damage.", ""),
    ("Cure Wounds", 1, "Evocation", "1 action", "Touch", "Instant", "Heal 1d8 + spellcasting modifier.", "Heals 2d8 + modifier."),
    ("Healing Word", 1, "Evocation", "1 bonus action", "60 ft", "Instant", "Heal 1d4 + spellcasting modifier.", "Heals 2d4 + modifier."),
    ("Bless", 1, "Enchantment", "1 action", "30 ft", "Conc, 1 min", "Up to three creatures add 1d4 to attack rolls and saving throws.", ""),
    ("Bane", 1, "Enchantment", "1 action", "30 ft", "Conc, 1 min", "Up to three creatures (Cha save) subtract 1d4 from attacks and saves.", ""),
    ("Sleep", 1, "Enchantment", "1 action", "90 ft", "1 min", "5d8 HP of creatures fall unconscious, lowest HP first.",
     "Wis save in a 5 ft sphere: Incapacitated, then Unconscious if it fails again."),
    ("Thunderwave", 1, "Evocation", "1 action", "Self (15 ft cube)", "Instant", "Con save or 2d8 thunder and pushed 10 ft; half on success.", ""),
    ("Burning Hands", 1, "Evocation", "1 action", "Self (15 ft cone)", "Instant", "Dex save, 3d6 fire, half on success.", ""),
    ("Charm Person", 1, "Enchantment", "1 action", "30 ft", "1 hour", "Wis save (advantage if fighting you) or a humanoid is Charmed by you.", ""),
    ("Detect Magic", 1, "Divination", "1 action", "Self (30 ft)", "Conc, 10 min", "Ritual. Sense magic nearby and see its aura and school.", ""),
    ("Faerie Fire", 1, "Evocation", "1 action", "60 ft (20 ft cube)", "Conc, 1 min", "Dex save or outlined in light: attacks against it have advantage; can't be invisible.", ""),
    ("Guiding Bolt", 1, "Evocation", "1 action", "120 ft", "1 round", "Ranged spell attack, 4d6 radiant; the next attack against it has advantage.", ""),
    ("Hex", 1, "Enchantment", "1 bonus action", "90 ft", "Conc, 1 hour", "+1d6 necrotic on your hits against the target; disadvantage on checks with one ability.", ""),
    ("Hunter's Mark", 1, "Divination", "1 bonus action", "90 ft", "Conc, 1 hour", "+1d6 damage on your weapon hits against the target; advantage to track it.", "Force damage, and Rangers get it free and stronger as they level."),
    ("Mage Armor", 1, "Abjuration", "1 action", "Touch", "8 hours", "Unarmored target's AC becomes 13 + Dex modifier.", ""),
    ("Shield of Faith", 1, "Abjuration", "1 bonus action", "60 ft", "Conc, 10 min", "+2 AC to one creature.", ""),
    ("Entangle", 1, "Conjuration", "1 action", "90 ft (20 ft square)", "Conc, 1 min", "Str save or Restrained by grasping plants; area is difficult terrain.", ""),
    ("Command", 1, "Enchantment", "1 action", "60 ft", "1 round", "Wis save or obey a one-word command (approach, drop, flee, grovel, halt).", ""),
    ("Inflict Wounds", 1, "Necromancy", "1 action", "Touch", "Instant", "Melee spell attack, 3d10 necrotic.", "Con save, 2d10 necrotic (half on success)."),
    ("Sanctuary", 1, "Abjuration", "1 bonus action", "30 ft", "1 min", "Attackers must make a Wis save or pick another target. Ends if the warded creature attacks.", ""),
    ("Feather Fall", 1, "Transmutation", "1 reaction", "60 ft", "1 min", "Up to five falling creatures descend at 60 ft per round and take no falling damage.", ""),
    ("Find Familiar", 1, "Conjuration", "1 hour", "10 ft", "Instant", "Ritual. Summon a spirit animal familiar you can see through and that can deliver touch spells.", ""),
    ("Protection from Evil and Good", 1, "Abjuration", "1 action", "Touch", "Conc, 10 min", "Aberrations, celestials, elementals, fey, fiends and undead have disadvantage attacking the target; it can't be charmed, frightened or possessed by them.", ""),
    ("Misty Step", 2, "Conjuration", "1 bonus action", "Self", "Instant", "Teleport up to 30 ft to a space you can see.", ""),
    ("Hold Person", 2, "Enchantment", "1 action", "60 ft", "Conc, 1 min", "Wis save or a humanoid is Paralyzed; it repeats the save at the end of each of its turns.", ""),
    ("Invisibility", 2, "Illusion", "1 action", "Touch", "Conc, 1 hour", "Target becomes invisible until it attacks or casts a spell.", ""),
    ("Spiritual Weapon", 2, "Evocation", "1 bonus action", "60 ft", "1 min", "Floating weapon: bonus action melee spell attack for 1d8 + modifier force.", "Requires concentration."),
    ("Scorching Ray", 2, "Evocation", "1 action", "120 ft", "Instant", "Three rays, each a ranged spell attack for 2d6 fire. One more ray per higher slot.", ""),
    ("Shatter", 2, "Evocation", "1 action", "60 ft (10 ft sphere)", "Instant", "Con save, 3d8 thunder, half on success; constructs of stone/metal have disadvantage.", ""),
    ("Web", 2, "Conjuration", "1 action", "60 ft (20 ft cube)", "Conc, 1 hour", "Sticky webs: difficult terrain, Dex save or Restrained; flammable.", ""),
    ("Darkness", 2, "Evocation", "1 action", "60 ft", "Conc, 10 min", "15 ft sphere of magical darkness; darkvision can't see through it.", ""),
    ("Lesser Restoration", 2, "Abjuration", "1 action", "Touch", "Instant", "End one disease or the Blinded, Deafened, Paralyzed or Poisoned condition.", "Bonus action to cast."),
    ("Aid", 2, "Abjuration", "1 action", "30 ft", "8 hours", "Up to three creatures gain +5 maximum and current HP.", ""),
    ("Mirror Image", 2, "Illusion", "1 action", "Self", "1 min", "Three illusory duplicates may absorb attacks aimed at you.", ""),
    ("Moonbeam", 2, "Evocation", "1 action", "120 ft", "Conc, 1 min", "5 ft radius beam: Con save, 2d10 radiant, half on success; you can move it.", ""),
    ("Suggestion", 2, "Enchantment", "1 action", "30 ft", "Conc, 8 hours", "Wis save or follow a reasonable-sounding course of action.", ""),
    ("Silence", 2, "Illusion", "1 action", "120 ft", "Conc, 10 min", "20 ft sphere with no sound; verbal spells can't be cast inside.", ""),
    ("Pass without Trace", 2, "Abjuration", "1 action", "Self (30 ft)", "Conc, 1 hour", "You and allies nearby get +10 to Stealth and leave no tracks.", ""),
    ("Spike Growth", 2, "Transmutation", "1 action", "150 ft (20 ft radius)", "Conc, 10 min", "Hidden thorns: difficult terrain, 2d4 piercing per 5 ft moved.", ""),
    ("Fireball", 3, "Evocation", "1 action", "150 ft (20 ft sphere)", "Instant", "Dex save, 8d6 fire, half on success. +1d6 per higher slot.", ""),
    ("Counterspell", 3, "Abjuration", "1 reaction", "60 ft", "Instant", "Stop a spell of 3rd level or lower; higher needs an ability check (DC 10 + its level).",
     "The caster makes a Con save; on a failure the spell fails and the slot isn't spent."),
    ("Dispel Magic", 3, "Abjuration", "1 action", "120 ft", "Instant", "End spells of 3rd level or lower on a target; higher needs a check (DC 10 + level).", ""),
    ("Fly", 3, "Transmutation", "1 action", "Touch", "Conc, 10 min", "Target gains a 60 ft flying speed.", ""),
    ("Haste", 3, "Transmutation", "1 action", "30 ft", "Conc, 1 min", "Double speed, +2 AC, advantage on Dex saves, an extra limited action. Lethargic for a turn when it ends.", ""),
    ("Hypnotic Pattern", 3, "Illusion", "1 action", "120 ft (30 ft cube)", "Conc, 1 min", "Wis save or Charmed and Incapacitated with speed 0; damage or a shake ends it.", ""),
    ("Lightning Bolt", 3, "Evocation", "1 action", "Self (100 ft line)", "Instant", "Dex save, 8d6 lightning, half on success.", ""),
    ("Revivify", 3, "Necromancy", "1 action", "Touch", "Instant", "A creature dead less than 1 minute returns with 1 HP (300 gp diamond consumed).", ""),
    ("Spirit Guardians", 3, "Conjuration", "1 action", "Self (15 ft)", "Conc, 10 min", "Enemies in the aura move at half speed; Wis save, 3d8 radiant or necrotic, half on success.", ""),
    ("Mass Healing Word", 3, "Evocation", "1 bonus action", "60 ft", "Instant", "Up to six creatures heal 1d4 + modifier.", "Heals 2d4 + modifier."),
    ("Slow", 3, "Transmutation", "1 action", "120 ft", "Conc, 1 min", "Up to six creatures (Wis save): half speed, −2 AC and Dex saves, limited actions.", ""),
    ("Animate Dead", 3, "Necromancy", "1 minute", "10 ft", "Instant", "Raise a skeleton or zombie servant; reassert control every 24 hours.", ""),
    ("Bestow Curse", 3, "Necromancy", "1 action", "Touch", "Conc, 1 min", "Wis save or suffer a curse (disadvantage, wasted turns, extra damage from you…).", ""),
    ("Remove Curse", 3, "Abjuration", "1 action", "Touch", "Instant", "All curses on a creature or object end.", ""),
    ("Fear", 3, "Illusion", "1 action", "Self (30 ft cone)", "Conc, 1 min", "Wis save or drop what it holds, become Frightened and Dash away.", ""),
    ("Stinking Cloud", 3, "Conjuration", "1 action", "90 ft (20 ft sphere)", "Conc, 1 min", "Con save at the start of each turn or lose the action retching.", ""),
    ("Polymorph", 4, "Transmutation", "1 action", "60 ft", "Conc, 1 hour", "Wis save or turn a creature into a beast (CR up to its level). Temporary HP of the new form.", ""),
    ("Banishment", 4, "Abjuration", "1 action", "60 ft", "Conc, 1 min", "Cha save or the target is sent away; native extraplanar creatures may not come back.", ""),
    ("Greater Invisibility", 4, "Illusion", "1 action", "Touch", "Conc, 1 min", "Target is invisible even while attacking or casting.", ""),
    ("Wall of Fire", 4, "Evocation", "1 action", "120 ft", "Conc, 1 min", "60 ft wall; Dex save 5d8 fire when it appears, and to anyone ending a turn near its hot side.", ""),
    ("Dimension Door", 4, "Conjuration", "1 action", "500 ft", "Instant", "Teleport yourself and one willing creature up to 500 ft.", ""),
    ("Ice Storm", 4, "Evocation", "1 action", "300 ft", "Instant", "Dex save, 2d8 bludgeoning + 4d6 cold, half on success; area becomes difficult terrain.", ""),
    ("Death Ward", 4, "Abjuration", "1 action", "Touch", "8 hours", "The first time the target would drop to 0 HP, it drops to 1 instead.", ""),
    ("Freedom of Movement", 4, "Abjuration", "1 action", "Touch", "1 hour", "Difficult terrain, paralysis and restraint can't hinder the target.", ""),
    ("Cone of Cold", 5, "Evocation", "1 action", "Self (60 ft cone)", "Instant", "Con save, 8d8 cold, half on success.", ""),
    ("Wall of Force", 5, "Evocation", "1 action", "120 ft", "Conc, 10 min", "An invisible, indestructible wall or dome; Disintegrate destroys it.", ""),
    ("Hold Monster", 5, "Enchantment", "1 action", "90 ft", "Conc, 1 min", "Like Hold Person but works on any creature (not undead).", ""),
    ("Raise Dead", 5, "Necromancy", "1 hour", "Touch", "Instant", "Return a creature dead up to 10 days (500 gp diamond); −4 penalty that fades with rests.", ""),
    ("Greater Restoration", 5, "Abjuration", "1 action", "Touch", "Instant", "End charm, petrification, a curse, an ability reduction, HP max reduction or one exhaustion level.", ""),
    ("Mass Cure Wounds", 5, "Evocation", "1 action", "60 ft", "Instant", "Up to six creatures in a 30 ft sphere heal 3d8 + modifier.", "Heals 5d8 + modifier."),
    ("Flame Strike", 5, "Evocation", "1 action", "60 ft", "Instant", "10 ft radius pillar: Dex save, 4d6 fire + 4d6 radiant, half on success.", "5d6 fire + 5d6 radiant."),
    ("Disintegrate", 6, "Transmutation", "1 action", "60 ft", "Instant", "Dex save or 10d6 + 40 force; reduced to 0 HP means turned to dust.", ""),
    ("Heal", 6, "Evocation", "1 action", "60 ft", "Instant", "Heal 70 HP and end blindness, deafness and diseases.", ""),
    ("Chain Lightning", 6, "Evocation", "1 action", "150 ft", "Instant", "Bolt hits a target then three more nearby: Dex save, 10d8 lightning, half on success.", ""),
    ("True Seeing", 6, "Divination", "1 action", "Touch", "1 hour", "Truesight 120 ft: see invisible, illusions, shapechangers and the Ethereal.", ""),
    ("Teleport", 7, "Conjuration", "1 action", "10 ft", "Instant", "You and up to eight willing creatures teleport to a destination; mishaps if unfamiliar.", ""),
    ("Plane Shift", 7, "Conjuration", "1 action", "Touch", "Instant", "Travel to another plane, or banish an unwilling creature (melee spell attack, Cha save).", ""),
    ("Finger of Death", 7, "Necromancy", "1 action", "60 ft", "Instant", "Con save, 7d8 + 30 necrotic; humanoids killed rise as zombies under your control.", ""),
    ("Resurrection", 7, "Necromancy", "1 hour", "Touch", "Instant", "Return a creature dead up to a century (1,000 gp diamond).", ""),
    ("Power Word Stun", 8, "Enchantment", "1 action", "60 ft", "Instant", "A creature with 150 HP or fewer is Stunned (Con save each turn to end).", ""),
    ("Dominate Monster", 8, "Enchantment", "1 action", "60 ft", "Conc, 1 hour", "Wis save or the creature is Charmed and obeys your telepathic commands.", ""),
    ("Sunburst", 8, "Evocation", "1 action", "150 ft (60 ft sphere)", "Instant", "Con save, 12d6 radiant and Blinded for 1 minute; half and not blinded on success.", ""),
    ("Wish", 9, "Conjuration", "1 action", "Self", "Instant", "Duplicate any spell of 8th level or lower, or attempt something greater at great risk.", ""),
    ("Meteor Swarm", 9, "Evocation", "1 action", "1 mile", "Instant", "Four 40 ft spheres: Dex save, 20d6 fire + 20d6 bludgeoning each, half on success.", ""),
    ("Power Word Kill", 9, "Enchantment", "1 action", "60 ft", "Instant", "A creature with 100 HP or fewer dies.", "Otherwise takes 12d12 psychic damage."),
    ("Time Stop", 9, "Transmutation", "1 action", "Self", "Instant", "Take 1d4 + 1 turns in a row; ends if you affect anyone else.", ""),
    ("True Resurrection", 9, "Necromancy", "1 hour", "Touch", "Instant", "Return a creature dead up to 200 years, even with no body (25,000 gp diamond).", ""),
]


def entries(homebrew=()):
    """Every reference entry as dicts: name, cat, meta, text, note."""
    out = [dict(name=n, cat="Rules", meta="Rule", text=t, note=x) for n, t, x in RULES]
    for n, lvl, school, time, rng, dur, txt, x in SPELLS:
        level = "Cantrip" if lvl == 0 else f"Level {lvl}"
        out.append(dict(name=n, cat="Spells", meta=f"{level} {school} · {time} · {rng} · {dur}", text=txt, note=x))
    for n, c in rules.CONDITIONS.items():
        out.append(dict(name=n, cat="Conditions", meta="Condition", text=c[2], note=c[3] or ""))
    for n, rar, tags, txt in MAGIC_ITEMS:
        out.append(dict(name=n, cat="Magic items", meta=f"{rar.title()} magic item", text=txt, note=""))
    lib = brew.load()  # the Brewery's items and creatures, shared by every app
    for i in lib["items"]:
        out.append(dict(name=i["name"], cat="Homebrew weapons", brew=("items", i["id"]), meta=f"{i['rarity'].title()} {i['type'].lower()} · Brewery",
                        text=brew.itemcard(i).split("\n", 2)[2], note=""))  # heading + subtitle are shown separately
    for m in lib["monsters"]:
        out.append(dict(name=m["name"], cat="Homebrew creatures", brew=("monsters", m["id"]), meta=f"{m['size']} {m['type'].lower()}, CR {m['cr']} · Brewery",
                        text=brew.statblock(m).split("\n", 2)[2], note=""))
    for h in homebrew:
        out.append(dict(name=h["name"], cat="Homebrew rules", meta=h.get("meta") or "Homebrew rule", text=h["text"], note=""))
    return out


def search(query, cat="All", homebrew=()):
    q = query.strip().lower()
    hits = [e for e in entries(homebrew) if (cat == "All" or e["cat"] == cat)
            and (not q or q in e["name"].lower() or q in e["text"].lower() or q in e["meta"].lower())]
    return sorted(hits, key=lambda e: (not e["name"].lower().startswith(q), q not in e["name"].lower(), e["name"]))
