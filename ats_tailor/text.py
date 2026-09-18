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


NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?:\s?%|\+)?")


def unsupported_numbers(text: str, source: str) -> list[str]:
    """Numeric tokens (with their %/+ suffix) in `text` that never appear in `source`."""
    known = {n.replace(" ", "") for n in NUMBER_RE.findall(source)}
    return sorted({n.replace(" ", "") for n in NUMBER_RE.findall(text)} - known)
