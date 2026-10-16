import os
import re
import sys
import json
import sqlite3
import subprocess
import requests
import colorsys
import math
from PIL import Image

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
DB_PATH = os.path.join(PROJECT_DIR, "data", "aatam.db")
STATIC_DIR = os.path.join(PROJECT_DIR, "static")
IMAGES_DIR = os.path.join(STATIC_DIR, "images")
VIDEOS_DIR = os.path.join(STATIC_DIR, "videos")
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "generated_manim")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(SCRIPTS_DIR, exist_ok=True)

try:
    from .aatam_db import aatam_db
except ImportError:
    from backend.aatam_db import aatam_db

try:
    from .llm_manager import llm_manager
except ImportError:
    from backend.llm_manager import llm_manager

def get_game_data(bgg_id: int):
    # Use custom AatamDB primary key lookup
    data = aatam_db.find_one(bgg_id)
    if data:
        return data
    # Fallback to SQLite if needed
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games WHERE bgg_id = ?", (bgg_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None

def download_and_prepare_image(bgg_id: int, image_url: str) -> str:
    """Download cover image from BGG and save locally."""
    local_path = os.path.join(IMAGES_DIR, f"game_{bgg_id}.jpg")
    if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
        return local_path

    if not image_url or not image_url.startswith("http"):
        img = Image.new("RGB", (600, 600), color=(30, 41, 59))
        img.save(local_path)
        return local_path

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(image_url, headers=headers, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(local_path, "wb") as f:
                f.write(resp.content)
            with Image.open(local_path) as im:
                im.verify()
            return local_path
    except Exception as e:
        print(f"Error downloading image for {bgg_id}: {e}")

    img = Image.new("RGB", (600, 600), color=(30, 41, 59))
    img.save(local_path)
    return local_path

def sanitize_text(text: str, max_len: int = None) -> str:
    """Escape text for a Manim string. Keep every word."""
    if not text:
        return ""
    clean = re.sub(r'["\n\r\\]', ' ', str(text)).strip()
    clean = re.sub(r'\s+', ' ', clean)
    return clean

def wrap_text_manim(text: str, max_chars_per_line: int = 32, max_lines: int = None) -> str:
    """Wrap on word boundaries. Never drop a word."""
    if not text:
        return ""
    clean = re.sub(r'["\n\r\\]', ' ', str(text)).strip()
    clean = re.sub(r'\s+', ' ', clean)
    words = clean.split()
    lines = []
    curr = []
    curr_len = 0
    for w in words:
        add_len = len(w) + (1 if curr else 0)
        if curr and curr_len + add_len > max_chars_per_line:
            lines.append(" ".join(curr))
            curr = [w]
            curr_len = len(w)
        else:
            curr.append(w)
            curr_len += add_len
    if curr:
        lines.append(" ".join(curr))
    return "\\n".join(lines)

def search_duckduckgo_game(game_name: str) -> str:
    """Search DuckDuckGo online for official instructions, components, rules, and strategies."""
    from bs4 import BeautifulSoup
    query = f"{game_name} board game official rules components how to play winning strategy"
    url = "https://html.duckduckgo.com/html/?q=" + requests.utils.quote(query)
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.post(url, headers=headers, timeout=12)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            snippets = []
            for item in soup.find_all("div", class_="result"):
                a = item.find("a", class_="result__a")
                s = item.find("a", class_="result__snippet")
                if a and s:
                    t_txt = a.get_text(strip=True)
                    s_txt = s.get_text(strip=True)
                    if t_txt and s_txt:
                        snippets.append(f"{t_txt}: {s_txt}")
            if snippets:
                print(f"[DuckDuckGo] Found {len(snippets)} search results for '{game_name}'")
                return "\n".join(snippets[:7])
    except Exception as e:
        print(f"[DuckDuckGo] Search warning for '{game_name}': {e}")
    return ""

def generate_custom_game_text_zai(game_name: str, search_snippets: str, reference_game: str = "Catan", game_meta: dict = None) -> dict:
    cfg = llm_manager.get_config()

    mechanics = (game_meta.get("mechanics", "") if game_meta else "")[:120]
    description = (game_meta.get("description", "") if game_meta else "")[:250]

    prompt = f"""Game: {game_name}
Reference Game: {reference_game}
Mechanics: {mechanics}
Overview: {description}
Web Context: {search_snippets[:1200] if search_snippets else "No web results; synthesize from mechanics and title."}

Extract authentic, non-generic gameplay rules. Output exactly with these prefixes:
COMPONENTS: (List 2 to 4 authentic components, comma-separated)
SETUP: (1 clear sentence describing how to set up the board and starting pieces)
REFERENCE_HOW: (1 sentence explaining how {reference_game} works)
THIS_HOW: (1 sentence explaining how {game_name} works)
EVOLUTION: (1 sentence explaining how {game_name} evolves the mechanics)
PHASES: (List 2 to 4 turn phases in order, separated by ' | '. Format each phase as: NAME : ACTION_DESCRIPTION)
CORE_ACTION_TITLE: (Title of primary action mechanism, e.g. TILE CONNECTION & MEEPLE PLACEMENT)
CORE_ACTION_RULE: (1 precise sentence explaining placement constraint, cost, or key rule)
SCORING: (List 2 to 4 concrete scoring rules separated by ' | ', e.g. Roads: 1 pt/tile | Cities: 2 pts/tile)
WIN_TRIGGER: (1 clear sentence stating victory condition and win trigger)
STRAT_OPENING: (Opening strategy tip in 10-12 words)
STRAT_MIDGAME: (Midgame strategy tip in 10-12 words)
STRAT_ENDGAME: (Endgame strategy tip in 10-12 words)
"""

    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3000,
        "temperature": 0.15
    }

    try:
        res_data = llm_manager.chat_completion(payload, timeout=int(cfg.get("timeout_seconds", 60)))
        if res_data:
            content = res_data["choices"][0]["message"].get("content") or ""
            extracted = {}
            for line in content.split("\n"):
                line = line.strip()
                if ":" in line:
                    prefix, val = line.split(":", 1)
                    prefix = prefix.strip().upper()
                    val = val.strip().strip("()")
                    if prefix and val:
                        extracted[prefix] = val
            if len(extracted) >= 5:
                return extracted
    except Exception as e:
        print(f"[z.ai] Text generation warning for '{game_name}': {e}")
    return {}

def extract_game_palette(image_path: str, game: dict) -> dict:
    """Extract a vibrant visual palette directly from the game's box art."""
    extracted_primary = None
    extracted_secondary = None
    extracted_accent = None
    extracted_bg = None
    extracted_card_bg = None

    if image_path and os.path.exists(image_path) and os.path.getsize(image_path) > 1000:
        try:
            with Image.open(image_path) as im:
                img_rgb = im.convert("RGB")
                img_small = img_rgb.resize((150, 150))
                quantized = img_small.quantize(colors=24, method=Image.Quantize.MEDIANCUT)
                palette_bytes = quantized.getpalette()[:72]
                counts = quantized.getcolors() or []
                counts.sort(key=lambda x: x[0], reverse=True)
                
                candidates = []
                for count, idx in counts:
                    r = palette_bytes[idx * 3]
                    g = palette_bytes[idx * 3 + 1]
                    b = palette_bytes[idx * 3 + 2]
                    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
                    if s >= 0.14 and 0.35 <= l <= 0.88:
                        score = (s ** 1.2) * (l ** 0.9) * (count ** 0.4)
                        candidates.append((score, h, l, s, f"#{r:02x}{g:02x}{b:02x}"))
                
                candidates.sort(key=lambda x: x[0], reverse=True)
                if candidates:
                    extracted_primary = candidates[0][4]
                    prim_h = candidates[0][1]
                    prim_s = candidates[0][3]

                    for cand in candidates[1:]:
                        if abs(cand[1] - prim_h) >= 0.08:
                            extracted_secondary = cand[4]
                            break

                    for cand in candidates[1:]:
                        if abs(cand[1] - prim_h) >= 0.16 and cand[4] != extracted_secondary:
                            extracted_accent = cand[4]
                            break

                    bg_r, bg_g, bg_b = colorsys.hls_to_rgb(prim_h, 0.09, min(0.68, max(0.40, prim_s * 0.9)))
                    extracted_bg = f"#{int(bg_r * 255):02x}{int(bg_g * 255):02x}{int(bg_b * 255):02x}"

                    card_r, card_g, card_b = colorsys.hls_to_rgb(prim_h, 0.14, min(0.60, max(0.35, prim_s * 0.85)))
                    extracted_card_bg = f"#{int(card_r * 255):02x}{int(card_g * 255):02x}{int(card_b * 255):02x}"
        except Exception as e:
            print(f"[PaletteExtraction] Warning during color extraction: {e}")

    themes_str = (game.get("themes") or "").lower()
    name_str = (game.get("name") or "").lower()

    if any(k in themes_str or k in name_str for k in ["space", "sci-fi", "mars", "alien", "cyber"]):
        default_primary = "#38bdf8"
        default_secondary = "#e11d48"
        default_accent = "#fbbf24"
        default_bg = "#160a22"
        default_card_bg = "#221035"
    elif any(k in themes_str or k in name_str for k in ["nature", "bird", "forest", "animal", "ocean", "farming"]):
        default_primary = "#10b981"
        default_secondary = "#38bdf8"
        default_accent = "#f59e0b"
        default_bg = "#071f16"
        default_card_bg = "#0d2e22"
    elif any(k in themes_str or k in name_str for k in ["medieval", "fantasy", "castle", "kingdom", "dragon"]):
        default_primary = "#f59e0b"
        default_secondary = "#ef4444"
        default_accent = "#38bdf8"
        default_bg = "#1f1008"
        default_card_bg = "#2d180d"
    elif any(k in themes_str or k in name_str for k in ["catan", "trade", "economic", "civilization"]):
        default_primary = "#f59e0b"
        default_secondary = "#ef4444"
        default_accent = "#10b981"
        default_bg = "#22090e"
        default_card_bg = "#330e15"
    else:
        default_primary = "#f59e0b"
        default_secondary = "#38bdf8"
        default_accent = "#10b981"
        default_bg = "#0f172a"
        default_card_bg = "#1e293b"

    primary = extracted_primary or default_primary
    secondary = extracted_secondary or default_secondary
    accent = extracted_accent if (extracted_accent and extracted_accent != primary and extracted_accent != secondary) else default_accent
    bg_dark = extracted_bg or default_bg
    card_bg = extracted_card_bg if extracted_card_bg else default_card_bg

    return {
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "bg_dark": bg_dark,
        "glow_1": primary,
        "glow_2": secondary,
        "card_bg": card_bg
    }

