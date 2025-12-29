# -*- coding: utf-8 -*-

import os
import json
import time
import requests

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

def log(msg):
    print(f"[AniList] {msg}")

def request(payload, retries=6):
    for attempt in range(retries):
        r = requests.post(
            ANILIST_API,
            headers=HEADERS,
            json=payload,
            timeout=30,
        )

        if r.status_code == 200:
            return r.json()

        if r.status_code == 429:
            wait = 10 * (attempt + 1)
            log(f"Rate limit 429 — aguardando {wait}s")
            time.sleep(wait)
            continue

        r.raise_for_status()

    raise RuntimeError("AniList rate limit persistente")

def fetch_all():
    page = 1
    results = []

    while True:
        log(f"Coletando página {page}")

        data = request({
            "query": QUERY,
            "variables": {"page": page},
        })

        page_data = data["data"]["Page"]
        results.extend(page_data["media"])

        if not page_data["pageInfo"]["hasNextPage"]:
            break

        page += 1
        time.sleep(0.8)

    return results

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    animes = fetch_all()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(animes, f, ensure_ascii=False, indent=2)

    log(f"Arquivo salvo: {OUTPUT_FILE}")
    log(f"Total coletado: {len(animes)}")

if __name__ == "__main__":
    main()
