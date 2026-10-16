import os
import math
from typing import List, Dict, Any, Optional
from .aatam_db import aatam_db

def get_user_profile(username: str) -> Dict[str, Any]:
    """Calculate deep taste analytics for a given user using AatamDB custom engine."""
    shelf_data = aatam_db.get_user_shelf(username)
    plays = shelf_data.get("plays", [])
    user_info = shelf_data.get("user", {"username": username, "display_name": username, "bio": "Board Game Explorer"})

    if not plays:
        return {
            "user": user_info,
            "total_played": 0,
            "avg_user_rating": 0.0,
            "avg_preferred_weight": 2.5,
            "top_mechanics": [],
            "top_themes": [],
            "rating_distribution": {i: 0 for i in range(1, 11)},
            "plays": []
        }

    ratings = [p["rating"] for p in plays if p.get("rating") is not None]
    avg_user_rating = sum(ratings) / len(ratings) if ratings else 0.0

    # Weight preference
    weights = [p["game_weight"] for p in plays if p.get("game_weight") and p["game_weight"] > 0]
    avg_weight = sum(weights) / len(weights) if weights else 2.5

    # Mechanics and themes affinity
    mech_counts: Dict[str, int] = {}
    theme_counts: Dict[str, int] = {}

    for p in plays:
        if p.get("mechanics"):
            for m in p["mechanics"].split(";"):
                m_clean = m.strip()
                if m_clean:
                    mech_counts[m_clean] = mech_counts.get(m_clean, 0) + 1
        if p.get("themes"):
            for t in p["themes"].split(";"):
                t_clean = t.strip()
                if t_clean:
                    theme_counts[t_clean] = theme_counts.get(t_clean, 0) + 1

    top_mechanics = sorted(mech_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    top_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    # Rating distribution bucket
    rating_dist = {i: 0 for i in range(1, 11)}
    for r in ratings:
        b = min(10, max(1, round(r)))
        rating_dist[b] += 1

    return {
        "user": user_info,
        "total_played": len(plays),
        "avg_user_rating": round(avg_user_rating, 2),
        "avg_preferred_weight": round(avg_weight, 2),
        "top_mechanics": [{"name": m, "count": c} for m, c in top_mechanics],
        "top_themes": [{"name": t, "count": c} for t, c in top_themes],
        "rating_distribution": rating_dist,
        "plays": plays
    }

def recommend_games_for_user(username: str, limit: int = 12, category: Optional[str] = None, max_weight: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Hybrid recommendation algorithm powered by AatamDB custom vectorized storage.
    Combines user taste vectors with Gaussian complexity penalties and Bayesian quality.
    """
    profile = get_user_profile(username)
    played_ids = set(p["bgg_id"] for p in profile["plays"])
    user_avg_weight = profile.get("avg_preferred_weight", 2.5)
    
    top_user_mechs = set(m["name"].lower() for m in profile.get("top_mechanics", [])[:6])
    top_user_themes = set(t["name"].lower() for t in profile.get("top_themes", [])[:6])

    # Query candidate games from custom AatamDB
    candidates, _ = aatam_db.query(
        category=category,
        max_weight=max_weight,
        sort_by="bayes_avg_rating",
        order="desc",
        limit=500
    )

    scored_candidates = []
    for game in candidates:
        gid = game["bgg_id"]
        if gid in played_ids:
            continue

        # 1. Mechanics score
        game_mechs = set(m.strip().lower() for m in (game.get("mechanics", "") or "").split(";") if m.strip())
        mech_overlap = game_mechs.intersection(top_user_mechs)
        mech_score = (len(mech_overlap) / max(1, len(top_user_mechs))) if top_user_mechs else 0.5

        # 2. Themes score
        game_themes = set(t.strip().lower() for t in (game.get("themes", "") or "").split(";") if t.strip())
        theme_overlap = game_themes.intersection(top_user_themes)
        theme_score = (len(theme_overlap) / max(1, len(top_user_themes))) if top_user_themes else 0.5

        # 3. Weight match score (Gaussian distance)
        gw = game.get("game_weight") or 2.5
        weight_diff = abs(gw - user_avg_weight)
        weight_score = math.exp(-0.5 * (weight_diff / 1.0) ** 2)

        # 4. Bayesian rating score
        bayes = game.get("bayes_avg_rating") or 6.0
        quality_score = min(1.0, max(0.0, (bayes - 6.0) / 2.5))

        # Combined Match Score (0 - 100%)
        match_score = (0.35 * mech_score + 0.20 * theme_score + 0.20 * weight_score + 0.25 * quality_score) * 100
        
        # Build human-readable explanations
        reasons = []
        if mech_overlap:
            formatted_mechs = ", ".join([m.title() for m in list(mech_overlap)[:3]])
            reasons.append(f"Shares favorite mechanics: {formatted_mechs}")
        if theme_overlap:
            formatted_themes = ", ".join([t.title() for t in list(theme_overlap)[:2]])
            reasons.append(f"Matches your theme taste: {formatted_themes}")
        if weight_diff < 0.5:
            reasons.append(f"Complexity sweet spot (Weight {gw:.1f} vs your avg {user_avg_weight:.1f})")
        if bayes >= 7.5:
            reasons.append(f"Top-tier community praise ({bayes:.1f}/10 Geek Rating)")

        game["match_score"] = round(match_score, 1)
        game["match_reasons"] = reasons
        scored_candidates.append(game)

    scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_candidates[:limit]

def get_similar_games(bgg_id: int, limit: int = 6) -> List[Dict[str, Any]]:
    """Return similar games based on mechanics, themes, and weight using AatamDB."""
    target_dict = aatam_db.find_one(bgg_id)
    if not target_dict:
        return []

    target_mechs = set(m.strip().lower() for m in (target_dict.get("mechanics", "") or "").split(";") if m.strip())
    target_themes = set(t.strip().lower() for t in (target_dict.get("themes", "") or "").split(";") if t.strip())
    target_weight = target_dict.get("game_weight") or 2.5

    candidates, _ = aatam_db.query(sort_by="bayes_avg_rating", order="desc", limit=200)

    results = []
    for g in candidates:
        if g["bgg_id"] == bgg_id:
            continue
        g_mechs = set(m.strip().lower() for m in (g.get("mechanics", "") or "").split(";") if m.strip())
        g_themes = set(t.strip().lower() for t in (g.get("themes", "") or "").split(";") if t.strip())
        
        m_overlap = len(g_mechs.intersection(target_mechs))
        t_overlap = len(g_themes.intersection(target_themes))
        w_diff = abs((g.get("game_weight") or 2.5) - target_weight)

        similarity = (m_overlap * 2.5) + (t_overlap * 1.5) - (w_diff * 1.0)
        g["similarity"] = similarity
        results.append(g)

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:limit]