# =========================================================================
# AUTHORITATIVE GAME RULES & INSTRUCTIONS KNOWLEDGE BASE
# =========================================================================
GAME_RULES_KNOWLEDGE_BASE = {
    13: {  # Catan
        "archetype": "spatial_hex",
        "components": [
            ("Modular Terrain Hexes", "19 hexes (Forest, Hill, Pasture, Field, Mountain) + Desert"),
            ("Numbered Chits", "Tokens 2-12 determining hex harvest odds on 2d6 rolls"),
            ("Settlements & Roads", "Player expansion pieces placed along hex vertices & edges"),
            ("Resource Cards", "Wood, Brick, Sheep, Wheat, and Ore commodity decks")
        ],
        "setup_directive": "Assemble modular island, distribute numbered tokens, and have each player place 2 starting settlements and 2 roads.",
        "phases": [
            ("PRODUCE", "ROLL & HARVEST", "Active player rolls 2d6; every player on adjacent hexes harvests resource cards"),
            ("TRADE", "BARTER WITH RIVALS", "Exchange commodities with rivals or trade with maritime ports at 4:1, 3:1, or 2:1 rates"),
            ("EXPAND", "BUILD INFRASTRUCTURE", "Spend resources: Road (wood+brick), Settlement (wood+brick+wheat+sheep), City (3 ore+2 wheat)")
        ],
        "core_action_title": "HEX RESOURCE HARVEST & SETTLEMENT NETWORK",
        "core_action_rule": "Distance Rule: Settlements must be placed at least 2 road edges apart. Rolling a 7 activates the Robber and forces discards over 7 cards!",
        "scoring": [
            ("+1 VP", "Each Settlement constructed on the board"),
            ("+2 VP", "Each Upgraded City (+1 VP over settlement)"),
            ("+2 VP Bonus", "Longest Continuous Road (5+ connected segments)"),
            ("+2 VP Bonus", "Largest Army (3+ Knight cards activated)")
        ],
        "win_trigger": "First player to claim 10 Victory Points on their turn wins immediately!",
        "strategies": [
            ("Early Game", "Secure high-probability hexes (6 & 8) with diverse resources; brick and wood enable early road dominance."),
            ("Mid Game", "Upgrade key settlements to cities early for double resource yields; monopolize a port to bypass trade blockades."),
            ("Endgame", "Hold secret victory point Development Cards in hand until you can trigger a sudden 10 VP victory sprint!")
        ]
    },
    822: {  # Carcassonne
        "archetype": "tile_placement",
        "components": [
            ("Landscape Tiles", "72 terrain tiles depicting roads, walled cities, cloisters & fields"),
            ("Worker Meeples", "8 meeples per player (1 on score track, 7 in hand)"),
            ("Score Track", "50-point track recording immediate feature completion points")
        ],
        "setup_directive": "Place the starting landscape tile face-up in center of table and deal 7 meeples to each player.",
        "phases": [
            ("DRAW & PLACE", "EXPAND LANDSCAPE", "Draw 1 landscape tile and place it matching existing edges (roads connect to roads, cities to cities)"),
            ("CLAIM FEATURE", "ASSIGN MEEPLE", "Optionally place 1 meeple on an unclaimed feature of the new tile (Road, City, Cloister, or Field)"),
            ("SCORE & RECALL", "RETURN MEEPLES", "Score completed features immediately and return assigned meeples to your hand")
        ],
        "core_action_title": "DYNAMIC LANDSCAPE EXPANSION & MEEPLE ASSIGNMENT",
        "core_action_rule": "Meeples become Highwaymen on roads (1 pt/tile), Knights in cities (2 pts/tile + 2 per shield), Monks in cloisters (9 pts when surrounded), and Farmers in fields!",
        "scoring": [
            ("+1 pt / tile", "Completed Roads (closed at both ends)"),
            ("+2 pts / tile", "Completed Cities (+2 bonus per coat of arms crest)"),
            ("+9 pts", "Completed Cloisters (fully surrounded by 8 adjacent tiles)"),
            ("+3 pts / city", "Farmers on pastures adjacent to finished cities at end")
        ],
        "win_trigger": "Highest total score after the last landscape tile is played and farmer field majorities are tallied!",
        "strategies": [
            ("Early Game", "Keep at least 2-3 meeples in reserve; never strand all 7 meeples in unfinished sprawling cities."),
            ("Mid Game", "Sneak onto rivals' high-value cities by placing adjacent tiles and merging roads to share or steal majority."),
            ("Endgame", "Deploy farmers onto vast interconnected pasture networks feeding into multiple finished cities for massive bursts.")
        ]
    },
    30549: {  # Pandemic
        "archetype": "cooperative",
        "components": [
            ("World Map Board", "Global network of 48 cities linked by major travel routes"),
            ("Disease Cubes", "96 wooden cubes across 4 distinct global plague strains"),
            ("Player Roles", "Unique specialist cards (Dispatcher, Medic, Researcher, Scientist)"),
            ("City & Infection Decks", "Player resource deck with Epidemics & Infection draw deck")
        ],
        "setup_directive": "Seed 9 starting cities with disease cubes, deal specialist roles, and prepare player deck with epidemic cards.",
        "phases": [
            ("ACTIONS", "TAKE 4 ACTIONS", "Drive/ferry, direct/charter flights, treat disease cubes, share knowledge, or build research stations"),
            ("DRAW CARDS", "SUPPLY & EPIDEMICS", "Draw 2 player cards; resolving Epidemic cards increases infection rate & reshuffles infect deck"),
            ("INFECT CITIES", "SPREAD PLAGUES", "Flip infection cards matching current rate and add disease cubes to indicated cities")
        ],
        "core_action_title": "SPECIALIST COLLABORATION & OUTBREAK CONTAINMENT",
        "core_action_rule": "If a 4th cube would be added to any city, an Outbreak occurs, spreading cubes to all connected cities and moving the outbreak tracker!",
        "scoring": [
            ("BLUE CURE", "Discover Cure for Blue Strain (5 matching cards at Station)"),
            ("YELLOW CURE", "Discover Cure for Yellow Strain (5 matching cards)"),
            ("BLACK CURE", "Discover Cure for Black Strain (5 matching cards)"),
            ("RED CURE", "Discover Cure for Red Strain (5 matching cards)")
        ],
        "win_trigger": "Discover cures for all 4 diseases to win together! Defeat triggers if 8 outbreaks occur or disease cubes run out!",
        "strategies": [
            ("Early Game", "Contain 3-cube hotspot cities immediately to prevent early chain-reaction outbreaks."),
            ("Mid Game", "Leverage specialist role synergies (e.g. Researcher card sharing) to assemble 5 matching color cards."),
            ("Endgame", "Coordinate logistics so the cure-bearer reaches a research station before the player draw deck empties.")
        ]
    },
    161936: {  # Pandemic Legacy Season 1
        "archetype": "cooperative",
        "components": [
            ("World Map Board", "Evolving world map tracking panic levels and quarantine zones"),
            ("Disease Strains", "4 global pathogens, one of which mutates into non-treatable COdA-403a"),
            ("Legacy Docket & Cards", "Top-secret dossiers, scratch-off cards, and permanent sticker sheets")
        ],
        "setup_directive": "Review monthly mission objectives, apply persistent upgrades, and seed infection deck based on prior game outcomes.",
        "phases": [
            ("ACTIONS", "4 TACTICAL ACTIONS", "Travel routes, treat diseases, build military/research bases, or search infection zones"),
            ("DRAW CARDS", "LEGACY ADVANCE", "Draw 2 player cards and resolve Epidemics that permanently accelerate panic levels"),
            ("INFECT", "OUTBREAK COLLAPSE", "Flip infection cards; outbreaks permanently degrade city stability toward Fallen status")
        ],
        "core_action_title": "LEGACY CAMPAIGN & PERMANENT WORLD MUTATION",
        "core_action_rule": "Characters take scars when caught in outbreaks; cities suffer permanent riots and roadblocks across the 12-month campaign!",
        "scoring": [
            ("CURE PATHOGENS", "Discover cures for curable disease strains"),
            ("SABOTAGE / QUARANTINE", "Establish quarantine barriers around infected zones"),
            ("MONTHLY MISSIONS", "Fulfill specific plot objectives before deck runs out")
        ],
        "win_trigger": "Complete all designated monthly objectives before outbreaks reach 8 or the player deck is exhausted!",
        "strategies": [
            ("Early Game", "Prioritize quarantine over treating when traveling through rioting cities to protect character health."),
            ("Mid Game", "Assign permanent character relationship perks to speed up card passing between key researchers."),
            ("Endgame", "Sacrifice secondary cities if necessary to secure vital objective checkpoints before the month ends.")
        ]
    },
    266192: {  # Wingspan
        "archetype": "card_engine",
        "components": [
            ("Player Habitat Mats", "Individual boards with Forest, Grassland, and Wetland action rows"),
            ("Bird Cards", "Deck of 170 unique illustrated birds with habitat, food cost & abilities"),
            ("Birdfeeder Dice", "Wooden dice rolled into birdfeeder tower to generate 5 food types"),
            ("Miniature Eggs", "Colored eggs placed onto bird nests to pay placement costs")
        ],
        "setup_directive": "Give each player a habitat mat, 5 bird cards & 5 food tokens (keep any combination totaling 5), and 2 bonus cards.",
        "phases": [
            ("SELECT ROW", "CHOOSE ACTION ROW", "Place action cube on Forest (Gain Food), Grassland (Lay Eggs), or Wetland (Draw Bird Cards)"),
            ("GATHER / DEPLOY", "EXECUTE ROW ACTION", "Collect designated food dice, eggs, or cards, or pay food and eggs to play a bird into that row"),
            ("BROWN POWERS", "ACTIVATE ENGINE", "Activate all brown bird powers in that habitat row from right to left!")
        ],
        "core_action_title": "HABITAT ENGINE BUILDING & COMPOUND BIRD POWERS",
        "core_action_rule": "Playing birds deeper into habitats requires egg sacrifices from other birds; card synergy cascades trigger recurring resource loops!",
        "scoring": [
            ("BIRD CARDS", "Printed Victory Points on Deployed Birds (1 to 9 VP)"),
            ("BONUS OBJECTIVES", "End-Game Secret Card Threshold Points"),
            ("ROUND GOALS", "Tally Points from 4 End-of-Round Goal Tiles"),
            ("+1 pt Each", "Laid Eggs, Cached Food & Tucked Flock Cards")
        ],
        "win_trigger": "Highest total score after 4 rounds across birds, eggs, caches, tucked cards, and round goals!",
        "strategies": [
            ("Early Game", "Prioritize birds that generate food or draw extra cards to jumpstart engine velocity."),
            ("Mid Game", "Align bird deployments with round goal tiles and your secret bonus card requirements."),
            ("Endgame", "Focus on high-capacity egg spam or birds with massive printed VP (7-9 pts) to out-score engine loops in Round 4.")
        ]
    },
    68448: {  # 7 Wonders
        "archetype": "card_engine",
        "components": [
            ("Wonder Boards", "Historic wonders (Pyramids, Colossus, etc.) with 3 construction stages"),
            ("Age Decks I, II, III", "Card decks scaled to player count (raw materials, science, military, guilds)"),
            ("Treasury Coins", "Gold and silver coins used to trade with neighboring cities")
        ],
        "setup_directive": "Assign wonder boards, distribute 3 starting coins, and prepare 3 separate Age decks scaled to player count.",
        "phases": [
            ("DRAFT CARD", "SIMULTANEOUS CHOICE", "Examine your hand, choose 1 card to play, and place it face-down"),
            ("REVEAL & PLAY", "CONSTRUCT OR TRADE", "Simultaneously reveal: pay resource costs to build, discard for 3 coins, or build Wonder stage"),
            ("PASS HAND", "CIRCULATE REMAINING", "Pass remaining cards to your neighbor (clockwise in Age I & III, counter-clockwise in Age II)")
        ],
        "core_action_title": "SIMULTANEOUS CARD DRAFTING & NEIGHBOR COMMERCE",
        "core_action_rule": "Pay 2 coins to borrow resources produced by left/right neighbors; science cards score quadratically: n^2 per symbol + 7 per complete set of 3!",
        "scoring": [
            ("CIVILIAN / BLUE", "Direct printed victory point buildings"),
            ("SCIENCE / GREEN", "Quadratic scoring: n² per symbol + 7 per set of 3"),
            ("COMMERCIAL / GUILDS", "Market bonuses and yellow/purple endgame triggers"),
            ("MILITARY / RED", "War conflict victory tokens (+1, +3, +5 per Age)")
        ],
        "win_trigger": "Highest victory point sum after 3 Ages across military, civilian, commercial, science, guild, and wonder stages!",
        "strategies": [
            ("Early Game", "Secure foundational brown/grey raw materials in Age I to avoid bleeding coins to neighbors in later Ages."),
            ("Mid Game", "Commit heavily to science sets if left uncontested, or deny high-value military cards to prevent rival sweeps."),
            ("Endgame", "Draft high-scoring purple Guild cards that capitalize on your neighbors' building choices for huge VP spikes.")
        ]
    },
    178900: {  # Codenames
        "archetype": "deduction",
        "components": [
            ("Codename Cards", "200 double-sided cards with everyday words laid out in a 5x5 grid"),
            ("Key Cards", "Grids showing secret identities: Red agents, Blue agents, bystanders & Assassin"),
            ("Agent Tiles", "Red operative, Blue operative, innocent bystander, and Assassin cover tiles")
        ],
        "setup_directive": "Lay out 25 word cards in a 5x5 grid; Spymasters examine the key card revealing agent positions.",
        "phases": [
            ("SPYMASTER CLUE", "TRANSMIT CODEWORD", "Spymaster gives exactly one word and one number indicating how many grid cards connect (e.g. 'Ocean 2')"),
            ("FIELD OPERATIVES", "IDENTIFY AGENTS", "Operatives discuss and touch cards one by one to reveal underlying identities"),
            ("RESOLVE", "TEAM ADVANTAGE", "Correct team card continues guess (up to clue+1); bystander or rival card ends turn immediately")
        ],
        "core_action_title": "ASSOCIATIVE DEDUCTION & ASSASSIN HAZARD",
        "core_action_rule": "Spymasters must give clues without word derivations or letter references. Touching the black Assassin card causes instant loss!",
        "scoring": [
            ("RED TEAM AGENTS", "Reveal all 8 or 9 Red Agent cards"),
            ("BLUE TEAM AGENTS", "Reveal all 8 or 9 Blue Agent cards"),
            ("AVOID BYSTANDERS", "Bystander cards consume guesses and end turn"),
            ("ASSASSIN DANGER", "Touching Assassin causes immediate sudden-death defeat!")
        ],
        "win_trigger": "First team to identify and cover all of their secret agent words on the board wins!",
        "strategies": [
            ("Early Game", "Spymasters look for strong 2-word or 3-word conceptual clusters that have zero proximity to the Assassin card."),
            ("Mid Game", "Field operatives should carry forward unused clues from previous turns when safe connections exist."),
            ("Endgame", "If trailing, Spymasters must take calculated risks on ambitious 3+ word clues to engineer a comeback victory.")
        ]
    },
    14996: {  # Ticket to Ride: Europe
        "archetype": "rail_network",
        "components": [
            ("Europe Map Board", "Map connecting iconic European cities with colored rail routes"),
            ("Colored Train Cars", "Plastic trains (45 per player) used to claim routes on board"),
            ("Train & Ticket Cards", "Color-matched train car cards, ferries, tunnels, and destination tickets")
        ],
        "setup_directive": "Deal 4 train cards and 1 long + 3 regular destination tickets to each player (keep at least 2), and reveal 5 market cards.",
        "phases": [
            ("DRAW CARDS", "COLLECT TRAINS", "Draw 2 train cards from face-up market or blind deck (or 1 wild locomotive)"),
            ("CLAIM ROUTE", "PLACE TRAINS", "Discard matching colored train cards equal to route length and place plastic trains"),
            ("DRAW TICKETS", "EXPAND DESTINATIONS", "Draw 3 destination tickets and keep at least 1 for end-game connection scoring")
        ],
        "core_action_title": "COLOR-MATCHED ROUTE CLAIMING & TUNNEL/FERRY LOGISTICS",
        "core_action_rule": "Longer routes score exponentially (1 car=1pt, 6 cars=15pts, 8 cars=21pts); completed destination tickets score printed points, but uncompleted tickets subtract!",
        "scoring": [
            ("ROUTE LENGTH", "Instant points: 1 car=1pt, 2=2pts, 3=4pts, 4=7pts, 6=15pts, 8=21pts"),
            ("DESTINATION TICKETS", "Complete connecting cities for positive points (uncompleted subtract!)"),
            ("EUROPEAN EXPRESS", "+10 Bonus Points for the single longest continuous train path"),
            ("UNUSED STATIONS", "+4 Bonus Points for each unbuilt train station remaining at end")
        ],
        "win_trigger": "Game end triggers when any player has 2 or fewer trains remaining; highest total points wins!",
        "strategies": [
            ("Early Game", "Stockpile colored cards before revealing intended routes; secure critical bottleneck tunnels early."),
            ("Mid Game", "Complete initial high-value long destination routes before drawing additional tickets."),
            ("Endgame", "Monitor rival train car reserves closely; trigger the end game abruptly when you hold a safe lead.")
        ]
    },
    167791: {  # Terraforming Mars
        "archetype": "card_engine",
        "components": [
            ("Mars Surface Board", "Map with temperature (-30°C to +8°C), oxygen (0% to 14%), and 9 ocean spots"),
            ("Corporation Sheets", "Player boards tracking MegaCredits, Steel, Titanium, Plants, Energy & Heat"),
            ("Project Card Deck", "208 unique project cards featuring technology, microbes, animals & infrastructure")
        ],
        "setup_directive": "Deal corporation cards and 10 starting project cards, set global parameters to starting minimums, and place TR at 20.",
        "phases": [
            ("DRAFT & BUY", "RESEARCH PHASE", "Draft 4 project cards each generation and buy selected cards into hand for 3 MegaCredits each"),
            ("EXECUTE ACTIONS", "ACTION ROUNDS", "Take 1-2 actions: play cards, fund standard projects, claim milestones/awards, convert plants/heat"),
            ("PRODUCTION", "HARVEST YIELDS", "Collect MegaCredits (TR + production), steel, titanium, plants, energy, and convert energy into heat")
        ],
        "core_action_title": "GLOBAL PARAMETER TERRAFORMING & CORRESPONDING TR RATING",
        "core_action_rule": "Every step you raise Temperature, Oxygen, or place an Ocean increases your Terraforming Rating (TR), which boosts both VP and recurring income!",
        "scoring": [
            ("TERRAFORMING RATING", "Base TR score earned by terraforming Mars"),
            ("GREENERY & OCEANS", "+1 VP per placed greenery tile and adjacent city tiles"),
            ("MILESTONES & AWARDS", "+5 VP per claimed milestone, 1st & 2nd place award bonuses"),
            ("CARD VICTORY POINTS", "Direct victory point values and variable icon multipliers on played cards")
        ],
        "win_trigger": "Game ends at end of generation where Temperature (+8°C), Oxygen (14%), and 9 Oceans are maxed; highest VP wins!",
        "strategies": [
            ("Early Game", "Focus on card projects that raise MegaCredit and resource production rather than early raw VP cards."),
            ("Mid Game", "Claim accessible milestones (Terraformer, Mayor, Planner) before rivals lock them out."),
            ("Endgame", "Convert high plant reserves into greenery tiles placed around your cities for double-dip scoring.")
        ]
    },
    230802: {  # Azul
        "archetype": "tile_placement",
        "components": [
            ("Factory Displays", "Circular coasters holding 4 colored mosaic tiles drawn from velvet bag"),
            ("Wall Player Boards", "Individual mosaic grids with 5 pattern lines, wall spaces, and floor penalty line"),
            ("Resin Mosaic Tiles", "100 tiles across 5 distinctive Moorish patterns and colors")
        ],
        "setup_directive": "Place 5 to 9 Factory displays in center, seed each with 4 tiles drawn from bag, and distribute player boards.",
        "phases": [
            ("FACTORY OFFER", "DRAFT TILES", "Pick all tiles of one color from any factory (slide remaining to center) or from center pool"),
            ("PATTERN PLACEMENT", "FILL PATTERN LINES", "Place drafted tiles into one row on your pattern line; excess tiles spill into floor penalty line"),
            ("WALL TILING", "SCORE ADJACENCY", "Move 1 tile from completed pattern lines to wall grid and immediately score connected rows/columns")
        ],
        "core_action_title": "COLOR CLUSTERING DRAFT & CONNECTED WALL SCORING",
        "core_action_rule": "Tiles on the floor line deduct -1, -2, or -3 points! A completed wall row immediately triggers final scoring.",
        "scoring": [
            ("TILE PLACEMENT", "+1 pt per newly placed tile + 1 pt per adjacent connected tile in row & column"),
            ("COMPLETED ROWS", "+2 Bonus Points for each complete horizontal line of 5 tiles"),
            ("COMPLETED COLUMNS", "+7 Bonus Points for each complete vertical line of 5 tiles"),
            ("COLOR SETS", "+10 Bonus Points for all 5 tiles of the same color placed on wall")
        ],
        "win_trigger": "Game end triggers immediately after any player completes a horizontal line of 5 tiles; highest points wins!",
        "strategies": [
            ("Early Game", "Complete top short pattern rows (1-3 tiles) early to establish an initial scoring anchor on the wall."),
            ("Mid Game", "Track center pool tiles closely to avoid being forced to draft massive excess colors into floor penalty zones."),
            ("Endgame", "Calculate whether completing a row now wins you the game or gives your rival a column bonus spike.")
        ]
    },
    148228: {  # Splendor
        "archetype": "card_engine",
        "components": [
            ("Development Cards", "90 cards across 3 tiers providing gem discounts and Prestige Points"),
            ("Gem Tokens", "40 weighted poker chips representing Diamond, Sapphire, Emerald, Ruby, Onyx & Gold"),
            ("Noble Tiles", "Aristocratic patrons offering bonus prestige points when card requirements are met")
        ],
        "setup_directive": "Display 4 cards per tier, reveal noble tiles (players + 1), and stack gem tokens by color.",
        "phases": [
            ("COLLECT GEMS", "TAKE TOKENS", "Take 3 different colored gem tokens, or 2 identical tokens (if 4+ remain in stack)"),
            ("RESERVE CARD", "CLAIM WITH GOLD", "Reserve 1 face-up or blind card into personal hand and take 1 gold wild token (max 3 cards held)"),
            ("PURCHASE CARD", "DEPLOY ASSET", "Spend gem tokens to buy a card into tableau; cards provide permanent discount gems for future purchases!")
        ],
        "core_action_title": "PERMANENT GEM DISCOUNTS & NOBLE VISITS",
        "core_action_rule": "Cards purchased into your tableau permanently reduce purchase costs of future cards; matching noble requirements attracts nobles for +3 VP!",
        "scoring": [
            ("TIER 2 & 3 CARDS", "Direct Prestige Points printed on advanced development cards (1 to 5 points)"),
            ("NOBLE PATRONS", "+3 Prestige Points per Noble tile attracted by your tableau color profile"),
            ("PRESTIGE RACE", "First player to reach 15 Prestige Points triggers final round!")
        ],
        "win_trigger": "First player to reach 15 Prestige Points triggers end of round; player with highest points wins!",
        "strategies": [
            ("Early Game", "Acquire inexpensive Tier 1 cards that match your target Noble requirements to build free purchasing power."),
            ("Mid Game", "Reserve key Tier 2/3 cards that your rivals are saving gems for to deny their strategy and secure wild gold."),
            ("Endgame", "Shift away from buying low-tier cards; buy directly into high-VP Tier 3 cards to sprint past 15 points.")
        ]
    }
}

