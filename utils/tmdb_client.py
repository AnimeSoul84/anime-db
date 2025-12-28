# -*- coding: utf-8 -*-

import os
import time
import requests
import itertools
from typing import Optional, Dict, Any

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/"

# ==========================================================
# TOKENS V4 (ROTATION)
# ==========================================================

TOKENS = [
    os.getenv("TMDB_TOKEN_1"),
    os.getenv("TMDB_TOKEN_2"),
    os.getenv("TMDB_TOKEN_3"),
    os.getenv("TMDB_TOKEN_4"),
    os.getenv("TMDB_TOKEN_5"),
]

TOKENS = [t for t in TOKENS if t]
TOKEN_CYCLE = itertools.cycle(TOKENS)

if not TOKENS:
    raise RuntimeError("❌ Nenhum TMDB_TOKEN encontrado no ambiente")

# ==========================================================
# LOGGING (SIMPLES, LIMPO, PROFISSIONAL)
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

    def _headers(self) -> Dict[str, str]:
        token = next(TOKEN_CYCLE)
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
    # DADOS PRINCIPAIS (FILME / SÉRIE)
    # ======================================================

    def get_details(self, tmdb_id: int, media_type: str, language: str) -> Optional[Dict]:
        endpoint = f"/{media_type}/{tmdb_id}"
        return self._request(endpoint, params={"language": language})

    def get_videos(self, tmdb_id: int, media_type: str, language: str) -> Optional[Dict]:
        endpoint = f"/{media_type}/{tmdb_id}/videos"
        return self._request(endpoint, params={"language": language})

    # ======================================================
    # ENRIQUECIMENTO COMPLETO
    # ======================================================

    def enrich(self, tmdb_id: int, media_type: str) -> Dict[str, Any]:
        log(f"Enriquecendo {media_type.upper()} ID={tmdb_id}")

        # -------------------------
        # GLOBAL (en-US)
        # -------------------------
        global_data = self.get_details(tmdb_id, media_type, "en-US")
        if not global_data:
            log("Dados globais não encontrados", "ERROR")
            return {}

        enriched = {
            "tmdb": self._parse_global(global_data, media_type)
        }

        # -------------------------
        # PT-BR
        # -------------------------
        pt_data = self.get_details(tmdb_id, media_type, "pt-BR")
        if pt_data and pt_data.get("overview"):
            enriched["tmdb_localized"] = self._parse_localized(pt_data, "pt-BR")
        else:
            enriched["tmdb_localized"] = None

        # -------------------------
        # FALLBACK en-US
        # -------------------------
        enriched["tmdb_fallback"] = self._parse_localized(global_data, "en-US")

        # -------------------------
        # TRAILER
        # -------------------------
        trailer = self._get_trailer(tmdb_id, media_type)
        if trailer:
            enriched["tmdb"]["trailer"] = trailer

        log(f"✔ Enriquecimento concluído ID={tmdb_id}")
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
            "first_air_date": data.get("first_air_date") or data.get("release_date"),
            "year": self._extract_year(data),
            "number_of_seasons": data.get("number_of_seasons"),
            "number_of_episodes": data.get("number_of_episodes"),
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
            "tagline": data.get("tagline"),
            "poster": self._img(data.get("poster_path"), "w500"),
            "backdrop": self._img(data.get("backdrop_path"), "w780"),
        }

    def _get_trailer(self, tmdb_id: int, media_type: str) -> Optional[str]:
        for lang in ("pt-BR", "en-US"):
            videos = self.get_videos(tmdb_id, media_type, lang)
            if not videos:
                continue

            for v in videos.get("results", []):
                if v["site"] == "YouTube" and v["type"] == "Trailer":
                    return v["key"]

        return None

    # ======================================================
    # HELPERS
    # ======================================================

    @staticmethod
    def _extract_year(data: Dict) -> Optional[int]:
        date = data.get("first_air_date") or data.get("release_date")
        if date and len(date) >= 4:
            return int(date[:4])
        return None

    @staticmethod
    def _img(path: Optional[str], size: str) -> Optional[str]:
        if not path:
            return None
        return f"{TMDB_IMAGE_BASE}{size}{path}"
