# -*- coding: utf-8 -*-

import json
import os
from jsonschema import validate, ValidationError

# ==========================================================
# CONFIG
# ==========================================================

INPUT_FILE = "data/processed/animes_enriched.json"
SCHEMA_FILE = "schemas/anime.schema.json"

OUT_ENRICHED = "data/final/animes_enriched.json"
OUT_NO_TMDB = "data/final/animes_no_tmdb.json"
OUT_NOT_MATCHED = "data/final/animes_not_matched.json"

INDEX_ANILIST = "data/indexes/by_anilist_id.json"
INDEX_TMDB = "data/indexes/by_tmdb_id.json"

# ==========================================================
# LOG
# ==========================================================

def log(msg, level="INFO"):
    print(f"[MAPPER][{level}] {msg}")

# ==========================================================
# HELPERS
# ==========================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clean_temporary_fields(anime: dict) -> dict:
    anime.pop("_normalized", None)
    return anime

def validate_anime(anime: dict, schema: dict):
    validate(instance=anime, schema=schema)

# ==========================================================
# MAIN
# ==========================================================

def main():
    log("Carregando dados...")
    animes = load_json(INPUT_FILE)
    schema = load_json(SCHEMA_FILE)

    enriched = []
    no_tmdb = []
    not_matched = []

    log(f"Processando {len(animes)} animes...")

    for anime in animes:
        anime = clean_temporary_fields(anime)

        match = anime.get("match", {})
        status = match.get("status")

        # ❌ Nunca valida NOT_MATCHED contra schema final
        if status != "MATCHED":
            not_matched.append(anime)
            continue

        # MATCHED mas sem TMDB
        if not anime.get("tmdb"):
            no_tmdb.append(anime)
            continue

        # ✅ Agora sim valida schema
        try:
            validate_anime(anime, schema)
        except ValidationError as e:
            log(
                f"Schema inválido (AniList ID {anime.get('anilist_id')}): {e.message}",
                "ERROR",
            )
            raise

        enriched.append(anime)

    # ======================================================
    # SAVE FILES
    # ======================================================

    log("Salvando arquivos finais...")
    save_json(OUT_ENRICHED, enriched)
    save_json(OUT_NO_TMDB, no_tmdb)
    save_json(OUT_NOT_MATCHED, not_matched)

    # ======================================================
    # INDEXES (APENAS ENRICHED)
    # ======================================================

    log("Gerando indexes...")

    index_anilist = {}
    index_tmdb = {}

    for i, anime in enumerate(enriched):
        index_anilist[str(anime["anilist_id"])] = i

        tmdb = anime.get("tmdb")
        if tmdb and tmdb.get("id"):
            index_tmdb[str(tmdb["id"])] = i

    save_json(INDEX_ANILIST, index_anilist)
    save_json(INDEX_TMDB, index_tmdb)

    # ======================================================
    # SUMMARY
    # ======================================================

    log("✔ MAPPER FINALIZADO")
    log(f"✔ Enriquecidos (válidos): {len(enriched)}")
    log(f"⚠ MATCHED sem TMDB: {len(no_tmdb)}")
    log(f"❌ Não match: {len(not_matched)}")

# ==========================================================
# ENTRYPOINT
# ==========================================================

if __name__ == "__main__":
    main()