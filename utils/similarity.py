# -*- coding: utf-8 -*-

from difflib import SequenceMatcher
from typing import Optional


class TitleSimilarity:
    @staticmethod
    def ratio(a: Optional[str], b: Optional[str]) -> float:
        """
        Similaridade básica entre duas strings.
        Retorna valor entre 0.0 e 1.0
        """
        if not a or not b:
            return 0.0

        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def word_overlap(a: Optional[str], b: Optional[str]) -> float:
        """
        Mede sobreposição de palavras.
        """
        if not a or not b:
            return 0.0

        set_a = set(a.split())
        set_b = set(b.split())

        if not set_a or not set_b:
            return 0.0

        intersection = set_a & set_b
        union = set_a | set_b

        return len(intersection) / len(union)

    @staticmethod
    def score(a: Optional[str], b: Optional[str]) -> float:
        """
        Score final combinado.
        """
        if not a or not b:
            return 0.0

        ratio_score = TitleSimilarity.ratio(a, b)
        overlap_score = TitleSimilarity.word_overlap(a, b)

        # Boost se uma string contém a outra
        contains_boost = 0.0
        if a in b or b in a:
            contains_boost = 0.1

        final_score = (
            ratio_score * 0.7 +
            overlap_score * 0.3 +
            contains_boost
        )

        return min(round(final_score, 3), 1.0)
