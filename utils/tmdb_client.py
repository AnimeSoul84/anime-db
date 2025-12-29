# -*- coding: utf-8 -*-

import os
import time
import requests
import itertools
from typing import Optional, Dict, Any, List

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/"

def log(msg: str, level: str = "INFO"):
    print(f"[TMDB][{level}] {msg}")


class TMDBClient:
    def __init__(self, timeout: int = 15, retries: int = 3):
        self.timeout = timeout
        self.retries = retries

        tokens = [
            os.getenv("TMDB_TOKEN_1"),
            os.getenv("TMDB_TOKEN_2"),
            os.getenv("TMDB_TOKEN_3"),
            os.getenv("TMDB_TOKEN_4"),
            os.getenv("TMDB_TOKEN_5"),
        ]
        self.tokens = [t for t in tokens if t]

        if not self.tokens:
            raise RuntimeError("Nenhum TMDB_TOKEN configurado")

        self._token_cycle = itertools.cycle(self.tokens)
        log(f"{len(self.tokens)} tokens TMDB carregados")

    # ======================================================
    # REQUEST
    # ======================================================

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {next(self._token_cycle)}",
            "Accept": "application/json",
            "User-Agent": "anime-db-bot/1.0",
        }

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
        url = f"{TMDB_API_BASE}{endpoint}"

        for attempt in range(1, self.retries + 1):
            try:
                r = requests.get(url, headers=self._headers(), params=params, timeout=self.timeout)

                if r.status_code == 200:
                    return r.json()

                if r.status_code == 429:
                    wait = min(2 * attempt, 10)
                    log(f"429 Rate limit → aguardando {wait}s", "WARN")
                    time.sleep(wait)
                    continue

                log(f"HTTP {r.status_code} em {endpoint}", "WARN")

            except requests.RequestException as e:
                log(f"Erro conexão ({attempt}): {e}", "WARN")

            time.sleep(1.2 * attempt)

        return None

    # ======================================================
    # SEARCH
    # ======================================================

    def search_multi(self, query: str, language: str = "en-US") -> List[Dict]:
        data = self._request("/search/multi", {
            "query": query,
            "include_adult": False,
            "language": language,
        })
        return data.get("results", []) if data else []

    # ======================================================
    # ENRICH
    # ======================================================

    def enrich(self, tmdb_id: int, media_type: str) -> Optional[Dict[str, Any]]:
        params = {
            "append_to_response": "videos,credits,content_ratings,release_dates,keywords",
            "language": "en-US",
        }

        base = self._request(f"/{media_type}/{tmdb_id}", params)
        if not base:
            return None

        return {
            "tmdb": self._normalize(base, media_type),
            "tmdb_localized": self._normalize(
                self._request(f"/{media_type}/{tmdb_id}", {**params, "language": "pt-BR"}),
                media_type
            ),
            "tmdb_fallback": self._normalize(
                self._request(f"/{media_type}/{tmdb_id}", {**params, "language": "ja-JP"}),
                media_type
            ),
        }

    # ======================================================
    # NORMALIZE
    # ======================================================

    def _normalize(self, data: Optional[Dict], media_type: str) -> Optional[Dict]:
        if not data:
            return None

        episode_runtime = data.get("episode_run_time") or []

        return {
            "id": data.get("id"),
            "media_type": media_type,

            "title": data.get("title") or data.get("name"),
            "original_title": data.get("original_title") or data.get("original_name"),

            "overview": data.get("overview"),
            "status": data.get("status"),

            "release_date": data.get("release_date") or data.get("first_air_date"),

            "episodes": data.get("number_of_episodes"),
            "seasons": data.get("number_of_seasons"),

            "runtime": (
                data.get("runtime")
                or (int(sum(episode_runtime) / len(episode_runtime)) if episode_runtime else None)
            ),

            "vote_average": data.get("vote_average"),
            "vote_count": data.get("vote_count"),
            "popularity": data.get("popularity"),

            "poster": self.image_url(data.get("poster_path")),
            "backdrop": self.image_url(data.get("backdrop_path"), "w780"),

            "genres": [g["name"] for g in data.get("genres", [])],
            "studios": [c["name"] for c in data.get("production_companies", [])],
            "networks": [n["name"] for n in data.get("networks", [])],

            "origin_country": data.get("origin_country"),

            "trailers": self._extract_trailers(data.get("videos", {})),
            "content_ratings": self._extract_ratings(data, media_type),
        }

    # ======================================================
    # EXTRAS
    # ======================================================

    def _extract_trailers(self, videos: Dict) -> List[Dict]:
        return [
            {
                "name": v.get("name"),
                "key": v.get("key"),
                "language": v.get("iso_639_1"),
                "official": v.get("official"),
            }
            for v in videos.get("results", [])
            if v.get("site") == "YouTube" and v.get("type") == "Trailer"
        ]

    def _extract_ratings(self, data: Dict, media_type: str) -> Dict[str, str]:
        ratings = {}

        if media_type == "tv":
            for r in data.get("content_ratings", {}).get("results", []):
                ratings[r["iso_3166_1"]] = r.get("rating")
        else:
            for r in data.get("release_dates", {}).get("results", []):
                for d in r.get("release_dates", []):
                    if d.get("certification"):
                        ratings[r["iso_3166_1"]] = d["certification"]

        return ratings

    @staticmethod
    def image_url(path: Optional[str], size: str = "w500") -> Optional[str]:
        return f"{TMDB_IMAGE_BASE}{size}{path}" if path else None