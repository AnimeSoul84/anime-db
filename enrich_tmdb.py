# -*- coding: utf-8 -*-

import json
import os
import time

from utils.tmdb_client import TMDBClient

# ==========================================================
# CONFIG
# ==========================================================

INPUT_FILE = "data/processed/animes_matched.json"
OUTPUT_FILE = "data/processed/animes_enriched.json"

DELAY_BETWEEN_REQUESTS = 0.3

# ==========================================================
# LOG
# ==========================================================

def log(msg, level="INFO"):
    print(f"[ENRICH][{level}] {msg}")

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

    try:
        data = client.enrich(tmdb_id, media_type)

        if not data or "tmdb" not in data:
            log(f"Falha ao enriquecer TMDB ID={tmdb_id}", "WARN")
            anime["tmdb"] = None
            return anime

        anime["tmdb"] = data.get("tmdb")
        anime["tmdb_localized"] = data.get("tmdb_localized")
        anime["tmdb_fallback"] = data.get("tmdb_fallback")

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

        anime = enrich_anime(anime, client)

        if anime.get("tmdb"):
            enriched += 1

        time.sleep(DELAY_BETWEEN_REQUESTS)

    log(f"✔ Enriquecidos: {enriched}/{total}")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(animes, f, ensure_ascii=False, indent=2)

    log(f"Arquivo salvo em {OUTPUT_FILE}")

# ==========================================================
# ENTRYPOINT
# ==========================================================

if __name__ == "__main__":
    main()
