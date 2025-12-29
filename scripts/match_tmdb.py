# -*- coding: utf-8 -*-

import json
import os
import sys
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from utils.normalizer import TitleNormalizer
from utils.similarity import TitleSimilarity
from utils.tmdb_client import TMDBClient

# ==========================================================
# CONFIG
# ==========================================================

INPUT_FILE = "data/processed/anilist_normalized.json"
OUTPUT_FILE = "data/processed/animes_matched.json"

SCORE_THRESHOLD = 0.75
FAST_MATCH_THRESHOLD = 0.92
DELAY_BETWEEN_REQUESTS = 0.1

# ==========================================================
# LOG
# ==========================================================

def log(msg, level="INFO"):
    print(f"[MATCH][{level}] {msg}")

# ==========================================================
# HELPERS
# ==========================================================

def get_display_title(anime: dict) -> str:
    titles = anime.get("_normalized", {})
    return (
        titles.get("english")
        or titles.get("romaji")
        or titles.get("native")
        or f"AniList {anime['anilist_id']}"
    )

def get_search_titles(anime: dict) -> list[str]:
    titles = anime.get("_normalized", {})
    search = []

    if titles.get("english"):
        search.append(titles["english"])
    if titles.get("romaji") and titles["romaji"] not in search:
        search.append(titles["romaji"])
    if titles.get("native") and titles["native"] not in search:
        search.append(titles["native"])

    return search

# ==========================================================
# MATCHING
# ==========================================================

def find_best_match(anime: dict, client: TMDBClient) -> dict:
    candidates = []

    for title in get_search_titles(anime):
        log(f"Buscando TMDB: {title}")

        results = client.search_multi(title)[:5]

        for r in results:
            media_type = r.get("media_type")
            if media_type not in ("tv", "movie"):
                continue

            tmdb_title = r.get("name") or r.get("title")
            if not tmdb_title:
                continue

            tmdb_title_norm = TitleNormalizer.normalize(tmdb_title)
            score = TitleSimilarity.score(title, tmdb_title_norm)

            if score >= FAST_MATCH_THRESHOLD:
                return {
                    "status": "MATCHED",
                    "tmdb_id": r["id"],
                    "media_type": media_type,
                    "method": "title_similarity_fast",
                    "score": round(score, 3),
                }

            candidates.append({
                "tmdb_id": r["id"],
                "media_type": media_type,
                "title": tmdb_title,
                "score": score,
            })

        time.sleep(DELAY_BETWEEN_REQUESTS)

    if not candidates:
        return {"status": "NOT_FOUND"}

    best = max(candidates, key=lambda x: x["score"])

    if best["score"] >= SCORE_THRESHOLD:
        return {
            "status": "MATCHED",
            "tmdb_id": best["tmdb_id"],
            "media_type": best["media_type"],
            "method": "title_similarity",
            "score": round(best["score"], 3),
        }

    return {
        "status": "NOT_MATCHED",
        "method": "title_similarity",
        "score": round(best["score"], 3),
    }

# ==========================================================
# MAIN
# ==========================================================

def main():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(INPUT_FILE)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        animes = json.load(f)

    # normalize titles
    for anime in animes:
        anime["_normalized"] = TitleNormalizer.normalize_all(anime["titles"])

    client = TMDBClient()
    matched = 0

    for i, anime in enumerate(animes, 1):
        log(f"[{i}/{len(animes)}] {get_display_title(anime)}")

        result = find_best_match(anime, client)
        anime["match"] = result

        if result["status"] == "MATCHED":
            matched += 1

    log(f"✔ MATCHED: {matched}/{len(animes)}")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(animes, f, ensure_ascii=False, indent=2)

    log(f"Arquivo salvo em {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
