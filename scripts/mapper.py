# -*- coding: utf-8 -*-

import json
import os
from jsonschema import validate, ValidationError

# ==========================================================
# CONFIG
# ==========================================================

VALIDATE = False  # ⚠️ Termux = False | GitHub Actions = True

# ==========================================================
# PATHS
# ==========================================================

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

INPUT_FILE = os.path.join(ROOT_DIR, "data", "raw", "anilist_raw.json")
OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "processed", "anilist_mapped.json")
SCHEMA_FILE = os.path.join(ROOT_DIR, "schemas", "anime.schema.json")

# ==========================================================
# LOG
# ==========================================================

def log(msg, level="INFO"):
    print(f"[MAPPER][{level}] {msg}", flush=True)

# ==========================================================
# MAPPER
# ==========================================================

def map_anime(raw: dict) -> dict:
    return {
        "anilist_id": raw.get("anilist_id"),
        "titles": raw.get("titles", {}),
        "format": raw.get("format"),
        "status": raw.get("status"),
        "episodes": raw.get("episodes"),
        "year": raw.get("year"),
        "genres": raw.get("genres", []),
        "anilist_score": raw.get("anilist_score"),
        "popularity": raw.get("popularity"),
        "match": raw.get("match", {"status": "NOT_PROCESSED"}),
    }

# ==========================================================
# MAIN
# ==========================================================

def main():
    log("Carregando AniList raw")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw_animes = json.load(f)

    schema = None
    if VALIDATE:
        log("Carregando schema")
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema = json.load(f)

    mapped = []

    for i, anime in enumerate(raw_animes, start=1):
        mapped_anime = map_anime(anime)

        if VALIDATE:
            try:
                validate(instance=mapped_anime, schema=schema)
            except ValidationError as e:
                log(
                    f"Schema inválido para AniList {anime.get('anilist_id')}: {e.message}",
                    "ERROR"
                )
                continue

        mapped.append(mapped_anime)

        if i % 500 == 0:
            log(f"Processados: {i}")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mapped, f, ensure_ascii=False, indent=2)

    log(f"✔ Mapeados: {len(mapped)}")

if __name__ == "__main__":
    main()
