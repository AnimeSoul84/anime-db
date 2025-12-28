# -*- coding: utf-8 -*-

import os
import json
import time
import requests
from typing import List, Dict, Optional

ANILIST_API = "https://graphql.anilist.co"

OUTPUT_FILE = "data/raw/anilist_raw.json"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# ==========================================================
# GRAPHQL QUERY
# ==========================================================

QUERY = """
query ($page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo {
      hasNextPage
      currentPage
      lastPage
    }
    media(type: ANIME) {
      id
      title {
        romaji
        english
        native
      }
      format
      status
      episodes
      startDate {
        year
      }
      genres
      averageScore
      popularity
      isAdult
    }
  }
}
"""

# ==========================================================
# LOG
# ==========================================================

def log(msg: str):
    print(f"[AniList] {msg}")

# ==========================================================
# FETCH PAGE (COM BACKOFF E RATE LIMIT)
# ==========================================================

def fetch_page(page: int) -> Optional[Dict]:
    payload = {
        "query": QUERY,
        "variables": {"page": page}
    }

    delay = 2

    for attempt in range(1, 6):  # até 5 tentativas
        try:
            response = requests.post(
                ANILIST_API,
                json=payload,
                headers=HEADERS,
                timeout=30
            )

            # Rate limit
            if response.status_code == 429:
                log(f"Rate limit na página {page}, aguardando {delay}s...")
                time.sleep(delay)
                delay *= 2
                continue

            response.raise_for_status()
            return response.json()

        except Exception as e:
            log(f"Erro página {page} ({attempt}/5): {e}")
            time.sleep(delay)
            delay *= 2

    log(f"❌ Pulando página {page} após múltiplas falhas")
    return None

# ==========================================================
# FETCH ALL
# ==========================================================

def fetch_all_animes() -> List[Dict]:
    page = 1
    all_animes: List[Dict] = []

    log("Iniciando coleta completa do AniList")

    while True:
        data = fetch_page(page)

        if not data:
            page += 1
            continue

        page_info = data["data"]["Page"]["pageInfo"]
        media = data["data"]["Page"]["media"]

        all_animes.extend(media)

        log(
            f"Página {page_info['currentPage']} / {page_info['lastPage']} "
            f"| Total coletado: {len(all_animes)}"
        )

        if not page_info["hasNextPage"]:
            break

        page += 1
        time.sleep(1.2)  # seguro para GitHub Actions

    return all_animes

# ==========================================================
# SAVE
# ==========================================================

def save_json(data: List[Dict]):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log(f"Arquivo salvo em: {OUTPUT_FILE}")
    log(f"Total final de animes: {len(data)}")

# ==========================================================
# MAIN
# ==========================================================

def main():
    animes = fetch_all_animes()
    save_json(animes)

if __name__ == "__main__":
    main()
