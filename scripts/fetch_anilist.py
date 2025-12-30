# -*- coding: utf-8 -*-

import os
import json
import time
import requests
from typing import List, Dict, Any

# ==========================================================
# CONFIG
# ==========================================================

ANILIST_API = "https://graphql.anilist.co"

OUTPUT_DIR = "data/raw"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "anilist_raw.json")

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "anime-db-github-action",
}

QUERY = """
query ($page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo {
      hasNextPage
      currentPage
      lastPage
    }
    media(type: ANIME, isAdult: false) {
      id
      format
      status
      episodes
      startDate { year }
      genres
      averageScore
      popularity
      title {
        romaji
        english
        native
      }
    }
  }
}
"""

# ==========================================================
# LOG
# ==========================================================

def log(msg: str, level: str = "INFO"):
    print(f"[AniList][{level}] {msg}")

# ==========================================================
# REQUEST (COM RETRY + RATE LIMIT)
# ==========================================================

def request(payload: Dict[str, Any], retries: int = 6) -> Dict[str, Any]:
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(
                ANILIST_API,
                headers=HEADERS,
                json=payload,
                timeout=30,
            )

            if r.status_code == 200:
                return r.json()

            if r.status_code == 429:
                wait = 10 * attempt
                log(f"Rate limit 429 — aguardando {wait}s", "WARN")
                time.sleep(wait)
                continue

            r.raise_for_status()

        except requests.RequestException as e:
            log(f"Erro de rede ({attempt}/{retries}): {e}", "ERROR")
            time.sleep(5 * attempt)

    raise RuntimeError("❌ AniList indisponível após múltiplas tentativas")

# ==========================================================
# NORMALIZE RAW (BLINDADO)
# ==========================================================

def normalize_media(media: Dict[str, Any]) -> Dict[str, Any]:
    title = media.get("title") or {}

    romaji = title.get("romaji") or ""
    english = title.get("english")
    native = title.get("native")

    return {
        # obrigatório
        "anilist_id": media.get("id"),

        "titles": {
            "romaji": romaji,               # NUNCA null
            "english": english,
            "native": native,
        },

        # AniList pode retornar null → schema aceita
        "format": media.get("format"),
        "status": media.get("status"),
        "episodes": media.get("episodes"),
        "year": (media.get("startDate") or {}).get("year"),

        "genres": media.get("genres") or [],
        "anilist_score": media.get("averageScore"),
        "popularity": media.get("popularity"),

        # placeholder para pipeline
        "match": {
            "status": "NOT_FOUND"
        }
    }

# ==========================================================
# FETCH ALL
# ==========================================================

def fetch_all() -> List[Dict[str, Any]]:
    page = 1
    results: List[Dict[str, Any]] = []

    while True:
        log(f"Coletando página {page}")

        data = request({
            "query": QUERY,
            "variables": {"page": page},
        })

        page_data = data.get("data", {}).get("Page")
        if not page_data:
            raise RuntimeError("Resposta inválida da AniList")

        media_list = page_data.get("media") or []

        for media in media_list:
            results.append(normalize_media(media))

        if not page_data.get("pageInfo", {}).get("hasNextPage"):
            break

        page += 1
        time.sleep(0.8)

    return results

# ==========================================================
# MAIN
# ==========================================================

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    log("Iniciando coleta do AniList...")
    animes = fetch_all()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(animes, f, ensure_ascii=False, indent=2)

    log(f"✔ Arquivo salvo: {OUTPUT_FILE}")
    log(f"✔ Total coletado: {len(animes)}")

if __name__ == "__main__":
    main()
