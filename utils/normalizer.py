# -*- coding: utf-8 -*-

import re
import unicodedata
from typing import Optional

# ==========================================================
# PALAVRAS INÚTEIS (STOPWORDS)
# ==========================================================

STOPWORDS = {
    "the", "a", "an",
    "season", "seasons",
    "part", "parts",
    "cour",
    "episode", "episodes",
    "tv", "series",
    "movie", "film",
    "ova", "ona", "special", "specials",
    "anime"
}

# ==========================================================
# NORMALIZER
# ==========================================================

class TitleNormalizer:
    @staticmethod
    def normalize(title: Optional[str]) -> Optional[str]:
        """
        Normaliza um título para comparação.
        Retorna string limpa ou None.
        """
        if not title:
            return None

        # --------------------------
        # lowercase
        # --------------------------
        text = title.lower()

        # --------------------------
        # remover acentos (latin)
        # --------------------------
        text = unicodedata.normalize("NFKD", text)
        text = "".join(
            c for c in text
            if not unicodedata.combining(c)
        )

        # --------------------------
        # remover símbolos (mantém japonês)
        # --------------------------
        text = re.sub(r"[^\w\s\u3040-\u30ff\u4e00-\u9faf]", " ", text)

        # --------------------------
        # remover stopwords
        # --------------------------
        words = []
        for word in text.split():
            if word not in STOPWORDS:
                words.append(word)

        text = " ".join(words)

        # --------------------------
        # normalizar espaços
        # --------------------------
        text = re.sub(r"\s+", " ", text).strip()

        return text if text else None

    @staticmethod
    def normalize_all(titles: dict) -> dict:
        """
        Normaliza múltiplos títulos (romaji, english, native).
        """
        return {
            key: TitleNormalizer.normalize(value)
            for key, value in titles.items()
            if value
        }
