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
