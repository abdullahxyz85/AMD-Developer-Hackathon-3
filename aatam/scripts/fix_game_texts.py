#!/usr/bin/env python3
"""
Restore readable About / How to Play / Components / Winning Strategies text.

The Melandra games.csv pipeline left Description as stemmed bag-of-words, and
HowToPlay was a one-size-fits-all template. This script:

1. Restores Description from raw_data/database.sqlite (real BGG prose)
2. Synthesizes a short readable About for games still missing real text
3. Rebuilds Components / HowToPlay / WinningStrategies from mechanics + description
4. Writes processed_data/bgg_master_dataset.csv
5. Rebuilds data/aatam_custom_db while preserving users / sessions / submissions
"""

from __future__ import annotations

import html
import os
import re
import shutil
import sqlite3
import sys
import time

import pandas as pd

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CSV_PATH = os.path.join(PROJECT_DIR, "processed_data", "bgg_master_dataset.csv")
RAW_SQLITE = os.path.join(PROJECT_DIR, "raw_data", "database.sqlite")
CUSTOM_DB_DIR = os.path.join(PROJECT_DIR, "data", "aatam_custom_db")
USER_RATINGS_CSV = os.path.join(PROJECT_DIR, "raw_data", "user_ratings.csv")

sys.path.insert(0, PROJECT_DIR)


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def clean_bgg_description(raw: str) -> str:
    if not raw or not isinstance(raw, str):
        return ""
    text = html.unescape(raw)
    text = text.replace("&#10;", "\n").replace("&#13;", "\n")
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def looks_stemmed(text: str) -> bool:
    if not text or not str(text).strip():
        return True
    t = str(text).strip()
    if t[:1].islower() and "." not in t[:350] and "," not in t[:350]:
        return True
    # Very few function words relative to length → bag of stems
    words = re.findall(r"[a-zA-Z']+", t[:500].lower())
    if len(words) >= 25:
        function = sum(1 for w in words if w in {"the", "a", "an", "of", "to", "and", "in", "on", "for", "with", "is", "are", "you", "your"})
        if function / len(words) < 0.04:
            return True
    return False


def first_sentences(text: str, max_chars: int = 520) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for p in parts:
        if not p:
            continue
        trial = (" ".join(out + [p])).strip()
        if out and len(trial) > max_chars:
            break
        out.append(p)
        if len(trial) >= max_chars * 0.7:
            break
    return " ".join(out).strip()


def split_list(val: str) -> list[str]:
    if not val or str(val).lower() == "nan":
        return []
    return [x.strip() for x in str(val).split(";") if x.strip()]


def synthesize_about(name: str, year, min_p, max_p, playtime, weight, mechanics, themes, categories) -> str:
    mechs = split_list(mechanics)[:4]
    themes_l = split_list(themes)[:3]
    cats = split_list(categories)[:3]
    mech_bit = ", ".join(mechs) if mechs else "classic tabletop actions"
    theme_bit = ", ".join(themes_l) if themes_l else (", ".join(cats) if cats else "tabletop competition")
    try:
        year_s = str(int(year)) if year and int(year) > 0 else "an unknown year"
    except Exception:
        year_s = "an unknown year"
    try:
        w = float(weight or 2.5)
    except Exception:
        w = 2.5
    weight_label = "light" if w < 2.0 else "medium-weight" if w < 3.2 else "heavy"
    try:
        lo, hi = int(min_p or 2), int(max_p or 4)
    except Exception:
        lo, hi = 2, 4
    try:
        mins = int(playtime or 45)
    except Exception:
        mins = 45
    return (
        f"{name} ({year_s}) is a {weight_label} board game for {lo}-{hi} players, "
        f"usually lasting about {mins} minutes. "
        f"It leans on {mech_bit}, set against a {theme_bit} backdrop. "
        f"Players take turns using those systems to build an advantage and chase victory points "
        f"(or the scenario's win condition)."
    )


