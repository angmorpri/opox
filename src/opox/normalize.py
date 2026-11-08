"""Text normalizations and similarity for deduplication (D011)."""

import re
import unicodedata

from rapidfuzz.distance import Levenshtein

_QUOTES = str.maketrans({"“": '"', "”": '"', "«": '"', "»": '"', "‘": "'", "’": "'"})
_DASHES = re.compile("[‐-―−]")
_ACCENTS = re.compile("[̀́̈]")  # grave, acute, diaeresis; keeps ñ
_SEPARATORS = re.compile(r"[.,;:](?=\s|$)")
_PROSE = re.compile(r"[¿?¡!\"'…]")


def base_key(s: str) -> str:
    """Moderate normalization: NFKC, quotes, dashes, spaces, final dot and case."""
    s = _DASHES.sub("-", unicodedata.normalize("NFKC", s).translate(_QUOTES))
    return re.sub(r"\s+", " ", s).strip().rstrip(".").rstrip().casefold()


def extended_key(s: str) -> str:
    """Aggressive normalization: base plus no accents nor prose punctuation.

    `. , ; :` are only removed before a space or at the end, to keep formulas intact.
    """
    s = unicodedata.normalize("NFC", _ACCENTS.sub("", unicodedata.normalize("NFD", base_key(s))))
    return re.sub(r"\s+", " ", _PROSE.sub(" ", _SEPARATORS.sub(" ", s))).strip()


def similarity(a: str, b: str) -> float:
    """Normalized Levenshtein similarity, 0-100: 1 - edits / longest length."""
    return 100 * Levenshtein.normalized_similarity(a, b)
