# Dungeon Master's Table

A native desktop virtual tabletop for Windows and Linux, built with Python and Qt (PySide6), in a dark medieval style.

## Development environment

Everything runs inside a virtual environment in `.venv` in this folder, with exact versions pinned in `requirements.txt`.

First time (or on a new machine):

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt        # Windows
.venv/bin/python -m pip install -r requirements.txt            # Linux
```

Activate it to use `python`, `pip` and `pyinstaller` from the venv: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Linux).

## Run from source

```
python main.py
```

- A **launcher** opens first: choose **The Table** (the VTT), **Map Forge** (the map editor) or the **Brewery** (homebrew). Closing an app brings you back. `python main.py --table`, `--forge` or `--brewery` skips the launcher.
- The **admin window** goes on your screen. Browser-style tabs along the top split it into pages: **Table** (map preview inside the gold frame, plus the Realm and Inspector panels), **Combat**, **Journal**, **Encounter**, **Loot**, **Rules** and **Sounds**. **Ctrl+1 to Ctrl+7** jump between them.
- The **player display** opens fullscreen on the second monitor and shows only the table.
- The campaign auto-saves on close to `campaign.json`. Use **Campaign → Save as / Open** to keep several campaigns.

## Build an executable

PyInstaller doesn't cross-compile, so build on each OS you want to run on, with the venv active:

```
pyinstaller --onefile --windowed --name DMTable --icon assets/dmtable.ico main.py
```

## Features

| Area | What you get |
|---|---|
| Maps | Image, animated GIF or video (with optional sound). Zoom, pan and fit from the admin window. Grid with snapping. |
| Creatures | Coloured or image tokens. Side rings: PC blue, ally green, enemy red, neutral gold. Bloodied ring. HP bars (players see PC bars only, optional). |
| Conditions | All 2014 and 2024 conditions as badges around the token's ring. Hover for a summary for the chosen edition. Exhaustion levels, concentration and custom effects. |
| Objects | Place your own images. Resize with Ctrl+wheel, turn with Alt+wheel. Choose above or below creatures. |
| Interactive objects | Triggered with the Interact tool or a double-click. They can open/close (swap to an "open" image or vanish), toggle their light, play a sound, pulse/shake/glow, reveal everything with a tag (a secret passage, lifting the fog over it), change the weather, or open a journal entry. |
| Lighting | Darkness level and tint, a time-of-day sky (dawn, dusk, night) with optional passing time. Light presets per creature or object: torch, candle, lantern, campfire, Light, Daylight, plus arcane, fey, hellfire and necrotic coloured light. Flickering flames. |
| Weather | Rain, thunderstorm with lightning, snow, fog banks, ash with embers, magic motes, sandstorm. Intensity and wind. One-click environment presets. |
| Initiative | Add creatures, roll NPC initiative, next/prev turn with a round counter, and auto-skip of slain monsters. Damage, heal and temp HP (resistant, vulnerable or immune) for one or many targets. Concentration DC prompts, unconscious/death handling, and timed conditions that count down. Combat log. |
| DM-only layer | Hidden creatures and objects, secret notes and traps, DM notes on everything. Fog and darkness are see-through for you and solid for the players. |
| Loot & rewards | Treasure rolls by challenge tier, individual or hoard, difficulty, location, enemy type and max rarity. Coins, gems, art, magic items picked to fit the place and foe, plus trinkets. "From encounter" fills these in. Give items to PCs or the party stash, split coins evenly, undo. Per-PC reward history with gp totals. Custom loot tables (`weight \| name \| rarity \| value`). |
| Encounter balancing | Difficulty by 2014 (Easy to Deadly, with the group multiplier) or 2024 (Low to High) XP rules, using PC levels and monster CRs. A Monte Carlo simulation of hundreds of fights (party resources fresh, some used or depleted) reports win %, TPK %, downed PCs, rounds and HP left, so you can spot lethal or trivial fights. |
| Rules reference | Search core rules, ~100 spells, all conditions and every magic item in the loot list, with short summaries and 2024 differences. **Homebrew weapons** and **Homebrew creatures** come straight from the Brewery: ✚ buttons create new ones there, and Edit opens the selected one there. **Homebrew rules** are your own campaign house-rule notes. |
| Sounds | **Music**: playlists per mood (Tavern, Battle, Dungeon…), drag to reorder, play/pause, previous/next, seek bar, shuffle, repeat playlist / track / play once, music volume. **Soundboard**: a pad per sound effect that can play over each other; loop pads (↻) for ambience like rain or fire; per-pad volume, rename, change file or remove (right-click); effects volume (also used by sounds that triggered map objects play) and Stop all. Saved with the campaign. |
| Journal | Locations, NPCs, quests, items, handouts, lore. Portraits, Markdown text with `[[wiki links]]`, relationships, "mentioned in" backlinks, voice notes (record or attach), pins on the map, a "this map only" filter, and showing a handout image to the players. |

## Map Forge

- **Paint, Room, Fill, Erase** terrain: stone, wood, cave, grass, dirt, sand, water, lava, chasm. Walls, shadows, rough natural edges and shorelines draw themselves around what you paint.
- **Objects**: doors, chests, pillars, statues, altars, thrones, furniture, stairs, torches, traps, trees, boulders and more.
- **Chunks**: 23 ready-made pieces (halls, shrines, throne room, vault, prison, library, crypt, junctions, lava bridge, chasm crossing, cave pockets, clearing, ruined tower, graveyard, village well). Click one, then click the map; **R** rotates, **F** flips. **Save selection as chunk** makes your own (stored in `forge_chunks.json`).
- **Generate** with a seed: **Dungeon** (rooms and corridors, doors, themed rooms, special chunk rooms, traps, stairs up/down), **Caves** (cellular automata, lakes or lava), **Wilderness** (forest, river with sandy banks, road with a bridge, campsite). Forge the whole map or **just a selected area**, then refine by hand. Same seed = same map.
- **Send to the Table**: opens the map in the VTT with the grid matched (70 px squares). Doors, chests, torches and traps become live objects: doors open and close, chests open and glow, torches light up the dark, and traps are DM-only markers.
- Undo/redo, save/open (`.dmap` in `maps/`), and export PNG at any square size, with or without grid and traps.

## Brewery

Everything you brew is saved by itself to `brewery.json` next to the program and shared with the other apps right away, even while they are open.

- **Items**: name, type, subtype, rarity (up to artifact), attunement, magic bonus, damage, AC, charges and recharge, properties, value, weight, image and description. They show up in the **Rules** reference and can drop from the **Loot** generator ("Include Brewery items"; artifacts never drop randomly).
- **Forge objects**: your own image (plus an "open" image), or a built-in shape; size in squares; light (any preset or custom colour, bright/dim radius and flicker); lit at the start; opens/closes when triggered; sound; animation; hidden from players; above creatures; DM notes. They appear in **Map Forge → Objects** (marked ✦), drawn with their light glow, and become live objects on the Table when you use **Send to the Table**.
- **Bestiary**: full stat blocks you can edit field by field: size, type, alignment, CR, AC, HP and hit dice, speed, all six abilities, saves, skills, vulnerabilities, resistances, immunities, senses, languages, traits, actions, bonus actions, reactions and legendary actions, plus token colour and image. Start **from scratch**, **from a template** (22 SRD monsters from kobold to young red dragon, or one of your own), use **Fill stats for its CR**, or recompute HP from the hit dice. They appear in the Table's **Place → Bestiary** search dropdown (marked ✦, alongside the 22 SRD monsters; type any part of a name, pick to place) and in the right-click menu ("Bestiary creature here") as ready-made tokens with HP, AC, initiative, CR, size and their actions in the DM notes. The **Encounter** tab rates and simulates them like any other monster, and the **Rules** tab shows their stat blocks.

## Controls

- **1-4**: Select, Interact, Reveal fog, Hide fog. **Esc**: back to Select. **N**: next turn. **Middle-drag** always pans.
- **Select tool**: drag things to move them, drag empty map to pan, wheel to zoom. **Delete** removes the selection.
- **Right-click** the map to add creatures, lights, notes, traps and objects. Right-click a thing to hide/reveal it, add it to initiative, duplicate or delete it.

## Icons

The icons are drawn in code (`vtt/icons.py`): a d20 in a gear for the launcher and exe, a d20 showing **VTT** for the table, a d20 with an anvil for Map Forge, and a teal d20 with a potion flask for the Brewery. `python -m vtt.icons` rewrites `assets/*.ico` and `*.png`; use the PNGs for a Linux `.desktop` entry.

## Linux notes

On Wayland the compositor decides which screen a window goes on. If the display opens on the wrong screen, run with `QT_QPA_PLATFORM=xcb python main.py`.

## Test

```
python test_vtt.py
```

## Credits

This work includes material taken from the System Reference Document 5.1 ("SRD 5.1") by Wizards of the Coast LLC and available at https://dnd.wizards.com/resources/systems-reference-document. The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at https://creativecommons.org/licenses/by/4.0/legalcode.
