# -*- coding: utf-8 -*-

import json
import os
from jsonschema import validate, ValidationError

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
    print(f"[MAPPER][{level}] {msg}")

# ==========================================================
# MAPPER
# ==========================================================

def map_anime(raw: dict) -> dict:
    return {
        "anilist_id": raw.get("id"),
        "titles": {
            "romaji": raw.get("title", {}).get("romaji"),
            "english": raw.get("title", {}).get("english"),
            "native": raw.get("title", {}).get("native"),
        },
        "format": raw.get("format"),
        "status": raw.get("status"),
        "episodes": raw.get("episodes"),
        "year": raw.get("startDate", {}).get("year"),
        "genres": raw.get("genres", []),
        "anilist_score": raw.get("averageScore"),
        "match": {"status": "NOT_PROCESSED"}
    }

# ==========================================================
# MAIN
# ==========================================================

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw_animes = json.load(f)

    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema = json.load(f)

    mapped = []

    for anime in raw_animes:
        mapped_anime = map_anime(anime)

        try:
            validate(instance=mapped_anime, schema=schema)
        except ValidationError as e:
            log(f"Schema inválido para AniList {anime.get('id')}: {e.message}", "ERROR")
            continue

        mapped.append(mapped_anime)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mapped, f, ensure_ascii=False, indent=2)

    log(f"✔ Mapeados e validados: {len(mapped)}")

if __name__ == "__main__":
    main()