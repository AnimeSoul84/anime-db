# -*- coding: utf-8 -*-

import os
import json
import time
import requests
from typing import List, Dict

ANILIST_API = "https://graphql.anilist.co"
OUTPUT_FILE = "data/raw/anilist_raw.json"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "anime-db-bot/1.0 (https://github.com/AnimeSoul84/anime-db)"
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
    }
  }
}
"""


def log(msg: str):
    print(f"[AniList] {msg}")


def fetch_page(page: int) -> Dict:
    payload = {
        "query": QUERY,
        "variables": {"page": page}
    }

    wait = 2

    while True:
        response = requests.post(
            ANILIST_API,
            json=payload,
            headers=HEADERS,
            timeout=30
        )

        # ✅ sucesso
        if response.status_code == 200:
            return response.json()

        # ⏳ rate limit
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            delay = int(retry_after) if retry_after else wait
            log(f"Rate limit na página {page}, aguardando {delay}s...")
            time.sleep(delay)
            wait = min(wait * 2, 60)
            continue

        # ❌ erro real
        log(f"Erro HTTP {response.status_code} na página {page}")
        time.sleep(wait)
        wait = min(wait * 2, 60)


def fetch_all_animes() -> List[Dict]:
    page = 1
    all_animes: List[Dict] = []

    log("Iniciando coleta completa do AniList")

    while True:
        data = fetch_page(page)

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
        time.sleep(0.8)  # seguro para CI

    return all_animes


def save_json(data: List[Dict]):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log(f"Arquivo salvo em: {OUTPUT_FILE}")
    log(f"Total final de animes: {len(data)}")


def main():
    # ✅ NÃO refaz se já existir
    if os.path.exists(OUTPUT_FILE):
        log("Arquivo anilist_raw.json já existe, pulando coleta.")
        return

    animes = fetch_all_animes()
    save_json(animes)


if __name__ == "__main__":
    main()
