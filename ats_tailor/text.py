"""Text normalisation shared by the base-resume parser and LLM output handling."""

import re
import unicodedata

_PUNCTUATION = [
    (re.compile(r"\s*[—―]\s*"), ", "),       # em dash -> comma
    (re.compile(r"(?<=\w)–(?=\w)"), "-"),          # en dash in ranges -> hyphen
    (re.compile(r"\s*–\s*"), ", "),               # spaced en dash -> comma
    (re.compile(r"[‐‑‒−]"), "-"),  # unicode hyphens / minus
    (re.compile(r"[‘’‚′]"), "'"),
    (re.compile(r"[“”„″]"), '"'),
    (re.compile(r"…"), "..."),
    (re.compile(r"\s*(?:→|->)\s*"), " to "),
    (re.compile(r"[   ]"), " "),
]


def plain_text(text: str) -> str:
    """Remove long dashes, smart quotes and symbols that make text look machine-written."""
    for pattern, repl in _PUNCTUATION:
        text = pattern.sub(repl, text)
    # Keep letters (incl. accents like é), digits, whitespace and plain ASCII punctuation.
    text = "".join(ch for ch in text if ch.isascii() or unicodedata.category(ch)[0] in ("L", "N"))
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return re.sub(r",\s*,", ",", re.sub(r"\s{2,}", " ", text)).strip()


def norm(text: str) -> str:
    """Lower-case, dash-insensitive, whitespace-collapsed form for comparisons."""
    text = text.replace("–", "-").replace("—", "-").lower()
    return re.sub(r"\s+", " ", text).strip()


def key(text: str) -> str:
    """Alphanumeric-only key: 'Think Tree' == 'ThinkTree' == 'think-tree'."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


# Version suffixes of names ("GPT-4", "Llama-3.1") are part of the name, not metrics.
NUMBER_RE = re.compile(r"(?<![\w.])(?<![A-Za-z]-)\d+(?:[.,]\d+)?(?:\s?%|\+)?")


def unsupported_numbers(text: str, source: str) -> list[str]:
    """Numeric tokens (with their %/+ suffix) in `text` that never appear in `source`."""
    known = {n.replace(" ", "") for n in NUMBER_RE.findall(source)}
    return sorted({n.replace(" ", "") for n in NUMBER_RE.findall(text)} - known)


def has_keyword(keyword: str, text: str) -> bool:
    """True if `keyword` appears in `text`, ignoring case, spacing and punctuation.

    Short keywords ("R", "Go", "AWS") must match as whole words to avoid false hits.
    """
    k = key(keyword)
    if not k:
        return True
    if len(k) <= 3:
        return re.search(rf"(?<![a-z0-9]){re.escape(norm(keyword))}(?![a-z0-9])", norm(text)) is not None
    haystack = key(text)
    # Singular/plural variants count ("Recommender systems" ~ "recommender system").
    return k in haystack or (k.endswith("s") and k[:-1] in haystack)


def missing_keywords(keywords: list[str], text: str) -> list[str]:
    seen, missing = set(), []
    for kw in keywords:
        if (k := key(kw)) and k not in seen:
            seen.add(k)
            if not has_keyword(kw, text):
                missing.append(kw.strip())
    return missing
