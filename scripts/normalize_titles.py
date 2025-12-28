# -*- coding: utf-8 -*-

import json
import os
import sys

# ==========================================================
# FIX PYTHON PATH (CI / GITHUB ACTIONS)
# ==========================================================

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from utils.normalizer import TitleNormalizer

# ==========================================================
# CONFIG
# ==========================================================

INPUT_FILE = "data/raw/anilist_raw.json"
OUTPUT_FILE = "data/processed/anilist_normalized.json"

# ==========================================================
# LOG
# ==========================================================

def log(msg, level="INFO"):
    print(f"[NORMALIZE][{level}] {msg}")

# ==========================================================
# NORMALIZATION
# ==========================================================

def normalize_anime(anime: dict) -> dict:
    titles = anime.get("title") or anime.get("titles")

    if not titles:
        anime["_normalized"] = {}
        return anime

    anime["_normalized"] = TitleNormalizer.normalize_all({
        "romaji": titles.get("romaji"),
        "english": titles.get("english"),
        "native": titles.get("native"),
    })

    return anime

# ==========================================================
# MAIN
# ==========================================================

def main():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(INPUT_FILE)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        animes = json.load(f)

    log(f"Normalizando títulos de {len(animes)} animes...")

    normalized = [normalize_anime(anime) for anime in animes]

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    log(f"✔ Arquivo salvo em {OUTPUT_FILE}")

# ==========================================================
# ENTRYPOINT
# ==========================================================

if __name__ == "__main__":
    main()
