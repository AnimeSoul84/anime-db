# -*- coding: utf-8 -*-

import json
import os
import sys
import time

# ==========================================================
# FIX PYTHON PATH (CI / GITHUB ACTIONS)
# ==========================================================

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
DELAY_BETWEEN_REQUESTS = 0.25

# ==========================================================
# LOG
# ==========================================================

def log(msg, level="INFO"):
    print(f"[MATCH][{level}] {msg}")

# ==========================================================
# MATCHING
# ==========================================================

def find_best_match(anime: dict, client: TMDBClient) -> dict:
    titles = anime.get("_normalized", {})
    candidates = []

    search_titles = [
        titles.get("english"),
        titles.get("romaji"),
        titles.get("native")
    ]
    search_titles = [t for t in search_titles if t]

    for title in search_titles:
        log(f"Buscando TMDB: {title}")

        results = client.search_multi(title)

        for r in results:
            media_type = r.get("media_type")
            if media_type not in ("tv", "movie"):
                continue

            tmdb_title = r.get("name") or r.get("title")
            if not tmdb_title:
                continue

            tmdb_title_norm = TitleNormalizer.normalize(tmdb_title)
            score = TitleSimilarity.score(title, tmdb_title_norm)

            candidates.append({
                "tmdb_id": r.get("id"),
                "media_type": media_type,
                "title": tmdb_title,
                "score": score
            })

        time.sleep(DELAY_BETWEEN_REQUESTS)

    if not candidates:
        return {
            "status": "NOT_FOUND"
        }

    best = max(candidates, key=lambda x: x["score"])

    if best["score"] >= SCORE_THRESHOLD:
        return {
            "status": "MATCHED",
            "tmdb_id": best["tmdb_id"],
            "media_type": best["media_type"],
            "method": "title_similarity",
            "score": round(best["score"], 3)
        }

    return {
        "status": "NOT_MATCHED",
        "method": "title_similarity",
        "score": round(best["score"], 3)
    }

# ==========================================================
# MAIN
# ==========================================================

def main():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(INPUT_FILE)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        animes = json.load(f)

    client = TMDBClient()

    total = len(animes)
    matched = 0

    for i, anime in enumerate(animes, 1):
        title = anime.get("titles", {}).get("romaji") or "Sem título"
        log(f"[{i}/{total}] {title}")

        result = find_best_match(anime, client)
        anime["match"] = result

        if result.get("status") == "MATCHED":
            anime["tmdb_id"] = result["tmdb_id"]
            anime["media_type"] = result["media_type"]
            matched += 1

    log(f"✔ MATCHED: {matched}/{total}")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(animes, f, ensure_ascii=False, indent=2)

    log(f"Arquivo salvo em {OUTPUT_FILE}")

# ==========================================================
# ENTRYPOINT
# ==========================================================

if __name__ == "__main__":
    main()