def build_components(mechanics: str, description: str) -> str:
    m = (mechanics or "").lower()
    d = (description or "").lower()
    parts = []
    if any(k in m or k in d for k in ("dice", "die rolling", "roll")):
        parts.append("Dice")
    if any(k in m or k in d for k in ("card", "deck", "draft", "hand management")):
        parts.append("Cards / decks")
    if any(k in m or k in d for k in ("tile", "hex", "modular board", "map addition")):
        parts.append("Map / tiles")
    if any(k in m or k in d for k in ("worker", "placement", "meeple", "pawn")):
        parts.append("Workers / meeples")
    if any(k in m or k in d for k in ("token", "resource", "cube", "goods")):
        parts.append("Resource tokens")
    if not parts:
        parts.append("Board and player pieces")
    parts.extend(["Score track / VP markers", "Rulebook and player aids"])
    # de-dupe preserve order
    seen = set()
    out = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return "; ".join(out)


def build_how_to_play(name: str, description: str, mechanics: str, min_p, max_p, playtime, weight) -> str:
    mechs = split_list(mechanics)[:4]
    mech_clause = ", ".join(mechs) if mechs else "the listed action systems"
    overview = first_sentences(description, 420)
    if not overview or looks_stemmed(overview):
        overview = (
            f"In {name}, players use {mech_clause} across a shared table to gather advantages "
            f"and push toward the published win condition."
        )
    try:
        lo, hi = int(min_p or 2), int(max_p or 4)
    except Exception:
        lo, hi = 2, 4
    try:
        mins = int(playtime or 45)
    except Exception:
        mins = 45
    try:
        w = float(weight or 2.5)
    except Exception:
        w = 2.5
    complexity = "keep the first game simple" if w < 2.5 else "expect a teaching round before it clicks" if w < 3.5 else "plan on a patient teach"

    win_hint = "race to the stated victory-point threshold or scenario objective"
    low = (description or "").lower()
    if "cooperat" in low or "co-op" in low:
        win_hint = "win or lose together against the game's threat track / scenario"
    elif "eliminate" in low or "last player" in low:
        win_hint = "survive while rivals are eliminated, or be the last player standing"
    elif "deduction" in (mechanics or "").lower() or "deduction" in low or "hidden role" in low:
        win_hint = "correctly identify (or deceive) the hidden information before time runs out"

    return (
        f"About the session\n"
        f"{name} plays for {lo}-{hi} players in about {mins} minutes — {complexity}.\n\n"
        f"What you're doing\n"
        f"{overview}\n\n"
        f"Turn flow\n"
        f"On your turn, resolve actions through {mech_clause}. "
        f"Respect the game's placement limits, hand limits, and timing rules printed on the player aids.\n\n"
        f"How you win\n"
        f"Typically you {win_hint}. Check the end-game trigger in the rulebook before the final round."
    )


def build_strategies(name: str, mechanics: str, themes: str, weight, description: str) -> str:
    mechs = split_list(mechanics)[:3]
    theme = (split_list(themes)[:1] or ["the open board"])[0]
    try:
        w = float(weight or 2.5)
    except Exception:
        w = 2.5
    early = (
        "Build an engine or income lead before chasing flashy points"
        if w >= 2.8
        else "Claim board presence and a steady scoring route early"
    )
    mid_focus = ", ".join(mechs) if mechs else "the core action cycle"
    coop = "cooperat" in (description or "").lower() or "co-op" in (description or "").lower()
    if coop:
        return (
            f"• Early: Assign roles clearly and clear the immediate threat before personal side goals.\n"
            f"• Mid: Use {mid_focus} to keep the shared crisis track under control; talk before locking turns.\n"
            f"• Late: Spend leftover resources on the scenario win condition — don't gold-plate side quests."
        )
    return (
        f"• Early: {early}; in {name}, empty moves cost more later than they look.\n"
        f"• Mid: Lean into {mid_focus} and contest the {theme} spaces rivals clearly need.\n"
        f"• Late: Convert leftover resources into end-game points two rounds before the trigger — "
        f"don't leave VP on the table."
    )


