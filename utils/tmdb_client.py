# -*- coding: utf-8 -*-

import os
import time
import requests
import itertools
from typing import Optional, Dict, Any, List

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/"

# ==========================================================
# LOG
# ==========================================================

def log(msg: str, level: str = "INFO"):
    print(f"[TMDB][{level}] {msg}")


# ==========================================================
# CLIENT
# ==========================================================

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
            raise RuntimeError(
                "❌ Nenhum TMDB_TOKEN encontrado. "
                "Configure TMDB_TOKEN_1..5 como secrets."
            )

        self._token_cycle = itertools.cycle(self.tokens)
        log(f"{len(self.tokens)} tokens TMDB carregados")

    # ======================================================
    # REQUEST
    # ======================================================

    def _headers(self) -> Dict[str, str]:
        token = next(self._token_cycle)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json;charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "anime-db-bot/1.0 (GitHub Actions)",
        }

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
        url = f"{TMDB_API_BASE}{endpoint}"

        for attempt in range(1, self.retries + 1):
            try:
                response = requests.get(
                    url,
                    headers=self._headers(),
                    params=params,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    wait = min(2 * attempt, 10)
                    log(f"Rate limit (429) em {endpoint}, aguardando {wait}s", "WARN")
                    time.sleep(wait)
                    continue

                log(f"HTTP {response.status_code} em {endpoint}", "WARN")

            except requests.RequestException as e:
                log(f"Erro de conexão ({attempt}/{self.retries}): {e}", "WARN")

            time.sleep(1.2 * attempt)

        log(f"Falha definitiva em {endpoint}", "ERROR")
        return None

    # ======================================================
    # SEARCH
    # ======================================================

    def search_multi(self, query: str, language: str = "en-US") -> List[Dict]:
        data = self._request(
            "/search/multi",
            {
                "query": query,
                "include_adult": False,
                "language": language,
            },
        )

        if not data or "results" not in data:
            return []

        return data["results"]

    # ======================================================
    # ENRICH (METADADOS COMPLETOS)
    # ======================================================

    def enrich(self, tmdb_id: int, media_type: str) -> Optional[Dict[str, Any]]:
        """
        media_type: 'movie' ou 'tv'
        """

        if media_type not in ("movie", "tv"):
            log(f"media_type inválido: {media_type}", "ERROR")
            return None

        params = {
            "append_to_response": "videos,credits,content_ratings,keywords",
            "language": "en-US",
        }

        tmdb = self._request(f"/{media_type}/{tmdb_id}", params)
        if not tmdb:
            return None

        tmdb_localized = self._request(f"/{media_type}/{tmdb_id}", {**params, "language": "pt-BR"})
        tmdb_fallback = self._request(f"/{media_type}/{tmdb_id}", {**params, "language": "ja-JP"})

        return {
            "tmdb": self._normalize(tmdb, media_type),
            "tmdb_localized": self._normalize(tmdb_localized, media_type),
            "tmdb_fallback": self._normalize(tmdb_fallback, media_type),
        }

    # ======================================================
    # NORMALIZE
    # ======================================================

    def _normalize(self, data: Optional[Dict], media_type: str) -> Optional[Dict]:
        if not data:
            return None

        return {
            "id": data.get("id"),
            "media_type": media_type,

            # TITLES
            "title": data.get("title") or data.get("name"),
            "original_title": data.get("original_title") or data.get("original_name"),

            # CONTENT
            "overview": data.get("overview"),
            "status": data.get("status"),

            # DATES
            "release_date": data.get("release_date") or data.get("first_air_date"),

            # STRUCTURE
            "episodes": data.get("number_of_episodes"),
            "seasons": data.get("number_of_seasons"),
            "runtime": data.get("runtime") or (
                data.get("episode_run_time")[0] if data.get("episode_run_time") else None
            ),

            # POPULARITY
            "vote_average": data.get("vote_average"),
            "vote_count": data.get("vote_count"),
            "popularity": data.get("popularity"),

            # IMAGES
            "poster": self.image_url(data.get("poster_path")),
            "backdrop": self.image_url(data.get("backdrop_path"), "w780"),

            # GENRES / STUDIOS / NETWORKS
            "genres": [g["name"] for g in data.get("genres", [])],
            "studios": [c["name"] for c in data.get("production_companies", [])],
            "networks": [n["name"] for n in data.get("networks", [])],

            # COUNTRIES
            "origin_country": data.get("origin_country"),

            # TRAILERS
            "trailers": self._extract_trailers(data.get("videos", {})),

            # RATINGS
            "content_ratings": self._extract_ratings(data, media_type),
        }

    # ======================================================
    # EXTRAS
    # ======================================================

    def _extract_trailers(self, videos: Dict) -> List[Dict]:
        results = videos.get("results", [])
        trailers = []
        for v in results:
            if v.get("site") == "YouTube" and v.get("type") == "Trailer":
                trailers.append({
                    "name": v.get("name"),
                    "key": v.get("key"),
                    "language": v.get("iso_639_1"),
                    "official": v.get("official"),
                })
        return trailers

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

    # ======================================================
    # IMAGE HELPERS
    # ======================================================

    @staticmethod
    def image_url(path: Optional[str], size: str = "w500") -> Optional[str]:
        if not path:
            return None
        return f"{TMDB_IMAGE_BASE}{size}{path}"