def format_rules_digest(instructions: dict, game_name: str = "this game") -> str:
    """Flatten curated/synthesized instructions into prose the LLM film path must teach."""
    if not instructions:
        return ""
    lines = [f"Game: {game_name}", f"Archetype: {instructions.get('archetype', 'unknown')}"]
    comps = instructions.get("components") or []
    if comps:
        lines.append("Components:")
        for title, body in comps:
            lines.append(f"  - {title}: {body}")
    setup = instructions.get("setup_directive")
    if setup:
        lines.append(f"Setup: {setup}")
    phases = instructions.get("phases") or []
    if phases:
        lines.append("Turn phases (in order):")
        for phase in phases:
            if len(phase) >= 3:
                lines.append(f"  - {phase[0]} / {phase[1]}: {phase[2]}")
            elif len(phase) == 2:
                lines.append(f"  - {phase[0]}: {phase[1]}")
    core_title = instructions.get("core_action_title")
    core_rule = instructions.get("core_action_rule")
    if core_title or core_rule:
        lines.append(f"Core mechanic: {core_title or ''}".strip())
        if core_rule:
            lines.append(f"  {core_rule}")
    scoring = instructions.get("scoring") or []
    if scoring:
        lines.append("Scoring:")
        for title, body in scoring:
            lines.append(f"  - {title}: {body}")
    win = instructions.get("win_trigger")
    if win:
        lines.append(f"Win trigger: {win}")
    strategies = instructions.get("strategies") or []
    if strategies:
        lines.append("Strategy tips:")
        for title, body in strategies:
            lines.append(f"  - {title}: {body}")
    return "\n".join(lines)


def synthesize_game_instructions(game: dict, ddg_snippets: str = None, zai_data: dict = None) -> dict:
    """
    Synthesize rich, authentic, game-specific instructions.
    Checks curated knowledge base first, then z.ai online synthesis,
    then dynamic semantic parsing of game metadata.
    """
    bgg_id = int(game.get("bgg_id", 0))

    # 1. High-priority curated authentic knowledge base
    if bgg_id in GAME_RULES_KNOWLEDGE_BASE:
        return GAME_RULES_KNOWLEDGE_BASE[bgg_id]

    name = game.get("name", "Board Game")
    name_clean = sanitize_text(name, 35)
    mechs = (game.get("mechanics", "") or "").lower()
    themes = (game.get("themes", "") or "").lower()
    desc = (game.get("description", "") or "").lower()
    weight = float(game.get("game_weight", 2.5) or 2.5)
    min_p = game.get("min_players", 2)
    max_p = game.get("max_players", 4)

    # Detect primary archetype
    if any(k in mechs or k in desc for k in ["tile placement", "grid", "hex", "modular board", "pattern building"]):
        archetype = "tile_placement"
    elif any(k in mechs or k in desc for k in ["worker placement", "action drafting"]):
        archetype = "worker_placement"
    elif any(k in mechs or k in desc for k in ["deck", "card drafting", "hand management", "tableau", "engine"]):
        archetype = "card_engine"
    elif any(k in mechs or k in desc for k in ["dice", "roll / spin", "push your luck"]):
        archetype = "dice_movement"
    elif any(k in mechs or k in desc for k in ["deduction", "clue", "hidden", "memory"]):
        archetype = "deduction"
    elif any(k in mechs or k in desc for k in ["network", "route", "rail"]):
        archetype = "rail_network"
    elif any(k in mechs or k in desc for k in ["cooperative", "pandemic"]):
        archetype = "cooperative"
    else:
        archetype = "strategy_tableau"

    # 2. Check if z.ai returned dynamic instructions
    if zai_data:
        comp_str = zai_data.get("COMPONENTS")
        phases_str = zai_data.get("PHASES")
        scoring_str = zai_data.get("SCORING")
        if comp_str and phases_str:
            components = []
            for item in comp_str.split(",")[:4]:
                item = item.strip()
                if item:
                    components.append((item, "Essential starting component"))
            phases = []
            for p in phases_str.split("|")[:4]:
                p = p.strip()
                if ":" in p:
                    pname, pdesc = p.split(":", 1)
                    phases.append((pname.strip().upper(), "ACTION", pdesc.strip()))
                elif p:
                    phases.append(("PHASE", "ACTION", p))
            scoring = []
            if scoring_str:
                for s in scoring_str.split("|")[:4]:
                    s = s.strip()
                    if ":" in s:
                        spoints, srule = s.split(":", 1)
                        scoring.append((spoints.strip(), srule.strip()))
                    elif s:
                        scoring.append(("+VP", s))
            if not scoring:
                scoring = [("+VP", "Milestones & Core Objectives"), ("Bonus", "Endgame Multipliers")]

            return {
                "archetype": archetype,
                "components": components if len(components) >= 2 else [("Central Board & Map", "Shared playing surface"), ("Action Components", "Tokens & player aids")],
                "setup_directive": zai_data.get("SETUP", f"Deploy central board and distribute starting components to {min_p}-{max_p} players."),
                "phases": phases if len(phases) >= 2 else [("ACTION", "CHOOSE", "Select action"), ("RESOLVE", "UPKEEP", "Score and pass turn")],
                "core_action_title": zai_data.get("CORE_ACTION_TITLE", f"{name_clean.upper()} CORE PLAY MECHANISM"),
                "core_action_rule": zai_data.get("CORE_ACTION_RULE", "Execute actions respecting placement constraints and resource limits."),
                "scoring": scoring,
                "win_trigger": zai_data.get("WIN_TRIGGER", "Player with the highest total victory points at end of game wins!"),
                "strategies": [
                    ("Early Game", zai_data.get("STRAT_OPENING", "Establish resource income and board presence early.")),
                    ("Mid Game", zai_data.get("STRAT_MIDGAME", "Chain engine synergies and control contested action spots.")),
                    ("Endgame", zai_data.get("STRAT_ENDGAME", "Sprint for final victory points and fulfill secret objectives."))
                ]
            }

    # 3. Dynamic semantic synthesis from mechanics and metadata
    if archetype == "worker_placement":
        components = [
            ("Worker Pawns & Meeples", f"Player figures assigned to exclusive action spaces"),
            ("Action Docking Bay", "Shared board containing restricted action locations"),
            ("Resource Supply Banks", "Goods, coins, and upgrade materials")
        ]
        setup_directive = f"Place shared action board, distribute worker pawns to {min_p}-{max_p} players, and seed resource banks."
        phases = [
            ("ASSIGN WORKER", "LOCK ACTION SPOT", "Place a meeple onto an unoccupied action dock to execute its ability"),
            ("GATHER YIELDS", "COLLECT RESOURCES", "Collect generated goods, pay costs, or draft technology upgrades"),
            ("UPKEEP & RECALL", "RESET WORKERS", "Retrieve all worker pawns from the board and advance round tracker")
        ]
        core_action_title = "EXCLUSIVE WORKER DOCKING & LOCKOUT DYNAMICS"
        core_action_rule = "Claiming an action dock locks opponents out of that space for the round, securing scarce resources!"
        scoring = [
            ("INFRASTRUCTURE", "Constructed buildings and developed personal mats"),
            ("ACHIEVEMENTS", "Completed public milestone objectives"),
            ("RESOURCE CONVERSION", "Leftover gold, goods, and bonus victory tokens")
        ]
        win_trigger = "Player with the highest total score after final round upkeep claims victory!"

    elif archetype == "card_engine":
        components = [
            ("Project & Action Cards", "Deck containing technologies, characters, and events"),
            ("Player Tableau Mat", "Personal board organizing active ongoing card engines"),
            ("Currency & Resource Tokens", "Commodities spent to pay card deployment costs")
        ]
        setup_directive = f"Shuffle the project deck, deal starting hand of cards, and distribute starting capital to each player."
        phases = [
            ("DRAFT / DRAW", "ACQUIRE PROJECTS", "Draw cards from market display or draw deck into personal hand"),
            ("PLAY INTO TABLEAU", "PAY & DEPLOY", "Pay indicated resource costs to deploy card into active engine tableau"),
            ("TRIGGER COMBOS", "ACTIVATE ABILITIES", "Trigger cascading ongoing abilities and collect recurring resource yields")
        ]
        core_action_title = "TABLEAU ENGINE BUILDING & CARD SYNERGIES"
        core_action_rule = "Every deployed card introduces permanent discounts, ongoing abilities, or compound end-game victory point multipliers!"
        scoring = [
            ("CARD VICTORY POINTS", "Direct printed victory points on deployed tableau cards"),
            ("SET BONUSES", "Multipliers for matching icon sets and suit categories"),
            ("MILESTONE OBJECTIVES", "End-game secret goal thresholds and public award claims")
        ]
        win_trigger = "Highest total victory point sum after round limit or deck trigger wins!"

    elif archetype == "tile_placement":
        components = [
            ("Modular Map Tiles", "Terrain tiles featuring roads, territories, and structures"),
            ("Player Tokens & Markers", "Pieces used to claim majority control on placed tiles"),
            ("Central Starting Anchor", "Initial terrain tile establishing map layout")
        ]
        setup_directive = f"Place starting tile in center, shuffle remaining tiles into draw stacks, and deal pieces to players."
        phases = [
            ("DRAW TILE", "EXPAND MAP", "Draw a terrain tile and place it matching adjacent edges and features"),
            ("CLAIM INFLUENCE", "ASSIGN PIECE", "Optionally place a marker on an unoccupied feature of the placed tile"),
            ("RESOLVE FEATURES", "SCORE COMPLETED", "Tally completed roads, cities, or areas and retrieve eligible markers")
        ]
        core_action_title = "MODULAR MAP ADDITION & FEATURE CLOSURE"
        core_action_rule = "Tiles must perfectly align with neighboring terrain features. Completed features score immediate victory points!"
        scoring = [
            ("COMPLETED FEATURES", "Points scored for closed roads, territories, and structures"),
            ("AREA MAJORITY", "Bonus points awarded to player with most pieces in shared zones"),
            ("ENDGAME MULTIPLIERS", "End-of-game bonuses for surrounding terrain combinations")
        ]
        win_trigger = "Highest score after the final tile is placed and end-game majorities are tallied!"

    elif archetype == "dice_movement":
        components = [
            ("Custom Action Dice", "Polyhedral dice determining movement and harvest outcomes"),
            ("Serpentine Track Board", "Curved track featuring hazard spaces, markets, and checkpoints"),
            ("Player Racing Pawns", "Tokens representing player positions along the route")
        ]
        setup_directive = f"Place board on table, position player pawns at starting zone, and prepare dice supply."
        phases = [
            ("ROLL DICE", "EVALUATE ODDS", "Roll action dice and choose whether to push luck for higher yields or bank rolls"),
            ("TRAVERSE TRACK", "MOVE PAWN", "Advance player pawn along track spaces corresponding to rolled numbers"),
            ("TRIGGER SPACES", "RESOLVE EFFECTS", "Collect rewards on landed spaces or resolve event hazard challenges")
        ]
        core_action_title = "PROBABILITY MANAGEMENT & PUSH-YOUR-LUCK MOMENTUM"
        core_action_rule = "Pushing your luck offers higher rewards but risks busting and forfeiting progress for the turn!"
        scoring = [
            ("CHECKPOINT MILESTONES", "Points awarded for reaching destination checkpoints first"),
            ("COLLECTED REWARDS", "High-value tokens and cards accumulated along the track"),
            ("SPEED BONUSES", "Bonus points awarded for earliest finish triggers")
        ]
        win_trigger = "First player to cross the finish line or highest points when track is completed wins!"

    elif archetype == "deduction":
        components = [
            ("Clue / Word Grid Cards", "Grid of face-up cards representing suspects, locations, or words"),
            ("Secret Identity Key", "Hidden card or screen revealing secret roles and hazard traps"),
            ("Team Operative Markers", "Tokens used to designate confirmed agent identities")
        ]
        setup_directive = f"Deal grid of cards face-up on table, provide secret key to clue-givers, and divide into teams."
        phases = [
            ("GIVE CLUE", "CODED TRANSMISSION", "Clue-giver provides a single word and number linking related target cards"),
            ("DISCUSS & GUESS", "SELECT TARGETS", "Team operatives discuss clues and touch cards to reveal underlying identities"),
            ("CONFIRM & PASS", "RESOLVE TURNS", "Correct guesses allow additional attempts; incorrect guesses forfeit turn")
        ]
        core_action_title = "ASSOCIATIVE DEDUCTION & HAZARD AVOIDANCE"
        core_action_rule = "Clues must strictly link conceptual meanings without spelling or phonetic hints. Avoid danger cards!"
        scoring = [
            ("REVEALED AGENTS", "Points for correctly identifying all assigned team targets"),
            ("SPEED ADVANTAGE", "Fewer turns taken to solve puzzle yields tactical tiebreaks"),
            ("AVOID HAZARDS", "Instant defeat triggered if black danger / assassin card is touched")
        ]
        win_trigger = "First team to discover all their assigned secret targets wins the match!"

    elif archetype == "rail_network":
        components = [
            ("Route Network Map", "Map depicting cities linked by color-coded railway routes"),
            ("Colored Carriage Trains", "Tokens used to claim track segments between cities"),
            ("Destination Contracts", "Secret ticket cards rewarding connections between designated hubs")
        ]
        setup_directive = f"Place map board, deal starting hand of colored train cards, and distribute destination contracts."
        phases = [
            ("COLLECT ASSETS", "DRAW ROUTE CARDS", "Draw color-matched train cards from shared market display or blind deck"),
            ("CLAIM TRACK", "DEPLOY TRAINS", "Discard matching colored cards equal to route length and claim track"),
            ("DRAW TICKETS", "EXPAND CONTRACTS", "Draw additional destination tickets to connect farther distant cities")
        ]
        core_action_title = "ROUTE LINKING & EXPONENTIAL CONNECTION SCORING"
        core_action_rule = "Connecting designated destination cities awards large positive points; uncompleted tickets deduct points at game end!"
        scoring = [
            ("TRACK LENGTH", "Instant points scaled exponentially by route distance claimed"),
            ("DESTINATION CONTRACTS", "Points awarded for successfully linking ticket city pairs"),
            ("NETWORK BONUS", "Grand bonus awarded to player with longest continuous network")
        ]
        win_trigger = "Game ends when any player's train reserve runs low; highest total points wins!"

    else:
        components = [
            ("Main Playing Board", "Central map and player territory zones"),
            ("Resource Commodities", "Tokens representing gold, materials, and production"),
            ("Action Cards & Aids", "Cards governing tactical abilities and turn options")
        ]
        setup_directive = f"Deploy board, distribute starting assets to {min_p}-{max_p} players, and determine starting player."
        phases = [
            ("STRATEGIC CHOICE", "CHOOSE PRIMARY ACTION", "Select and execute main tactical action on board or personal tableau"),
            ("EXPAND & DEVELOP", "INVEST RESOURCES", "Spend accumulated resources to construct assets or upgrade tech"),
            ("SCORE & TRANSITION", "RESOLVE OBJECTIVES", "Check milestone completion, collect income, and pass first-player token")
        ]
        core_action_title = f"{name_clean.upper()} TACTICAL ACTION ENGINE"
        core_action_rule = "Balance early resource investment against sudden end-game victory point sprints!"
        scoring = [
            ("TERRITORY & ASSETS", "Points awarded for deployed structures and board presence"),
            ("COMPLETED MILESTONES", "Bonus victory points for fulfilling objective conditions"),
            ("RESOURCE SURPLUS", "Endgame conversion of surplus gold and technology cards")
        ]
        win_trigger = "Highest score after target rounds or victory threshold reached claims victory!"

    strat_econ = "Focus heavily on economic production and engine velocity during opening turns." if weight >= 2.8 else "Establish rapid board presence and consistent scoring momentum immediately."
    strategies = [
        ("Early Game", strat_econ),
        ("Mid Game", "Block opponents from high-value choke points and capitalize on synergy combos."),
        ("Endgame", "Pivot all asset generation directly into end-game victory point sprints 2 rounds before triggers.")
    ]

    return {
        "archetype": archetype,
        "components": components,
        "setup_directive": setup_directive,
        "phases": phases,
        "core_action_title": core_action_title,
        "core_action_rule": core_action_rule,
        "scoring": scoring,
        "win_trigger": win_trigger,
        "strategies": strategies
    }

