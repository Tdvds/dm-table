"""Encounter difficulty for 2014 and 2024 rules, plus a quick Monte Carlo battle simulation. No Qt."""
import math, random
from fractions import Fraction

CR_XP = {"0": 10, "1/8": 25, "1/4": 50, "1/2": 100, "1": 200, "2": 450, "3": 700, "4": 1100, "5": 1800, "6": 2300,
         "7": 2900, "8": 3900, "9": 5000, "10": 5900, "11": 7200, "12": 8400, "13": 10000, "14": 11500, "15": 13000,
         "16": 15000, "17": 18000, "18": 20000, "19": 22000, "20": 25000, "21": 33000, "22": 41000, "23": 50000,
         "24": 62000, "25": 75000, "26": 90000, "27": 105000, "28": 120000, "29": 135000, "30": 155000}
# 2014 DMG XP thresholds per character: easy, medium, hard, deadly
T2014 = {1: (25, 50, 75, 100), 2: (50, 100, 150, 200), 3: (75, 150, 225, 400), 4: (125, 250, 375, 500),
         5: (250, 500, 750, 1100), 6: (300, 600, 900, 1400), 7: (350, 750, 1100, 1700), 8: (450, 900, 1400, 2100),
         9: (550, 1100, 1600, 2400), 10: (600, 1200, 1900, 2800), 11: (800, 1600, 2400, 3600), 12: (1000, 2000, 3000, 4500),
         13: (1100, 2200, 3400, 5100), 14: (1250, 2500, 3800, 5700), 15: (1400, 2800, 4300, 6400), 16: (1600, 3200, 4800, 7200),
         17: (2000, 3900, 5900, 8800), 18: (2100, 4200, 6300, 9500), 19: (2400, 4900, 7300, 10900), 20: (2800, 5700, 8500, 12700)}
# 2024 DMG XP budget per character: low, moderate, high
T2024 = {1: (50, 75, 100), 2: (100, 150, 200), 3: (150, 225, 400), 4: (250, 375, 500), 5: (500, 750, 1100),
         6: (600, 1000, 1400), 7: (750, 1300, 1700), 8: (1000, 1700, 2100), 9: (1300, 2000, 2600), 10: (1600, 2300, 3100),
         11: (1900, 2900, 4100), 12: (2200, 3700, 4700), 13: (2600, 4200, 5400), 14: (2900, 4900, 6200), 15: (3300, 5400, 7800),
         16: (3800, 6100, 9800), 17: (4500, 7200, 11700), 18: (5000, 8700, 14200), 19: (5500, 10700, 17200), 20: (6400, 13200, 22000)}
STEPS = [0.5, 1, 1.5, 2, 2.5, 3, 4]  # 2014 group multipliers


def cr_norm(cr):
    try:
        f = Fraction(str(cr).strip())
    except (ValueError, ZeroDivisionError):
        return None
    s = str(f)
    return s if s in CR_XP else None


def cr_value(cr):
    n = cr_norm(cr)
    return float(Fraction(n)) if n else 0.0


def xp_for(cr):
    return CR_XP.get(cr_norm(cr), 0)


def lvl(level):
    return max(1, min(20, int(level or 1)))


def rate(levels, crs, ruleset="2024"):
    """levels: PC levels. crs: monster CRs. Returns xp, adjusted xp, [(label, threshold)], rating."""
    xp = sum(xp_for(c) for c in crs)
    if not levels or not crs:
        return dict(xp=xp, adjusted=xp, thresholds=[], rating="—", mult=1)
    if ruleset == "2024":
        labels, table, adj, mult = ("Low", "Moderate", "High"), T2024, xp, 1
    else:
        n = len(crs)
        i = 1 if n == 1 else 2 if n == 2 else 3 if n <= 6 else 4 if n <= 10 else 5 if n <= 14 else 6
        i += 1 if len(levels) < 3 else -1 if len(levels) >= 6 else 0  # small parties feel numbers more
        mult = STEPS[max(0, min(6, i))]
        labels, table, adj = ("Easy", "Medium", "Hard", "Deadly"), T2014, xp * mult
    th = [(lab, sum(table[lvl(l)][k] for l in levels)) for k, lab in enumerate(labels)]
    rating = "Trivial"
    for lab, val in th:
        if adj >= val:
            rating = lab
    if ruleset == "2024" and adj >= th[-1][1] * 1.5:
        rating = "Beyond High (deadly)"
    return dict(xp=xp, adjusted=adj, thresholds=th, rating=rating, mult=mult)


