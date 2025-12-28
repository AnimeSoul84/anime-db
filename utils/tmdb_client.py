# -*- coding: utf-8 -*-

import os
import time
import requests
import itertools
from typing import Optional, Dict, Any

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
                "Configure TMDB_TOKEN_1..5 como secrets no GitHub Actions."
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
        }

    def _request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
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

                log(f"HTTP {response.status_code} em {endpoint}", "WARN")

            except requests.RequestException as e:
                log(f"Erro de conexão ({attempt}/{self.retries}): {e}", "WARN")

            time.sleep(1.5 * attempt)

        log(f"Falha definitiva em {endpoint}", "ERROR")
        return None

    # ======================================================
    # SEARCH
    # ======================================================

    def search_multi(self, query: str, language: str = "en-US") -> Optional[Dict]:
        return self._request(
            "/search/multi",
            params={
                "query": query,
                "include_adult": False,
                "language": language,
            },
        )

    # ======================================================
    # API METHODS
    # ======================================================

    def get_details(self, tmdb_id: int, media_type: str, language: str) -> Optional[Dict]:
        return self._request(f"/{media_type}/{tmdb_id}", {"language": language})

    def get_videos(self, tmdb_id: int, media_type: str, language: str) -> Optional[Dict]:
        return self._request(f"/{media_type}/{tmdb_id}/videos", {"language": language})

    # ======================================================
    # ENRICH
    # ======================================================

    def enrich(self, tmdb_id: int, media_type: str) -> Dict[str, Any]:
        log(f"Enriquecendo {media_type.upper()} ID={tmdb_id}")

        global_data = self.get_details(tmdb_id, media_type, "en-US")
        if not global_data:
            return {}

        enriched = {
            "tmdb": self._parse_global(global_data, media_type),
            "tmdb_fallback": self._parse_localized(global_data, "en-US"),
        }

        pt = self.get_details(tmdb_id, media_type, "pt-BR")
        enriched["tmdb_localized"] = (
            self._parse_localized(pt, "pt-BR") if pt and pt.get("overview") else None
        )

        trailer = self._get_trailer(tmdb_id, media_type)
        if trailer:
            enriched["tmdb"]["trailer"] = trailer

        return enriched

    # ======================================================
    # PARSERS
    # ======================================================

    def _parse_global(self, data: Dict, media_type: str) -> Dict[str, Any]:
        return {
            "id": data.get("id"),
            "media_type": media_type,
            "original_language": data.get("original_language"),
            "original_name": data.get("original_name") or data.get("original_title"),
            "year": self._extract_year(data),
            "vote_average": data.get("vote_average"),
            "vote_count": data.get("vote_count"),
            "popularity": data.get("popularity"),
            "status": data.get("status"),
            "genres": [g["name"] for g in data.get("genres", [])],
        }

    def _parse_localized(self, data: Dict, language: str) -> Dict[str, Any]:
        return {
            "language": language,
            "title": data.get("name") or data.get("title"),
            "overview": data.get("overview"),
            "poster": self._img(data.get("poster_path"), "w500"),
            "backdrop": self._img(data.get("backdrop_path"), "w780"),
        }

    def _get_trailer(self, tmdb_id: int, media_type: str) -> Optional[str]:
        for lang in ("pt-BR", "en-US"):
            videos = self.get_videos(tmdb_id, media_type, lang)
            if not videos:
                continue

            for v in videos.get("results", []):
                if v.get("site") == "YouTube" and v.get("type") == "Trailer":
                    return v.get("key")
        return None

    # ======================================================
    # HELPERS
    # ======================================================

    @staticmethod
    def _extract_year(data: Dict) -> Optional[int]:
        date = data.get("first_air_date") or data.get("release_date")
        return int(date[:4]) if date else None

    @staticmethod
    def _img(path: Optional[str], size: str) -> Optional[str]:
        return f"{TMDB_IMAGE_BASE}{size}{path}" if path else None