# =========================================================================
# DYNAMIC FLUID MANIM CODE GENERATOR
# =========================================================================

def generate_manim_code(game: dict, local_image_path: str, custom_instruction: str = None, user_played_games: list = None, prefer_procedural: bool = False) -> str:
    """
    Synthesize complete, crash-proof, visually stunning Python Manim code for the game.
    Dynamically themes all colors, glowing auras, and graphics to match the game's authentic box art.
    Includes custom transitions and correlations to games the user has already played.
    """
    palette = extract_game_palette(local_image_path, game)
    bgg_id = int(game["bgg_id"])
    name = sanitize_text(game["name"], 35)
    year = int(game["year_published"]) if game.get("year_published") else 2000
    players = f"{game.get('min_players', 2)}-{game.get('max_players', 4)} Players"
    playtime = f"{game.get('mfg_playtime', 45)} mins"
    weight_val = float(game.get("game_weight", 2.5) or 2.5)
    weight_desc = "Lightweight" if weight_val < 2.0 else "Medium Strategy" if weight_val < 3.2 else "Heavy Strategy"

    # Online search & AI text synthesis
    ddg_snippets = search_duckduckgo_game(name)

    reference_game_name = "Catan"
    if user_played_games:
        for pg in user_played_games:
            if pg.get("bgg_id") != bgg_id and pg.get("name"):
                reference_game_name = sanitize_text(pg["name"], 25)
                break

    zai_data = generate_custom_game_text_zai(name, ddg_snippets, reference_game=reference_game_name, game_meta=game)

    # Resolve rules first so the LLM path teaches the same authentic content as procedural.
    instructions = synthesize_game_instructions(game, ddg_snippets=ddg_snippets, zai_data=zai_data)
    rules_digest = format_rules_digest(instructions, game_name=name)

    # Curated titles already have authentic multi-chapter coverage — use the masterclass,
    # not a short LLM teaser (Wingspan and peers were shipping ~20s films).
    if bgg_id in GAME_RULES_KNOWLEDGE_BASE and not prefer_procedural:
        print(
            f"[ManimGenerator] {name} has curated rules — using procedural masterclass "
            f"(full components, turns, scoring, strategy; 3+ minutes)."
        )
        prefer_procedural = True

    # 1. Attempt LLM generation if enabled and not bypassed
    if not prefer_procedural:
        try:
            correlation_prompt = custom_instruction or ""
            if user_played_games:
                played_names = [g.get("name", "") for g in user_played_games if g.get("name")]
                if played_names:
                    correlation_prompt += f" The user has previously played: {', '.join(played_names[:3])}. Add an explicit comparison explaining how mechanics translate!"

            llm_code = llm_manager.generate_manim_code(
                game,
                local_image_path,
                correlation_prompt,
                palette=palette,
                research=ddg_snippets,
                rules_digest=rules_digest,
            )
            if llm_code:
                runtime = llm_manager.estimate_runtime(llm_code)
                if runtime < llm_manager.MIN_FILM_SECONDS:
                    print(
                        f"[ManimGenerator] LLM film too short ({runtime:.0f}s < "
                        f"{llm_manager.MIN_FILM_SECONDS}s). Falling back to procedural masterclass."
                    )
                else:
                    cfg = llm_manager.get_config()
                    model_tag = cfg.get("model_name", "vLLM Model")
                    header = f"# Generated via vLLM Hot-Swapped Model: {model_tag}\n"
                    return header + llm_code
        except Exception as e:
            print(f"[ManimGenerator] LLM synthesis skipped/failed: {e}")

    # 2. Procedural synthesis engine (full multi-chapter masterclass, ~3+ minutes)
    print(f"[ManimGenerator] Building procedural masterclass for {name}...")
    archetype = instructions["archetype"]
    components = instructions["components"]
    setup_directive = instructions["setup_directive"]
    phases = instructions["phases"]
    core_action_title = instructions["core_action_title"]
    core_action_rule = instructions["core_action_rule"]
    scoring_rules = instructions["scoring"]
    win_trigger = instructions["win_trigger"]
    strategies = instructions["strategies"]

    # Correlation comparison
    old_game_how = zai_data.get("REFERENCE_HOW") if zai_data else ""
    new_game_how = zai_data.get("THIS_HOW") if zai_data else ""
    correlation_detail = zai_data.get("EVOLUTION") if zai_data else ""

    if not old_game_how or not new_game_how:
        if archetype == "worker_placement":
            old_game_how = f"Roll dice or move along fixed tracks to collect raw resources in {reference_game_name}."
            new_game_how = f"In {name}, assign meeples to exclusive action docks to lock opponents out."
            correlation_detail = f"Evolves luck into tactical control: worker placement guarantees your action while blocking rivals!"
        elif archetype == "card_engine":
            old_game_how = f"Hold basic commodity cards in hand to pay static costs in {reference_game_name}."
            new_game_how = f"In {name}, deploy cards into a tableau that trigger cascading recurring bonuses."
            correlation_detail = f"Evolves resource hoarding into engine building where every played card powers your turns!"
        elif archetype == "tile_placement":
            old_game_how = f"Place buildings on fixed vertices and single-segment roads in {reference_game_name}."
            new_game_how = f"In {name}, draw and place modular tiles to dynamically expand shared geography."
            correlation_detail = f"Deepens spatial planning: every tile expands matching edges and scoring majorities!"
        else:
            old_game_how = f"Gather commodities, trade with rivals, and race to victory points in {reference_game_name}."
            new_game_how = f"In {name}, execute phase-based tactical actions to trigger strategic victory goals."
            correlation_detail = f"Applies the pacing and strategic tempo of classic games directly to {name}'s victory goals!"

    old_game_how_wrapped = wrap_text_manim(old_game_how, 26, 4)
    new_game_how_wrapped = wrap_text_manim(new_game_how, 26, 4)

    # Dynamic Background Elements tailored to archetype
    if archetype in ["spatial_hex", "tile_placement"]:
        bg_elements_code = f'''
        # Dynamic Fluid Background: Honeycomb hexagonal territory lattice
        bg_elements = VGroup(*[
            RegularPolygon(n=6, radius=0.85, stroke_color="{palette['primary']}", stroke_width=0.9, stroke_opacity=0.18, fill_color="{palette['card_bg']}", fill_opacity=0.03)
            .shift(np.array([x, y, 0]))
            for x, y in [(-5.4, 2.3), (-4.1, 3.0), (-2.8, 2.3), (3.1, -2.4), (4.4, -1.7), (5.7, -2.4), (-4.3, -2.5), (4.5, 2.4)]
        ])'''
    elif archetype in ["card_engine", "strategy_tableau"]:
        bg_elements_code = f'''
        # Dynamic Fluid Background: Cascading card silhouette fan
        bg_elements = VGroup(*[
            RoundedRectangle(corner_radius=0.1, height=1.6, width=1.1, stroke_color=("{palette['secondary']}" if i % 2 == 0 else "{palette['primary']}"), stroke_width=0.9, stroke_opacity=0.18, fill_color="{palette['card_bg']}", fill_opacity=0.03)
            .rotate(i * 0.2 - 0.3)
            .shift(np.array([x, y, 0]))
            for i, (x, y) in enumerate([(-5.2, 2.3), (-3.9, 2.6), (-2.6, 2.1), (3.3, -2.3), (4.5, -1.9), (5.7, -2.4)])
        ])'''
    elif archetype == "worker_placement":
        bg_elements_code = f'''
        # Dynamic Fluid Background: Action dock wireframes & worker slots
        bg_elements = VGroup(*[
            RoundedRectangle(corner_radius=0.08, height=0.7, width=1.8, stroke_color="{palette['primary']}", stroke_width=0.9, stroke_opacity=0.18, fill_color="{palette['card_bg']}", fill_opacity=0.03)
            .shift(np.array([x, y, 0]))
            for x, y in [(-5.0, 2.4), (-4.8, -2.2), (5.0, 2.2), (4.8, -2.4), (-2.5, -2.8), (2.5, 2.8)]
        ])'''
    else:
        bg_elements_code = f'''
        # Dynamic Fluid Background: Polyhedral isometric nodes & orbit lines
        bg_elements = VGroup(*[
            Square(side_length=0.85, stroke_color="{palette['secondary']}", stroke_width=0.9, stroke_opacity=0.18, fill_color="{palette['card_bg']}", fill_opacity=0.03)
            .rotate(PI / 4 + i * 0.2)
            .shift(np.array([x, y, 0]))
            for i, (x, y) in enumerate([(-5.2, -2.2), (5.2, 2.4), (-4.5, 2.5), (4.6, -2.3)])
        ])'''

    escaped_img_path = local_image_path.replace("\\", "/")

    # Build dynamic component cards code (responsive count 2 to 4)
    comp_cards_code = []
    num_comps = len(components)
    # Keep the whole row inside the safe frame (±6.0) with gutters
    comp_w = min(3.1, 10.4 / max(num_comps, 1))
    for idx, (c_name, c_sub) in enumerate(components):
        c_x = (idx - (num_comps - 1) / 2.0) * (comp_w + 0.22)
        comp_cards_code.append(
            f'comp_{idx} = self.create_component_pod("{sanitize_text(c_name)}", "{sanitize_text(c_sub)}", "{palette["primary"] if idx % 2 == 0 else palette["secondary"]}", pos=np.array([{c_x:.2f}, -0.15, 0]), width={comp_w:.2f}, height=1.7)'
        )
    comp_creation_stmt = ", ".join([f"comp_{i}" for i in range(num_comps)])

    # Build dynamic phase flow cards code (responsive count 2 to 4)
    num_phases = len(phases)
    phase_w = min(3.2, 10.2 / max(num_phases, 1))
    phase_cards_code = []
    phase_arrows_code = []
    for idx, (p_lbl, p_act, p_det) in enumerate(phases):
        p_x = (idx - (num_phases - 1) / 2.0) * (phase_w + 0.22)
        phase_color = palette['primary'] if idx == 0 else (palette['secondary'] if idx == 1 else palette['accent'])
        phase_cards_code.append(
            f'phase_{idx} = self.create_phase_card("{sanitize_text(p_lbl)}", "{sanitize_text(p_act)}", "{sanitize_text(p_det)}", "{phase_color}", pos=np.array([{p_x:.2f}, -0.35, 0]), width={phase_w:.2f}, height=2.15)'
        )
        if idx > 0:
            phase_arrows_code.append(
                f'arrow_{idx} = Arrow(start=phase_{idx-1}.get_right(), end=phase_{idx}.get_left(), buff=0.10, color="{palette["secondary"]}", stroke_width=2.5)'
            )
    phase_creation_stmt = ", ".join([f"phase_{i}" for i in range(num_phases)])
    arrow_creation_stmt = (", " + ", ".join([f"GrowArrow(arrow_{i})" for i in range(1, num_phases)])) if num_phases > 1 else ""

    # Build dynamic scoring pods code (responsive count 2 to 4)
    num_scores = len(scoring_rules)
    score_cards_code = []
    score_w = min(3.1, 10.4 / max(num_scores, 1))
    for idx, (pts, rule) in enumerate(scoring_rules):
        s_x = (idx - (num_scores - 1) / 2.0) * (score_w + 0.22)
        s_color = palette['accent'] if idx == 0 else (palette['primary'] if idx == 1 else palette['secondary'])
        score_cards_code.append(
            f'score_{idx} = self.create_scoring_pod("{sanitize_text(pts)}", "{sanitize_text(rule)}", "{s_color}", pos=np.array([{s_x:.2f}, -0.15, 0]), width={score_w:.2f}, height=1.7)'
        )
    score_creation_stmt = ", ".join([f"score_{i}" for i in range(num_scores)])

    comp_cards_block = "\n".join(["        " + line for line in comp_cards_code])
    phase_cards_block = "\n".join(["        " + line for line in phase_cards_code])
    phase_arrows_block = ("\n" + "\n".join(["        " + line for line in phase_arrows_code])) if phase_arrows_code else ""
    score_cards_block = "\n".join(["        " + line for line in score_cards_code])

    # Interactive mechanics simulation block code tailored to archetype
    if archetype == "spatial_hex":
        sim_code = f'''
        # Ground-Up Hexagonal Grid & Dynamic Settlement Placement
        hex1 = RegularPolygon(n=6, radius=0.90, stroke_color="{palette['primary']}", stroke_width=2.5, fill_color="{palette['card_bg']}", fill_opacity=0.9).shift(LEFT * 1.5 + DOWN * 0.45)
        hex2 = RegularPolygon(n=6, radius=0.90, stroke_color="{palette['secondary']}", stroke_width=2.5, fill_color="{palette['card_bg']}", fill_opacity=0.9).shift(RIGHT * 0.3 + DOWN * 0.45)
        lbl1 = Text("FOREST (6)", font_size=11, color="#f8fafc", weight=BOLD).move_to(hex1.get_center())
        lbl2 = Text("HILLS (8)", font_size=11, color="#f8fafc", weight=BOLD).move_to(hex2.get_center())

        # Rolling 2d6 Dice Animation
        die1 = Square(side_length=0.45, stroke_color="{palette['accent']}", stroke_width=1.5, fill_color="{palette['bg_dark']}", fill_opacity=0.95).shift(UP * 0.8 + LEFT * 0.4)
        die2 = Square(side_length=0.45, stroke_color="{palette['accent']}", stroke_width=1.5, fill_color="{palette['bg_dark']}", fill_opacity=0.95).shift(UP * 0.8 + RIGHT * 0.4)
        t_d1 = Text("3", font_size=16, weight=BOLD, color="#fef08a").move_to(die1.get_center())
        t_d2 = Text("5", font_size=16, weight=BOLD, color="#fef08a").move_to(die2.get_center())
        dice = VGroup(die1, t_d1, die2, t_d2)

        # Settlement Piece Token materializes on vertex
        settlement = Polygon(
            [-0.2, -0.2, 0], [0.2, -0.2, 0], [0.2, 0.1, 0], [0, 0.3, 0], [-0.2, 0.1, 0],
            color="{palette['primary']}", fill_color="{palette['primary']}", fill_opacity=1.0, stroke_width=1.5
        ).move_to(hex2.get_top() + DOWN * 0.1)
        settlement_lbl = self.fit_label("Settlement (+1 VP)", 2.6, 0.32, font_size=14, color="{palette['secondary']}", weight=BOLD).next_to(settlement, UP, buff=0.15)

        # Resource harvest particles
        res_wood = Dot(radius=0.14, color="{palette['primary']}").move_to(hex1.get_center())
        res_brick = Dot(radius=0.14, color="{palette['secondary']}").move_to(hex2.get_center())

        rule_caption = self.make_caption_bar("{sanitize_text(core_action_rule)}", "{palette['primary']}", width=8.2, max_height=1.05, y=-2.35)

        self.play(GrowFromCenter(hex1), GrowFromCenter(hex2), FadeIn(lbl1), FadeIn(lbl2), run_time=1.4, rate_func=smooth)
        self.play(FadeIn(dice, shift=DOWN*0.35), Rotate(dice, angle=TAU, about_point=dice.get_center()), run_time=0.9)
        self.play(Indicate(hex2, color="{palette['accent']}"), Flash(hex2.get_center(), color="{palette['accent']}", flash_radius=0.5))
        self.play(FadeIn(settlement, scale=1.4), FadeIn(settlement_lbl), FadeIn(rule_caption), run_time=1.6, rate_func=smooth)
        self.play(res_brick.animate.shift(RIGHT * 2.4 + UP * 0.6), res_wood.animate.shift(LEFT * 2.4 + UP * 0.6), run_time=1.2, rate_func=smooth)
        self.play(Circumscribe(settlement, color="{palette['primary']}", run_time=1.2))
        self.wait(12.0)
        self.play(FadeOut(hex1), FadeOut(hex2), FadeOut(lbl1), FadeOut(lbl2), FadeOut(die1), FadeOut(die2), FadeOut(t_d1), FadeOut(t_d2), FadeOut(settlement), FadeOut(settlement_lbl), FadeOut(res_wood), FadeOut(res_brick), FadeOut(rule_caption), run_time=1.0, rate_func=smooth)
'''
    elif archetype == "tile_placement":
        sim_code = f'''
        # Dynamic Tile Matching & Meeple Highwayman Assignment
        tile1 = Square(side_length=1.6, stroke_color="{palette['primary']}", stroke_width=2.5, fill_color="{palette['card_bg']}", fill_opacity=0.9).shift(LEFT * 1.5 + DOWN * 0.45)
        road1 = Line(tile1.get_left(), tile1.get_right(), stroke_color="{palette['secondary']}", stroke_width=4.0)
        lbl1 = Text("ROAD TILE", font_size=10, weight=BOLD, color="{palette['secondary']}").next_to(road1, UP, buff=0.1)

        tile2 = Square(side_length=1.6, stroke_color="{palette['accent']}", stroke_width=2.5, fill_color="{palette['card_bg']}", fill_opacity=0.9).shift(RIGHT * 1.5 + DOWN * 0.45)
        road2 = Line(tile2.get_left(), tile2.get_right(), stroke_color="{palette['secondary']}", stroke_width=4.0)
        lbl2 = Text("ROAD SEAM", font_size=10, weight=BOLD, color="{palette['accent']}").next_to(road2, UP, buff=0.1)

        meeple = Circle(radius=0.22, stroke_color="#ffffff", stroke_width=1.5, fill_color="{palette['accent']}", fill_opacity=1.0).move_to(tile1.get_center())
        meeple_lbl = self.fit_label("Highwayman (+1 pt/tile)", 2.8, 0.32, font_size=14, color="{palette['accent']}", weight=BOLD).next_to(meeple, UP, buff=0.18)

        rule_caption = self.make_caption_bar("{sanitize_text(core_action_rule)}", "{palette['secondary']}", width=8.2, max_height=1.05, y=-2.35)

        self.play(FadeIn(tile1, shift=RIGHT*0.3), Create(road1), FadeIn(lbl1), run_time=1.0, rate_func=smooth)
        self.play(tile2.animate.shift(LEFT * 1.4), road2.animate.shift(LEFT * 1.4), lbl2.animate.shift(LEFT * 1.4), run_time=1.1, rate_func=rush_from)
        self.play(Flash(tile2.get_left(), color="{palette['secondary']}", line_length=0.25, flash_radius=0.4))
        self.play(FadeIn(meeple, scale=1.4), FadeIn(meeple_lbl), FadeIn(rule_caption), run_time=1.4, rate_func=smooth)
        self.play(Circumscribe(meeple, color="{palette['accent']}", run_time=1.2))
        self.wait(12.0)
        self.play(FadeOut(tile1), FadeOut(tile2), FadeOut(road1), FadeOut(road2), FadeOut(lbl1), FadeOut(lbl2), FadeOut(meeple), FadeOut(meeple_lbl), FadeOut(rule_caption), run_time=1.0, rate_func=smooth)
'''
    elif archetype == "worker_placement":
        sim_code = f'''
        # Ground-Up Worker Placement & Exclusive Action Dock
        dock1 = RoundedRectangle(corner_radius=0.14, height=1.3, width=3.4, stroke_color="{palette['primary']}", stroke_width=2, fill_color="{palette['card_bg']}", fill_opacity=0.96).shift(LEFT * 2.1 + DOWN * 0.45)
        t_d1 = self.fit_label("HARVEST TERMINAL\\n(+3 Food Resources)", 2.9, 0.95, font_size=14, min_font=11, weight=BOLD, color="{palette['primary']}")
        self.seat_in_panel(t_d1, dock1, pad=0.12, left_gutter=0.0)

        dock2 = RoundedRectangle(corner_radius=0.14, height=1.3, width=3.4, stroke_color="{palette['secondary']}", stroke_width=2, fill_color="{palette['card_bg']}", fill_opacity=0.96).shift(RIGHT * 2.1 + DOWN * 0.45)
        t_d2 = self.fit_label("UPGRADE FORGE\\n(Draw Technology)", 2.9, 0.95, font_size=14, min_font=11, weight=BOLD, color="{palette['secondary']}")
        self.seat_in_panel(t_d2, dock2, pad=0.12, left_gutter=0.0)

        worker = Dot(radius=0.28, color="{palette['accent']}").move_to(LEFT * 6.2 + DOWN * 0.45)
        lock_badge = self.fit_label("LOCKED OUT", 1.8, 0.28, font_size=13, weight=BOLD, color="#f87171").next_to(dock1, UP, buff=0.1)

        rule_caption = self.make_caption_bar("{sanitize_text(core_action_rule)}", "{palette['primary']}", width=8.2, max_height=1.05, y=-2.35)

        self.play(Create(dock1), FadeIn(t_d1), Create(dock2), FadeIn(t_d2), run_time=1.3, rate_func=smooth)
        self.play(worker.animate.move_to(dock1.get_center()), run_time=0.8, rate_func=rush_into)
        self.play(FadeIn(lock_badge, shift=DOWN*0.1), FadeIn(rule_caption), run_time=1.0, rate_func=smooth)
        self.play(Wiggle(worker, run_time=1.2), Flash(dock1.get_top(), color="{palette['primary']}", line_length=0.25))
        self.wait(12.0)
        self.play(FadeOut(dock1), FadeOut(dock2), FadeOut(t_d1), FadeOut(t_d2), FadeOut(worker), FadeOut(lock_badge), FadeOut(rule_caption), run_time=1.0, rate_func=smooth)
'''
    elif archetype == "deduction":
        sim_code = f'''
        # Associative Clue Grid & Identity Reveal
        g1 = RoundedRectangle(corner_radius=0.08, height=0.85, width=2.2, stroke_color="{palette['primary']}", stroke_width=1.5, fill_color="{palette['card_bg']}", fill_opacity=0.9).shift(LEFT * 2.5 + DOWN * 0.2)
        t_g1 = Text("RIVER", font_size=11, weight=BOLD, color="#ffffff").move_to(g1.get_center())

        g2 = RoundedRectangle(corner_radius=0.08, height=0.85, width=2.2, stroke_color="{palette['primary']}", stroke_width=1.5, fill_color="{palette['card_bg']}", fill_opacity=0.9).shift(DOWN * 0.2)
        t_g2 = Text("SUBMARINE", font_size=11, weight=BOLD, color="#ffffff").move_to(g2.get_center())

        g3 = RoundedRectangle(corner_radius=0.08, height=0.85, width=2.2, stroke_color="#ef4444", stroke_width=1.5, fill_color="{palette['card_bg']}", fill_opacity=0.9).shift(RIGHT * 2.5 + DOWN * 0.2)
        t_g3 = Text("ASSASSIN", font_size=11, weight=BOLD, color="#ef4444").move_to(g3.get_center())

        clue_banner = RoundedRectangle(corner_radius=0.1, height=0.52, width=5.2, stroke_color="{palette['secondary']}", stroke_width=1.5, fill_color="{palette['bg_dark']}", fill_opacity=0.95).shift(UP * 0.8)
        clue_txt = self.fit_label("SPYMASTER CLUE: 'WATER 2'", 4.7, 0.34, font_size=15, min_font=11, weight=BOLD, color="{palette['secondary']}")
        self.seat_in_panel(clue_txt, clue_banner, pad=0.1, left_gutter=0.0)

        conduit1 = Arrow(start=clue_banner.get_bottom(), end=g1.get_top(), buff=0.1, color="{palette['secondary']}", stroke_width=2.5)
        conduit2 = Arrow(start=clue_banner.get_bottom(), end=g2.get_top(), buff=0.1, color="{palette['secondary']}", stroke_width=2.5)

        rule_caption = self.make_caption_bar("{sanitize_text(core_action_rule)}", "{palette['secondary']}", width=8.2, max_height=1.05, y=-2.35)

        self.play(LaggedStart(FadeIn(g1, shift=UP*0.2), FadeIn(t_g1), FadeIn(g2, shift=UP*0.2), FadeIn(t_g2), FadeIn(g3, shift=UP*0.2), FadeIn(t_g3), lag_ratio=0.12), run_time=1.4, rate_func=smooth)
        self.play(Create(clue_banner), FadeIn(clue_txt), GrowArrow(conduit1), GrowArrow(conduit2), run_time=1.4, rate_func=smooth)
        self.play(g1.animate.set_fill("{palette['primary']}", opacity=0.9), g2.animate.set_fill("{palette['primary']}", opacity=0.9), run_time=1.2)
        self.play(FadeIn(rule_caption), Circumscribe(g3, color="#ef4444", run_time=1.2))
        self.wait(12.0)
        self.play(FadeOut(g1), FadeOut(t_g1), FadeOut(g2), FadeOut(t_g2), FadeOut(g3), FadeOut(t_g3), FadeOut(clue_banner), FadeOut(clue_txt), FadeOut(conduit1), FadeOut(conduit2), FadeOut(rule_caption), run_time=1.0, rate_func=smooth)
'''
    else:
        # Default card_engine and tableau simulation
        sim_code = f'''
        # Ground-Up Card Drafting, Tableau Staging & Synergy Cascades
        c1 = RoundedRectangle(corner_radius=0.12, height=1.9, width=2.4, stroke_color="{palette['primary']}", stroke_width=2, fill_color="{palette['card_bg']}", fill_opacity=0.95).shift(LEFT * 1.8 + DOWN * 0.45)
        t_c1 = self.fit_label("PRODUCTION DECK\\n(Recurring Food)", 2.0, 1.5, font_size=14, min_font=11, weight=BOLD, color="{palette['primary']}")
        self.seat_in_panel(t_c1, c1, pad=0.14, left_gutter=0.0)

        c2 = RoundedRectangle(corner_radius=0.12, height=1.9, width=2.4, stroke_color="{palette['secondary']}", stroke_width=2, fill_color="{palette['card_bg']}", fill_opacity=0.95).shift(RIGHT * 1.8 + DOWN * 0.45)
        t_c2 = self.fit_label("SYNERGY ENGINE\\n(Compound VP)", 2.0, 1.5, font_size=14, min_font=11, weight=BOLD, color="{palette['secondary']}")
        self.seat_in_panel(t_c2, c2, pad=0.14, left_gutter=0.0)

        syn_arrow = Arrow(start=c1.get_right(), end=c2.get_left(), buff=0.15, color="{palette['accent']}", stroke_width=3)
        syn_lbl = Text("CHAIN COMBO", font_size=9, weight=BOLD, color="{palette['accent']}").next_to(syn_arrow, UP, buff=0.1)

        rule_caption = self.make_caption_bar("{sanitize_text(core_action_rule)}", "{palette['accent']}", width=8.2, max_height=1.05, y=-2.35)

        self.play(FadeIn(c1, shift=UP*0.25), FadeIn(t_c1), FadeIn(c2, shift=DOWN*0.25), FadeIn(t_c2), run_time=1.3, rate_func=smooth)
        self.play(GrowArrow(syn_arrow), FadeIn(syn_lbl), FadeIn(rule_caption), run_time=1.1)
        combo_dot = Dot(radius=0.08, color="{palette['accent']}").move_to(syn_arrow.get_start())
        self.play(MoveAlongPath(combo_dot, syn_arrow), run_time=0.6)
        self.remove(combo_dot)
        self.play(Circumscribe(c2, color="{palette['accent']}", run_time=1.2), Flash(c2.get_top(), color="{palette['accent']}"))
        self.wait(14.0)
        self.play(FadeOut(c1), FadeOut(t_c1), FadeOut(c2), FadeOut(t_c2), FadeOut(syn_arrow), FadeOut(syn_lbl), FadeOut(rule_caption), run_time=1.0, rate_func=smooth)
'''

    # Strategy nodes code
    s1_title, s1_body = sanitize_text(strategies[0][0]), sanitize_text(strategies[0][1])
    s2_title, s2_body = sanitize_text(strategies[1][0]), sanitize_text(strategies[1][1])
    s3_title, s3_body = sanitize_text(strategies[2][0]), sanitize_text(strategies[2][1])

    script_template = f'''"""
Dynamic In-Depth Manim Explainer & Strategy Masterclass for {name} (BGG ID: {bgg_id})
Generated automatically by Aatam Video Engine (1080p Full HD)
"""
from manim import *
import numpy as np

class GameExplainer_{bgg_id}(MovingCameraScene):
    def construct(self):
        # ----------------------------------------------------
        # AMBIENT COSMIC STAGING THEMED DIRECTLY AFTER BOX ART
        # ----------------------------------------------------
        self.camera.background_color = "{palette['bg_dark']}"
        
        # Deep cosmic ambient rings matching authentic game palette
        ambient_aura1 = Annulus(inner_radius=2.6, outer_radius=4.8, color="{palette['glow_1']}", fill_opacity=0.06).shift(UP * 0.4)
        ambient_aura2 = Annulus(inner_radius=1.1, outer_radius=2.5, color="{palette['glow_2']}", fill_opacity=0.06).shift(DOWN * 0.6)
        orbit_ring = Circle(radius=3.8, stroke_color="{palette['primary']}", stroke_width=1.2, stroke_opacity=0.18).shift(UP * 0.2)
        {bg_elements_code}
        
        # Micro constellation dust with complementary theme colors
        stars = VGroup(*[
            Dot(point=np.array([np.sin(i * 1.3) * 6.2, np.cos(i * 1.9) * 3.4, 0]), radius=0.04, color=("{palette['primary']}" if i % 2 == 0 else "{palette['secondary']}"), fill_opacity=0.45)
            for i in range(18)
        ])
        self.add(ambient_aura1, ambient_aura2, orbit_ring, bg_elements, stars)
        orbit_ring.add_updater(lambda m, dt: m.rotate(0.12 * dt))
        ambient_aura1.add_updater(lambda m, dt: m.rotate(-0.04 * dt))
        stars.add_updater(lambda m, dt: m.set_opacity(0.35 + 0.25 * abs(np.sin(self.time * 1.4))))
        
        # ----------------------------------------------------
        # SCENE 1: CINEMATIC INTRO & BOX ART (1080p HD)
        # ----------------------------------------------------
        title = Text("{name}", font_size=28, weight=BOLD, color="#f8fafc")
        if title.width > 9.2:
            title.scale_to_fit_width(9.2)
        year_badge = Text("({year})", font_size=14, color="#94a3b8").next_to(title, RIGHT, buff=0.20)
        title_row = VGroup(title, year_badge)
        if title_row.width > 12.2:
            title_row.scale_to_fit_width(12.2)
        title_row.move_to(UP * 3.15)

        underline_glow = Line(LEFT * 4.0, RIGHT * 4.0, stroke_width=5, color="{palette['primary']}", stroke_opacity=0.35).next_to(title_row, DOWN, buff=0.10)
        underline = Line(LEFT * 3.8, RIGHT * 3.8, stroke_width=2.0, color="{palette['secondary']}").move_to(underline_glow.get_center())
        
        # Living box: the cover floats, and the pieces drawn on it keep moving
        box_home = LEFT * 3.0 + DOWN * 0.35
        box_shadow = RoundedRectangle(corner_radius=0.18, height=3.85, width=3.05, fill_color="#000000", fill_opacity=0.55, stroke_width=0).move_to(box_home + DOWN * 0.12 + RIGHT * 0.1)
        box_frame = RoundedRectangle(corner_radius=0.16, height=3.75, width=2.95, stroke_color="{palette['primary']}", stroke_width=2.5, fill_color="{palette['card_bg']}", fill_opacity=0.92).move_to(box_home)
        box_glow = RoundedRectangle(corner_radius=0.22, height=3.95, width=3.15, stroke_color="{palette['primary']}", stroke_width=6, stroke_opacity=0.35).move_to(box_home)
        pulse_ring = RoundedRectangle(corner_radius=0.2, height=3.75, width=2.95, stroke_color="{palette['secondary']}", stroke_width=3, stroke_opacity=0.7).move_to(box_home)

        box_img = ImageMobject("{escaped_img_path}")
        box_img.height = 3.55
        box_img.move_to(box_home)

        # Pieces that live ON the cover face (spawned inside the frame, never past the edge)
        inner_card = RoundedRectangle(corner_radius=0.06, height=0.85, width=0.55, stroke_color="#f8fafc", stroke_width=1.2, fill_color="{palette['card_bg']}", fill_opacity=0.92).move_to(box_home + LEFT * 0.55 + UP * 0.35)
        inner_card_pip = Line(inner_card.get_top() + DOWN * 0.14, inner_card.get_bottom() + UP * 0.14, stroke_color="{palette['accent']}", stroke_width=2)
        inner_die = Square(side_length=0.38, stroke_color="#f8fafc", stroke_width=1.2, fill_color="{palette['primary']}", fill_opacity=0.95).move_to(box_home + RIGHT * 0.55 + UP * 0.55)
        die_pips = VGroup(*[Dot(radius=0.03, color="#0f172a") for _ in range(5)])
        die_pips.arrange_in_grid(rows=3, cols=2, buff=0.05)
        die_pips.move_to(inner_die.get_center())
        token_a = Circle(radius=0.14, stroke_width=1.2, stroke_color="#f8fafc", fill_color="{palette['secondary']}", fill_opacity=1).move_to(box_home + LEFT * 0.4 + DOWN * 0.85)
        token_b = Circle(radius=0.14, stroke_width=1.2, stroke_color="#f8fafc", fill_color="{palette['accent']}", fill_opacity=1).move_to(box_home + RIGHT * 0.05 + DOWN * 0.85)
        token_c = RegularPolygon(n=6, radius=0.14, stroke_width=1.2, stroke_color="#f8fafc", fill_color="{palette['primary']}", fill_opacity=1).move_to(box_home + RIGHT * 0.5 + DOWN * 0.85)
        # Sheen + sparks stay INSIDE the cover frame (never orbit outside the box)
        sheen = Rectangle(height=3.2, width=0.14, stroke_width=0, fill_color="#ffffff", fill_opacity=0.18).move_to(box_home + LEFT * 0.85)
        sparks = VGroup(*[
            Dot(radius=0.03, color="{palette['accent']}", fill_opacity=0.8).move_to(
                box_home + np.array([np.cos(i) * 1.05, np.sin(i * 1.7) * 1.35, 0])
            )
            for i in range(8)
        ])
        box_pieces = VGroup(inner_card, inner_card_pip, inner_die, die_pips, token_a, token_b, token_c, sheen, sparks)
        box_rig = Group(box_shadow, box_glow, box_frame, box_img, box_pieces)

        stat1 = self.create_badge("{players}", "{palette['primary']}")
        stat2 = self.create_badge("{playtime}", "{palette['secondary']}")
        stat3 = self.create_badge("Weight: {weight_val:.1f} / 5", "{palette['accent']}")
        stat4 = self.create_badge("{weight_desc}", "{palette['primary']}")

        stats_group = VGroup(stat1, stat2, stat3, stat4).arrange(DOWN, buff=0.18, aligned_edge=LEFT)
        stats_group.move_to(RIGHT * 3.15 + DOWN * 0.25)
        self.clamp_to_safe(stats_group)

        self.play(Write(title), FadeIn(year_badge, shift=LEFT*0.15), Create(underline_glow), Create(underline), run_time=1.4, rate_func=smooth)
        self.play(title.animate.scale(1.04), rate_func=there_and_back, run_time=0.5)
        self.play(
            FadeIn(box_shadow),
            GrowFromCenter(box_glow),
            GrowFromCenter(box_frame),
            FadeIn(box_img, scale=0.82),
            LaggedStart(
                FadeIn(inner_card, shift=DOWN*0.2),
                FadeIn(inner_card_pip),
                SpinInFromNothing(inner_die),
                FadeIn(die_pips),
                GrowFromCenter(token_a),
                GrowFromCenter(token_b),
                GrowFromCenter(token_c),
                FadeIn(sparks),
                lag_ratio=0.08,
            ),
            LaggedStart(*[FadeIn(s, shift=LEFT*0.35) for s in stats_group], lag_ratio=0.15),
            pulse_ring.animate.scale(1.28).set_stroke(opacity=0),
            run_time=2.2,
            rate_func=smooth
        )

        box_frame.add_updater(lambda m: m.move_to(box_home + UP * 0.07 * np.sin(self.time * 1.7)))
        box_img.add_updater(lambda m: m.move_to(box_frame.get_center()))
        box_shadow.add_updater(lambda m: m.move_to(box_frame.get_center() + DOWN * 0.12 + RIGHT * 0.1))
        box_glow.add_updater(lambda m: m.move_to(box_frame.get_center()).set_stroke(opacity=0.22 + 0.28 * abs(np.sin(self.time * 2.1))))
        def _tilt(m, target):
            m.rotate(target - getattr(m, "_tilt", 0.0))
            m._tilt = target
        # Subtle motion only — amplitudes stay inside the cover face
        inner_card.add_updater(lambda m: (m.move_to(box_frame.get_center() + LEFT * 0.55 + UP * (0.35 + 0.05 * np.sin(self.time * 2.4))), _tilt(m, 0.1 * np.sin(self.time * 1.6))))
        inner_card_pip.add_updater(lambda m: m.put_start_and_end_on(inner_card.get_top() + DOWN * 0.16, inner_card.get_bottom() + UP * 0.16))
        inner_die.add_updater(lambda m, dt: m.move_to(box_frame.get_center() + RIGHT * 0.55 + UP * (0.55 + 0.04 * np.sin(self.time * 3))).rotate(1.2 * dt))
        die_pips.add_updater(lambda m, dt: m.move_to(inner_die.get_center()).rotate(1.2 * dt))
        for tok, home_off, phase in (
            (token_a, LEFT * 0.4 + DOWN * 0.85, 0.0),
            (token_b, RIGHT * 0.05 + DOWN * 0.85, 0.8),
            (token_c, RIGHT * 0.5 + DOWN * 0.85, 1.6),
        ):
            tok.add_updater(lambda m, off=home_off, ph=phase: m.move_to(box_frame.get_center() + off + UP * 0.04 * np.sin(self.time * 3.2 + ph)))
        sheen.add_updater(lambda m: m.move_to(box_frame.get_center() + LEFT * 0.2 + RIGHT * (0.7 * np.sin(self.time * 1.3))).set_opacity(0.1 + 0.1 * abs(np.sin(self.time * 1.3))))
        for i, sp in enumerate(sparks):
            sp.add_updater(lambda m, k=i: m.move_to(box_frame.get_center() + np.array([np.cos(self.time * 0.8 + k) * 1.0, np.sin(self.time * 1.1 + k * 1.7) * 1.25, 0])).set_opacity(0.35 + 0.55 * abs(np.sin(self.time * 2 + k))))

        self.play(
            token_a.animate.shift(UP * 0.15),
            token_c.animate.shift(LEFT * 0.08),
            Flash(inner_die, color="{palette['accent']}", flash_radius=0.35, line_length=0.15),
            Circumscribe(box_frame, color="{palette['secondary']}", fade_out=True),
            run_time=1.6,
            rate_func=smooth,
        )
        self.wait(8.0)

        for mob in (box_frame, box_img, box_shadow, box_glow, inner_card, inner_card_pip, inner_die, die_pips, token_a, token_b, token_c, sheen, *sparks):
            mob.clear_updaters()
        self.play(
            FadeOut(box_rig),
            FadeOut(stats_group), FadeOut(year_badge), FadeOut(pulse_ring),
            underline_glow.animate.set_stroke(opacity=0.15),
            underline.animate.set_stroke(opacity=0.4),
            run_time=1.0,
            rate_func=smooth
        )

        # ----------------------------------------------------
        # SCENE 2: DYNAMIC GROUND-UP SETUP & ANATOMY (NON-STATIC)
        # ----------------------------------------------------
        setup_header = self.create_chapter_banner("CHAPTER 1: OFFICIAL COMPONENTS & BOARD SETUP", "{palette['primary']}")
        setup_header.next_to(underline, DOWN, buff=0.25)
        self.play(FadeIn(setup_header, shift=DOWN*0.2), run_time=1.2, rate_func=smooth)

{comp_cards_block}
        setup_pods = VGroup({comp_creation_stmt})

        setup_caption = self.make_caption_bar("{sanitize_text(setup_directive)}", "{palette['primary']}", width=8.2, max_height=1.05, y=-2.45)

        self.play(
            LaggedStart(*[GrowFromCenter(c) for c in setup_pods], lag_ratio=0.18),
            FadeIn(setup_caption, shift=UP*0.1),
            run_time=2.0,
            rate_func=smooth
        )
        self.play(
            Indicate(setup_pods[0], color=WHITE, scale_factor=1.04),
            LaggedStart(*[setup_pods[i].animate.shift(UP * 0.04) for i in range(len(setup_pods))], lag_ratio=0.2),
            run_time=1.1,
            rate_func=there_and_back,
        )
        # Hold long enough to read every component and the setup directive
        self.wait(18.0)
        self.play(
            FadeOut(setup_pods), FadeOut(setup_caption),
            run_time=1.0,
            rate_func=smooth
        )

        # ----------------------------------------------------
        # SCENE 2.5: HOW OLD GAME WORKS VS HOW NEW GAME WORKS
        # ----------------------------------------------------
        corr_header = self.create_chapter_banner("TACTICAL BRIDGE: FROM {reference_game_name.upper()} TO {name.upper()}", "{palette['secondary']}")
        corr_header.next_to(underline, DOWN, buff=0.25)
        self.play(ReplacementTransform(setup_header, corr_header), run_time=1.2, rate_func=smooth)

        old_card = self.create_mechanic_card(
            "{reference_game_name}",
            "OLD / REFERENCE GAME",
            "How It Works:",
            "{old_game_how_wrapped}",
            "{palette['primary']}",
            LEFT * 3.4 + DOWN * 0.35
        )
        new_card = self.create_mechanic_card(
            "{name}",
            "NEW / TARGET GAME",
            "How It Works:",
            "{new_game_how_wrapped}",
            "{palette['accent']}",
            RIGHT * 3.4 + DOWN * 0.35
        )

        bridge_arrow = Arrow(start=old_card.get_right() + LEFT * 0.1, end=new_card.get_left() + RIGHT * 0.1, buff=0.18, color="{palette['secondary']}", stroke_width=3.5)
        bridge_label = Text("EVOLVES TO", font_size=10, weight=BOLD, color="{palette['secondary']}").next_to(bridge_arrow, UP, buff=0.12)

        note_caption = self.make_caption_bar("{sanitize_text(correlation_detail)}", "{palette['secondary']}", width=8.2, max_height=1.05, y=-2.45)

        self.play(FadeIn(old_card, shift=RIGHT*0.3), run_time=1.2, rate_func=smooth)
        self.play(GrowArrow(bridge_arrow), FadeIn(bridge_label, shift=DOWN*0.08), run_time=0.8)
        bridge_pulse = Dot(radius=0.08, color="{palette['secondary']}").move_to(bridge_arrow.get_start())
        self.play(MoveAlongPath(bridge_pulse, bridge_arrow), run_time=0.7, rate_func=smooth)
        self.play(FadeOut(bridge_pulse), FadeIn(new_card, shift=LEFT*0.3), run_time=1.2, rate_func=smooth)
        self.play(FadeIn(note_caption), run_time=1.2, rate_func=smooth)
        self.play(Circumscribe(old_card, color="{palette['primary']}", run_time=1.2))
        self.wait(5.0)
        self.play(Circumscribe(new_card, color="{palette['accent']}", run_time=1.2))
        self.wait(12.0)
        self.play(
            FadeOut(old_card), FadeOut(bridge_arrow), FadeOut(bridge_label),
            FadeOut(new_card), FadeOut(note_caption),
            run_time=1.0,
            rate_func=smooth
        )

        # ----------------------------------------------------
        # SCENE 3: DYNAMIC TURN ANATOMY & SHIFTING PHASE BEACON
        # ----------------------------------------------------
        turn_header = self.create_chapter_banner("CHAPTER 2: TURN SEQUENCE & ACTIVE PHASE TRACK", "{palette['secondary']}")
        turn_header.next_to(underline, DOWN, buff=0.25)
        self.play(ReplacementTransform(corr_header, turn_header), run_time=1.2, rate_func=smooth)

{phase_cards_block}{phase_arrows_block}
        all_phase_cards = VGroup({phase_creation_stmt})

        self.play(
            LaggedStart(*[FadeIn(p, shift=UP*0.25, scale=0.92) for p in all_phase_cards], lag_ratio=0.2)
            {arrow_creation_stmt},
            run_time=1.8,
            rate_func=smooth
        )

        # Active glowing phase beacon shifting fluidly across turn stages
        beacon = Dot(radius=0.18, color="{palette['accent']}").move_to(phase_0.get_top() + UP * 0.22)
        beacon_halo = Annulus(inner_radius=0.22, outer_radius=0.38, color="{palette['accent']}", fill_opacity=0.35).move_to(beacon.get_center())
        beacon_group = VGroup(beacon, beacon_halo)
        
        self.play(FadeIn(beacon_group, scale=1.5), run_time=0.6)
        for i in range({num_phases}):
            target_phase = getattr(self, f"dummy_{{i}}", all_phase_cards[i])
            if i > 0:
                self.play(beacon_group.animate.move_to(target_phase.get_top() + UP * 0.22), run_time=0.9, rate_func=smooth)
            self.play(
                Circumscribe(target_phase, color=("{palette['primary']}" if i % 2 == 0 else "{palette['secondary']}"), run_time=1.0),
                Flash(target_phase.get_top(), color="{palette['accent']}", line_length=0.25, flash_radius=0.35)
            )
            # Pause on each phase so the viewer can read the full rule text
            self.wait(6.0)

        self.wait(8.0)
        self.play(FadeOut(all_phase_cards), FadeOut(beacon_group), {", ".join([f"FadeOut(arrow_{i})" for i in range(1, num_phases)]) if num_phases > 1 else ""}, run_time=1.0, rate_func=smooth)

        # ----------------------------------------------------
        # SCENE 4: INTERACTIVE GAMEPLAY SIMULATION (TAILORED)
        # ----------------------------------------------------
        comp_header = self.create_chapter_banner("CHAPTER 3: {sanitize_text(core_action_title)}", "{palette['accent']}")
        comp_header.next_to(underline, DOWN, buff=0.25)
        self.play(ReplacementTransform(turn_header, comp_header), run_time=1.2, rate_func=smooth)
{sim_code}

        # ----------------------------------------------------
        # SCENE 5: SCORING TALLY & VICTORY SPRINT ENGINE
        # ----------------------------------------------------
        vic_header = self.create_chapter_banner("CHAPTER 4: SCORING ENGINE & VICTORY SPRINT", "{palette['accent']}")
        vic_header.next_to(underline, DOWN, buff=0.25)
        self.play(ReplacementTransform(comp_header, vic_header), run_time=1.2, rate_func=smooth)

{score_cards_block}
        score_pods = VGroup({score_creation_stmt})

        # Victory caption stays inside frame; trophy sits on the bar, not past the edge
        win_caption = self.make_caption_bar("VICTORY: {sanitize_text(win_trigger)}", "{palette['accent']}", width=7.6, max_height=1.05, y=-2.4, weight=BOLD)
        trophy_star = Star(n=5, outer_radius=0.28, inner_radius=0.13, color="{palette['accent']}", fill_opacity=1.0)
        trophy_star.next_to(win_caption, RIGHT, buff=0.14)
        self.clamp_to_safe(trophy_star)
        sprint = Line(LEFT * 3.0, RIGHT * 3.0, stroke_width=5, color="{palette['accent']}").next_to(score_pods, DOWN, buff=0.14)
        self.clamp_to_safe(sprint)
        sprint_tip = Dot(radius=0.08, color="#fef08a").move_to(sprint.get_start())

        self.play(LaggedStart(*[GrowFromEdge(s, DOWN) for s in score_pods], lag_ratio=0.16), run_time=1.6, rate_func=smooth)
        self.play(Create(sprint), MoveAlongPath(sprint_tip, sprint), run_time=1.1, rate_func=smooth)
        self.play(FadeIn(win_caption), SpinInFromNothing(trophy_star), FadeOut(sprint_tip), run_time=1.3, rate_func=smooth)
        self.play(Flash(trophy_star.get_center(), color="{palette['accent']}", line_length=0.28, flash_radius=0.4), Rotate(trophy_star, angle=TAU * 0.2), run_time=1.0)
        self.wait(16.0)
        self.play(FadeOut(score_pods), FadeOut(sprint), FadeOut(win_caption), FadeOut(trophy_star), run_time=1.0, rate_func=smooth)

        # ----------------------------------------------------
        # SCENE 6: MASTERCLASS WINNING STRATEGIES & PRO TIPS
        # ----------------------------------------------------
        strat_header = self.create_chapter_banner("CHAPTER 5: MASTER STRATEGY MATRIX & PRO TIPS", "{palette['primary']}")
        strat_header.next_to(underline, DOWN, buff=0.25)
        self.play(ReplacementTransform(vic_header, strat_header), run_time=1.2, rate_func=smooth)

        s_node1 = self.create_tactical_node("STAGE 1: OPENING", "{s1_title}", "{s1_body}", "{palette['accent']}", pos=LEFT * 3.35 + DOWN * 0.35, width=2.7, height=2.05)
        s_node2 = self.create_tactical_node("STAGE 2: MIDGAME", "{s2_title}", "{s2_body}", "{palette['primary']}", pos=DOWN * 0.35, width=2.7, height=2.05)
        s_node3 = self.create_tactical_node("STAGE 3: ENDGAME", "{s3_title}", "{s3_body}", "{palette['secondary']}", pos=RIGHT * 3.35 + DOWN * 0.35, width=2.7, height=2.05)

        conduit1 = Arrow(start=s_node1.get_right(), end=s_node2.get_left(), buff=0.14, color="{palette['primary']}", stroke_width=3)
        conduit2 = Arrow(start=s_node2.get_right(), end=s_node3.get_left(), buff=0.14, color="{palette['primary']}", stroke_width=3)

        self.play(FadeIn(s_node1, shift=RIGHT*0.2), run_time=0.7, rate_func=smooth)
        self.play(GrowArrow(conduit1), run_time=0.45)
        strat_pulse = Dot(radius=0.08, color="{palette['accent']}").move_to(conduit1.get_start())
        self.play(MoveAlongPath(strat_pulse, conduit1), FadeIn(s_node2, shift=UP*0.15), run_time=0.7)
        self.play(GrowArrow(conduit2), run_time=0.4)
        self.play(MoveAlongPath(strat_pulse, conduit2), FadeIn(s_node3, shift=LEFT*0.15), run_time=0.7)
        self.play(FadeOut(strat_pulse), run_time=0.3)
        self.play(Indicate(s_node1, color=WHITE, scale_factor=1.05, run_time=0.7))
        self.wait(8.0)
        self.play(Indicate(s_node2, color=WHITE, scale_factor=1.05, run_time=0.7))
        self.wait(8.0)
        self.play(Indicate(s_node3, color=WHITE, scale_factor=1.05, run_time=0.7))
        self.wait(12.0)
        self.play(FadeOut(s_node1), FadeOut(s_node2), FadeOut(s_node3), FadeOut(conduit1), FadeOut(conduit2), run_time=1.0, rate_func=smooth)

        # ----------------------------------------------------
        # SCENE 7: SUMMARY & OUTRO
        # ----------------------------------------------------
        recap_title = self.fit_label("Master {name}", 11.5, 0.7, font_size=32, weight=BOLD, color="{palette['primary']}")
        recap_sub = self.fit_label("Track plays, explore guides, and discover winning strategies on Aatam", 11.0, 0.4, font_size=16, color="#94a3b8")
        recap_block = VGroup(recap_title, recap_sub).arrange(DOWN, buff=0.28).shift(UP * 0.15)

        self.play(ReplacementTransform(strat_header, recap_title), FadeIn(recap_sub, shift=UP*0.2), run_time=1.5, rate_func=smooth)
        self.play(recap_block.animate.scale(1.04), rate_func=there_and_back, run_time=0.8)
        self.wait(12.0)
        self.play(FadeOut(recap_title), FadeOut(recap_sub), FadeOut(title), FadeOut(underline), FadeOut(underline_glow), run_time=1.0, rate_func=smooth)

    # --------------------------------------------------------
    # GRAPHIC GENERATION HELPERS — zero overflow, fixed frames
    # --------------------------------------------------------
    SAFE_X = 6.1
    SAFE_Y = 3.25

    def _wrap_block(self, paragraphs, max_width, font_size, kwargs):
        style = {{k: kwargs[k] for k in ("weight", "font", "line_spacing") if k in kwargs}}
        lines = []
        for para in paragraphs:
            words = para.split()
            if not words:
                continue
            current = words[0]
            for word in words[1:]:
                trial = current + " " + word
                if Text(trial, font_size=font_size, **style).width <= max_width:
                    current = trial
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return "\\n".join(lines) if lines else ""

    def fit_label(self, text, max_width, max_height=None, font_size=18, min_font=11, **kwargs):
        """Word-wrap and shrink until the label sits strictly inside max_width x max_height."""
        raw = str(text).replace("\\\\n", "\\n")
        paragraphs = [p.strip() for p in raw.split("\\n")] or [""]
        size = int(font_size)
        floor = int(min_font)
        label = None
        while size >= floor:
            wrapped = self._wrap_block(paragraphs, max_width, size, kwargs)
            label = Text(wrapped if wrapped else " ", font_size=size, **kwargs)
            too_wide = label.width > max_width + 0.02
            too_tall = max_height is not None and label.height > max_height + 0.02
            if not too_wide and not too_tall:
                return label
            size -= 1
        wrapped = self._wrap_block(paragraphs, max_width, floor, kwargs)
        label = Text(wrapped if wrapped else " ", font_size=floor, **kwargs)
        self.contain(label, max_width, max_height if max_height is not None else label.height + 1)
        return label

    def contain(self, mob, max_width, max_height):
        if max_width and mob.width > max_width and mob.width > 0:
            mob.scale_to_fit_width(max_width)
        if max_height and mob.height > max_height and mob.height > 0:
            mob.scale_to_fit_height(max_height)
        if max_width and mob.width > max_width and mob.width > 0:
            mob.scale_to_fit_width(max_width)
        return mob

    def seat_in_panel(self, content, box, pad=0.16, left_gutter=0.18):
        """Scale + center content so every pixel stays inside the panel face."""
        usable_w = max(0.12, box.width - 2 * pad - left_gutter)
        usable_h = max(0.12, box.height - 2 * pad)
        self.contain(content, usable_w, usable_h)
        content.move_to(box.get_center() + RIGHT * (left_gutter * 0.45))
        return content

    def clamp_to_safe(self, mob):
        """Nudge a mobject so its bounding box stays inside the 16:9 safe area."""
        r = mob.get_right()[0]
        l = mob.get_left()[0]
        t = mob.get_top()[1]
        b = mob.get_bottom()[1]
        dx = 0.0
        dy = 0.0
        if r > self.SAFE_X:
            dx -= (r - self.SAFE_X)
        if l < -self.SAFE_X:
            dx += (-self.SAFE_X - l)
        if t > self.SAFE_Y:
            dy -= (t - self.SAFE_Y)
        if b < -self.SAFE_Y:
            dy += (-self.SAFE_Y - b)
        if dx or dy:
            mob.shift(RIGHT * dx + UP * dy)
        return mob

    def make_panel(self, width, height, color_hex, pos):
        shadow = RoundedRectangle(corner_radius=0.16, height=height, width=width, stroke_width=0, fill_color="#000000", fill_opacity=0.38).move_to(pos + np.array([0.05, -0.06, 0]))
        glow = RoundedRectangle(corner_radius=0.18, height=height + 0.08, width=width + 0.08, stroke_color=color_hex, stroke_width=3.0, stroke_opacity=0.22).move_to(pos)
        box = RoundedRectangle(corner_radius=0.14, height=height, width=width, stroke_color=color_hex, stroke_width=1.8, fill_color="{palette['card_bg']}", fill_opacity=0.97).move_to(pos)
        sheen = RoundedRectangle(corner_radius=0.1, height=max(0.18, height * 0.38), width=max(0.35, width - 0.28), stroke_width=0, fill_color="#ffffff", fill_opacity=0.04).move_to(box.get_top() + DOWN * (height * 0.22))
        accent = RoundedRectangle(corner_radius=0.03, height=max(0.18, height - 0.42), width=0.06, stroke_width=0, fill_color=color_hex, fill_opacity=0.95)
        accent.move_to(box.get_center()).align_to(box, LEFT).shift(RIGHT * 0.14)
        return VGroup(shadow, glow, box, sheen, accent)

    def make_caption_bar(self, text, color_hex, width=8.2, max_height=1.1, y=-2.45, weight=NORMAL):
        """Bottom rule/setup bar — text is guaranteed inside the rounded rect."""
        inner_w = width - 0.5
        inner_h = max_height - 0.3
        txt = self.fit_label(text, inner_w, inner_h, font_size=15, min_font=11, color="#fef08a", weight=weight, line_spacing=0.85)
        h = float(np.clip(txt.height + 0.3, 0.7, max_height))
        box = RoundedRectangle(
            corner_radius=0.14, height=h, width=width,
            stroke_color=color_hex, stroke_width=1.5,
            fill_color="{palette['card_bg']}", fill_opacity=0.96,
        ).move_to(UP * y)
        self.seat_in_panel(txt, box, pad=0.14, left_gutter=0.06)
        return self.clamp_to_safe(VGroup(box, txt))

    def create_chapter_banner(self, text, color_hex):
        t = self.fit_label(text, 10.6, 0.42, font_size=18, min_font=12, weight=BOLD, color=color_hex)
        w = float(np.clip(t.width + 0.9, 6.8, 11.6))
        h = 0.72
        panel = self.make_panel(w, h, color_hex, ORIGIN)
        self.seat_in_panel(t, panel[2], pad=0.12, left_gutter=0.14)
        return self.clamp_to_safe(VGroup(panel, t))

    def create_badge(self, text, color_hex):
        t = self.fit_label(text, 2.55, 0.32, font_size=15, min_font=11, weight=BOLD, color=color_hex)
        w = float(np.clip(t.width + 0.48, 2.4, 3.15))
        h = 0.58
        panel = self.make_panel(w, h, color_hex, ORIGIN)
        self.seat_in_panel(t, panel[2], pad=0.1, left_gutter=0.12)
        return VGroup(panel, t)

    def create_component_pod(self, title, subtitle, color_hex, pos, width=2.4, height=1.7):
        panel = self.make_panel(width, height, color_hex, pos)
        inner_w = width - 0.55
        t = self.fit_label(title, inner_w, height * 0.28, font_size=16, min_font=11, weight=BOLD, color="#f8fafc")
        s = self.fit_label(subtitle, inner_w, height * 0.48, font_size=13, min_font=11, color="#cbd5e1", line_spacing=0.85)
        content = VGroup(t, s).arrange(DOWN, buff=0.1, center=True)
        self.seat_in_panel(content, panel[2], pad=0.14, left_gutter=0.18)
        return self.clamp_to_safe(VGroup(panel, content))

    def create_phase_card(self, phase_num, title, desc, color_hex, pos, width=2.6, height=2.15):
        panel = self.make_panel(width, height, color_hex, pos)
        inner_w = width - 0.55
        num = self.fit_label(phase_num, inner_w, 0.28, font_size=12, min_font=11, weight=BOLD, color=color_hex)
        t = self.fit_label(title, inner_w, 0.34, font_size=14, min_font=11, weight=BOLD, color="#f8fafc")
        d = self.fit_label(desc, inner_w, height * 0.48, font_size=13, min_font=11, color="#e2e8f0", line_spacing=0.85)
        content = VGroup(num, t, d).arrange(DOWN, buff=0.08, center=True)
        self.seat_in_panel(content, panel[2], pad=0.14, left_gutter=0.18)
        return self.clamp_to_safe(VGroup(panel, content))

    def create_scoring_pod(self, points_txt, rule_txt, color_hex, pos, width=2.5, height=1.7):
        panel = self.make_panel(width, height, color_hex, pos)
        inner_w = width - 0.55
        pts = self.fit_label(points_txt, inner_w, height * 0.28, font_size=15, min_font=11, weight=BOLD, color=color_hex)
        rule = self.fit_label(rule_txt, inner_w, height * 0.48, font_size=13, min_font=11, color="#e2e8f0", line_spacing=0.85)
        content = VGroup(pts, rule).arrange(DOWN, buff=0.1, center=True)
        self.seat_in_panel(content, panel[2], pad=0.14, left_gutter=0.18)
        return self.clamp_to_safe(VGroup(panel, content))

    def create_tactical_node(self, stage_txt, title, desc, color_hex, pos, width=2.6, height=2.05):
        panel = self.make_panel(width, height, color_hex, pos)
        inner_w = width - 0.55
        stg = self.fit_label(stage_txt, inner_w, 0.26, font_size=12, min_font=11, weight=BOLD, color=color_hex)
        t = self.fit_label(title, inner_w, 0.32, font_size=14, min_font=11, weight=BOLD, color="#f8fafc")
        d = self.fit_label(desc, inner_w, height * 0.46, font_size=12, min_font=11, color="#e2e8f0", line_spacing=0.85)
        content = VGroup(stg, t, d).arrange(DOWN, buff=0.08, center=True)
        self.seat_in_panel(content, panel[2], pad=0.14, left_gutter=0.18)
        return self.clamp_to_safe(VGroup(panel, content))

    def create_mechanic_card(self, game_name, badge_txt, headline, desc_lines, color_hex, pos):
        w, h_box = 3.45, 2.55
        panel = self.make_panel(w, h_box, color_hex, pos)
        inner_w = w - 0.55
        badge = self.fit_label(badge_txt, inner_w - 0.25, 0.22, font_size=11, min_font=11, weight=BOLD, color=color_hex)
        badge_box = RoundedRectangle(
            corner_radius=0.08,
            height=min(0.36, badge.height + 0.14),
            width=min(inner_w - 0.1, badge.width + 0.28),
            stroke_color=color_hex, stroke_width=1.2,
            fill_color=color_hex, fill_opacity=0.22,
        )
        self.seat_in_panel(badge, badge_box, pad=0.06, left_gutter=0.0)
        badge_pill = VGroup(badge_box, badge)
        t = self.fit_label(game_name, inner_w, 0.34, font_size=16, min_font=11, weight=BOLD, color="#ffffff")
        div = Line(LEFT * (inner_w / 2), RIGHT * (inner_w / 2), stroke_color=color_hex, stroke_width=1.0, stroke_opacity=0.45)
        h = self.fit_label(headline, inner_w, 0.28, font_size=13, min_font=11, weight=BOLD, color=color_hex)
        d = self.fit_label(desc_lines, inner_w, 1.0, font_size=12, min_font=11, color="#e2e8f0", line_spacing=0.85)
        content = VGroup(badge_pill, t, div, h, d).arrange(DOWN, buff=0.08, center=True)
        self.seat_in_panel(content, panel[2], pad=0.14, left_gutter=0.16)
        return self.clamp_to_safe(VGroup(panel, content))
'''
    return script_template