def pc_stats(level):
    """Rough stats for a PC of this level when the token doesn't say."""
    L = lvl(level)
    prof = 2 + (L - 1) // 4
    return dict(hp=round(9 + 6.5 * (L - 1)), ac=15 + (L >= 5) + (L >= 11), atk=prof + 3 + (L >= 8),
                dpr=7 + 2.6 * L, attacks=1 + (L >= 5))


def monster_stats(cr):
    """Rough stats by CR, tuned to sit near typical published monsters."""
    c = cr_value(cr)
    return dict(hp=max(4, round(15 * c + 10)), ac=min(19, 13 + int(c // 3)), atk=3 + math.ceil(c / 3),
                dpr=max(1.0, 6 * c + 4), attacks=1 if c < 3 else 2)


def combatant(name, side, hp, ac, atk, dpr, attacks):
    attacks = max(1, int(attacks))
    return dict(name=name, side=side, hp=max(1, hp), ac=ac, atk=atk, dmg=dpr / attacks, attacks=attacks)


def simulate(party, foes, runs=1000, resources="fresh", seed=None):
    """Fights the battle `runs` times. PCs focus the weakest foe; monsters pick random targets."""
    rng = random.Random(seed)
    boost = {"fresh": 1.15, "some used": 1.0, "depleted": 0.8}[resources]  # spell slots and abilities left
    total_hp = sum(c["hp"] for c in party) or 1
    wins = rounds = downs = any_down = tpk = hp_left = 0
    for _ in range(runs):
        cs = [dict(c, cur=c["hp"], dmg=c["dmg"] * boost) for c in party] + [dict(c, cur=c["hp"]) for c in foes]
        rng.shuffle(cs)
        order = sorted(cs, key=lambda c: rng.randint(1, 20), reverse=True)
        pcs, mons = [c for c in cs if c["side"] == "party"], [c for c in cs if c["side"] == "foe"]
        r = 0
        while r < 20 and any(c["cur"] > 0 for c in pcs) and any(c["cur"] > 0 for c in mons):
            r += 1
            for c in order:
                if c["cur"] <= 0:
                    continue
                targets = [t for t in (mons if c["side"] == "party" else pcs) if t["cur"] > 0]
                for _a in range(c["attacks"]):
                    if not targets:
                        break
                    t = min(targets, key=lambda x: x["cur"]) if c["side"] == "party" else rng.choice(targets)
                    roll = rng.randint(1, 20)
                    if roll == 20 or (roll != 1 and roll + c["atk"] >= t["ac"]):
                        t["cur"] -= c["dmg"] * (2 if roll == 20 else 1) * rng.uniform(0.6, 1.4)
                        if t["cur"] <= 0:
                            targets.remove(t)
        down = sum(c["cur"] <= 0 for c in pcs)
        won = not any(c["cur"] > 0 for c in mons) and down < len(pcs)
        wins += won
        rounds += r
        downs += down
        any_down += down > 0
        tpk += down == len(pcs)
        hp_left += sum(max(0, c["cur"]) for c in pcs) / total_hp
    return dict(win=wins / runs, rounds=rounds / runs, downs=downs / runs, any_down=any_down / runs,
                tpk=tpk / runs, hp_left=hp_left / runs)


def verdict(sim):
    if sim["tpk"] >= 0.1 or sim["win"] < 0.7:
        return "Lethal"
    if sim["any_down"] >= 0.5 or sim["win"] < 0.9:
        return "Dangerous"
    if sim["hp_left"] > 0.85 and sim["rounds"] <= 2.5:
        return "Trivial"
    if sim["hp_left"] > 0.65:
        return "Easy"
    return "Solid challenge"