def restore_and_rewrite() -> pd.DataFrame:
    log(f"Reading {CSV_PATH}...")
    t0 = time.time()
    df = pd.read_csv(CSV_PATH, low_memory=False)
    log(f"Loaded {len(df):,} rows in {time.time() - t0:.1f}s")

    log(f"Loading BGG descriptions from {RAW_SQLITE}...")
    con = sqlite3.connect(RAW_SQLITE)
    raw = pd.read_sql_query(
        'SELECT CAST("game.id" AS INTEGER) AS bgg_id, "details.description" AS raw_description '
        "FROM BoardGames",
        con,
    )
    con.close()
    raw_map = {
        int(r.bgg_id): clean_bgg_description(r.raw_description)
        for r in raw.itertuples(index=False)
        if r.raw_description
    }
    log(f"Raw descriptions available for {len(raw_map):,} games")

    restored = 0
    synthesized = 0
    kept = 0
    new_desc = []
    new_comp = []
    new_how = []
    new_strat = []

    for row in df.itertuples(index=False):
        bgg_id = int(row.BGGId)
        name = str(row.Name) if pd.notna(row.Name) else "This board game"
        current = "" if pd.isna(row.Description) else str(row.Description)
        raw_desc = raw_map.get(bgg_id, "")

        if raw_desc:
            desc = raw_desc
            restored += 1
        elif not looks_stemmed(current):
            desc = current.strip()
            kept += 1
        else:
            desc = synthesize_about(
                name,
                getattr(row, "YearPublished", None),
                getattr(row, "MinPlayers", 2),
                getattr(row, "MaxPlayers", 4),
                getattr(row, "MfgPlaytime", 45),
                getattr(row, "GameWeight", 2.5),
                getattr(row, "Mechanics", ""),
                getattr(row, "Themes", ""),
                getattr(row, "Categories", ""),
            )
            synthesized += 1

        mechanics = "" if pd.isna(getattr(row, "Mechanics", "")) else str(row.Mechanics)
        themes = "" if pd.isna(getattr(row, "Themes", "")) else str(row.Themes)

        new_desc.append(desc)
        new_comp.append(build_components(mechanics, desc))
        new_how.append(
            build_how_to_play(
                name,
                desc,
                mechanics,
                getattr(row, "MinPlayers", 2),
                getattr(row, "MaxPlayers", 4),
                getattr(row, "MfgPlaytime", 45),
                getattr(row, "GameWeight", 2.5),
            )
        )
        new_strat.append(
            build_strategies(name, mechanics, themes, getattr(row, "GameWeight", 2.5), desc)
        )

    df["Description"] = new_desc
    # Ensure enrichment columns sit beside Description
    for col in ("Components", "HowToPlay", "WinningStrategies"):
        if col in df.columns:
            df.drop(columns=[col], inplace=True)
    desc_idx = df.columns.get_loc("Description")
    df.insert(desc_idx + 1, "Components", new_comp)
    df.insert(desc_idx + 2, "HowToPlay", new_how)
    df.insert(desc_idx + 3, "WinningStrategies", new_strat)

    log(
        f"Descriptions — restored from BGG: {restored:,}, kept readable: {kept:,}, "
        f"synthesized fallbacks: {synthesized:,}"
    )
    log(f"Writing {CSV_PATH}...")
    t1 = time.time()
    df.to_csv(CSV_PATH, index=False)
    log(f"CSV written in {time.time() - t1:.1f}s")
    return df


def rebuild_custom_db() -> None:
    preserve = ["users_shelf.json", "sessions.json", "submissions.json"]
    backups = {}
    os.makedirs(CUSTOM_DB_DIR, exist_ok=True)
    for name in preserve:
        path = os.path.join(CUSTOM_DB_DIR, name)
        if os.path.exists(path):
            bak = path + ".bak_fix"
            shutil.copy2(path, bak)
            backups[name] = bak
            log(f"Preserved {name}")

    from backend.aatam_db import AatamDB

    db = AatamDB(CUSTOM_DB_DIR)
    db.build_from_csv(CSV_PATH, USER_RATINGS_CSV if os.path.exists(USER_RATINGS_CSV) else None)

    for name, bak in backups.items():
        dest = os.path.join(CUSTOM_DB_DIR, name)
        shutil.copy2(bak, dest)
        os.remove(bak)
        log(f"Restored {name}")

    # Reload so in-process state matches disk if this module is reused
    db.load()
    log(f"Custom DB rebuilt with {len(db.offset_index):,} games")


def main() -> None:
    restore_and_rewrite()
    rebuild_custom_db()
    # Spot-check a few titles
    from backend.aatam_db import AatamDB

    db = AatamDB(CUSTOM_DB_DIR)
    for gid in (13, 174430, 167791, 30549):
        g = db.find_one(gid)
        if not g:
            log(f"MISSING {gid}")
            continue
        log(f"OK {gid} {g['name']}")
        log(f"  about: {g['description'][:140].replace(chr(10), ' ')}...")
        log(f"  how:   {g['how_to_play'][:140].replace(chr(10), ' | ')}...")


if __name__ == "__main__":
    main()