def render_game_video(bgg_id: int, quality: str = "h", overwrite: bool = False, user_played_games: list = None, prefer_procedural: bool = False) -> str:
    """
    Renders the explainer video for the game in 1080p Full HD.
    quality: 'h' (1080p, Full HD), 'm' (720p, high def), 'l' (480p, fast)
    """
    target_mp4 = os.path.join(VIDEOS_DIR, f"{bgg_id}.mp4")
    if os.path.exists(target_mp4) and os.path.getsize(target_mp4) > 1000 and not overwrite:
        print(f"Video already rendered for {bgg_id} at {target_mp4}")
        return target_mp4

    game = get_game_data(bgg_id)
    if not game:
        raise ValueError(f"Game with BGG ID {bgg_id} not found in database.")

    # 1. Download image
    local_image = download_and_prepare_image(bgg_id, game.get("image_path", ""))

    # 2. Generate Manim code
    code = generate_manim_code(game, local_image, user_played_games=user_played_games, prefer_procedural=prefer_procedural)
    script_path = os.path.join(SCRIPTS_DIR, f"explainer_{bgg_id}.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(code)

    # 3. Render with Manim at specified resolution (defaults to 1080p 'h')
    venv_manim = os.path.join(PROJECT_DIR, ".venv", "bin", "manim")
    scene_name = f"GameExplainer_{bgg_id}"
    
    # -qh is 1080p60. Pin the frame so a model-written scene cannot drop to 480p.
    res_flag = ["-r", "1920,1080", "--fps", "30"] if quality == "h" else ["-r", "1280,720", "--fps", "30"] if quality == "m" else ["-r", "854,480", "--fps", "15"]
    cmd = [
        venv_manim,
        f"-q{quality}",
        *res_flag,
        "--media_dir", os.path.join(PROJECT_DIR, "media"),
        "-o", f"{bgg_id}.mp4",
        script_path,
        scene_name
    ]
    print(f"Rendering Manim video for '{game['name']}' (ID: {bgg_id}) at quality {quality}...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Locate output
    quality_subfolder = "1080p60" if quality == "h" else "720p30" if quality == "m" else "480p15"
    rendered_file = os.path.join(PROJECT_DIR, "media", "videos", f"explainer_{bgg_id}", quality_subfolder, f"{bgg_id}.mp4")
    
    if os.path.exists(rendered_file):
        import shutil
        shutil.copyfile(rendered_file, target_mp4)
        print(f"Successfully rendered video to {target_mp4} ({os.path.getsize(target_mp4)} bytes)")
        return target_mp4
    else:
        found = False
        media_videos = os.path.join(PROJECT_DIR, "media", "videos", f"explainer_{bgg_id}")
        if os.path.exists(media_videos):
            for root, dirs, files in os.walk(media_videos):
                for f in files:
                    if f.endswith(".mp4") and "partial" not in root:
                        import shutil
                        shutil.copyfile(os.path.join(root, f), target_mp4)
                        found = True
                        break
        if found:
            return target_mp4

        print("Manim stdout:", res.stdout[-800:])
        print("Manim stderr:", res.stderr[-800:])
        raise RuntimeError(f"Manim failed to render video: {res.stderr}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, default=13, help="BGG ID to render (default: 13 Catan)")
    parser.add_argument("--quality", type=str, default="h", help="Quality: h (1080p Full HD), m (720p), l (480p)")
    args = parser.parse_args()
    render_game_video(args.id, quality=args.quality, overwrite=True)
