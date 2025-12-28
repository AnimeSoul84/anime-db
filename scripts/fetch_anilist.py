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
    "Accept": "application/json"
}

# GraphQL query completa e segura
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


def log(msg: str):
    print(f"[AniList] {msg}")


def fetch_page(page: int) -> Dict:
    payload = {
        "query": QUERY,
        "variables": {"page": page}
    }

    for attempt in range(3):
        try:
            response = requests.post(
                ANILIST_API,
                json=payload,
                headers=HEADERS,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log(f"Erro na página {page} (tentativa {attempt + 1}/3): {e}")
            time.sleep(2)

    raise RuntimeError(f"Falha definitiva ao buscar página {page}")


def fetch_all_animes() -> List[Dict]:
    page = 1
    all_animes = []

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
        time.sleep(0.6)  # respeita a API

    return all_animes


def save_json(data: List[Dict]):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log(f"Arquivo salvo em: {OUTPUT_FILE}")
    log(f"Total final de animes: {len(data)}")


def main():
    animes = fetch_all_animes()
    save_json(animes)


if __name__ == "__main__":
    main()
