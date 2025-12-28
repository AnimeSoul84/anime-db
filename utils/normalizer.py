# -*- coding: utf-8 -*-

import re
import unicodedata
from typing import Optional, Dict

# ==========================================================
# STOPWORDS
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
        if not title:
            return None

        text = title.lower()

        # remove acentos (latin)
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))

        # remove símbolos (mantém japonês)
        text = re.sub(r"[^\w\s\u3040-\u30ff\u4e00-\u9faf]", " ", text)

        # remove stopwords
        words = [w for w in text.split() if w not in STOPWORDS]
        text = " ".join(words)

        # normaliza espaços
        text = re.sub(r"\s+", " ", text).strip()

        return text or None

    @staticmethod
    def normalize_all(titles: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
        return {
            key: TitleNormalizer.normalize(value)
            for key, value in titles.items()
            if value
        }
