# -*- coding: utf-8 -*-

import json
import os
import time
from typing import Dict

from utils.tmdb_client import TMDBClient

# ==========================================================
# CONFIG
# ==========================================================

INPUT_FILE = "data/processed/animes_matched.json"
OUTPUT_FILE = "data/processed/animes_enriched.json"

DELAY_BETWEEN_REQUESTS = 0.2  # seguro com cache

# ==========================================================
# LOG
# ==========================================================

def log(msg, level="INFO"):
    print(f"[ENRICH][{level}] {msg}")

# ==========================================================
# CACHE (TMDB ID)
# ==========================================================

_tmdb_cache: Dict[str, dict] = {}

def get_cached(tmdb_id: int, media_type: str):
    return _tmdb_cache.get(f"{media_type}:{tmdb_id}")

def set_cached(tmdb_id: int, media_type: str, data: dict):
    _tmdb_cache[f"{media_type}:{tmdb_id}"] = data

# ==========================================================
# ENRICHMENT
# ==========================================================

def enrich_anime(anime: dict, client: TMDBClient) -> dict:
    match = anime.get("match", {})

    if match.get("status") != "MATCHED":
        anime["tmdb"] = None
        anime["tmdb_localized"] = None
        anime["tmdb_fallback"] = None
        return anime

    tmdb_id = match.get("tmdb_id")
    media_type = match.get("media_type")

    if not tmdb_id or not media_type:
        log("Match inválido, pulando", "WARN")
        anime["tmdb"] = None
        return anime

    cache = get_cached(tmdb_id, media_type)
    if cache:
        anime.update(cache)
        return anime

    try:
        data = client.enrich(tmdb_id, media_type)

        if not data or "tmdb" not in data:
            log(f"Falha ao enriquecer TMDB ID={tmdb_id}", "WARN")
            anime["tmdb"] = None
            return anime

        anime["tmdb"] = data.get("tmdb")
        anime["tmdb_localized"] = data.get("tmdb_localized")
        anime["tmdb_fallback"] = data.get("tmdb_fallback")

        # salva no cache
        set_cached(
            tmdb_id,
            media_type,
            {
                "tmdb": anime["tmdb"],
                "tmdb_localized": anime["tmdb_localized"],
                "tmdb_fallback": anime["tmdb_fallback"],
            },
        )

        return anime

    except Exception as e:
        log(f"Erro inesperado TMDB ID={tmdb_id}: {e}", "ERROR")
        anime["tmdb"] = None
        anime["tmdb_localized"] = None
        anime["tmdb_fallback"] = None
        return anime

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
    enriched = 0

    for i, anime in enumerate(animes, 1):
        title = anime.get("titles", {}).get("romaji", "???")
        log(f"[{i}/{total}] {title}")

        enrich_anime(anime, client)

        if anime.get("tmdb"):
            enriched += 1

        time.sleep(DELAY_BETWEEN_REQUESTS)

    log(f"✔ Enriquecidos: {enriched}/{total}")
    log(f"✔ Cache TMDB usado: {len(_tmdb_cache)} itens")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(animes, f, ensure_ascii=False, indent=2)

    log(f"Arquivo salvo em {OUTPUT_FILE}")

# ==========================================================
# ENTRYPOINT
# ==========================================================

if __name__ == "__main__":
    main()
