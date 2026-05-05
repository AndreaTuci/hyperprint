"""ANSI escape helpers.

`stylize(text, "bold bright_yellow on red")` is the only public function
the rest of the package uses. Style strings mirror the rich syntax so
settings.Palette stays human-readable.
"""

import re

RESET = "\x1b[0m"

_FG = {
    "black": 30, "red": 31, "green": 32, "yellow": 33,
    "blue": 34, "magenta": 35, "cyan": 36, "white": 37,
    "bright_black": 90, "bright_red": 91, "bright_green": 92,
    "bright_yellow": 93, "bright_blue": 94, "bright_magenta": 95,
    "bright_cyan": 96, "bright_white": 97,
}

_BG = {name: code + 10 for name, code in _FG.items()}

_ATTR = {
    "bold": 1, "dim": 2, "italic": 3, "underline": 4,
    "blink": 5, "reverse": 7, "strike": 9,
}

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(text: str) -> int:
    """Length of a string without ANSI escapes."""
    return len(_ANSI_RE.sub("", text))


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _parse_style(spec: str) -> list[int]:
    if not spec:
        return []
    codes: list[int] = []
    tokens = spec.split()
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "on" and i + 1 < len(tokens):
            bg = tokens[i + 1]
            if bg in _BG:
                codes.append(_BG[bg])
            i += 2
            continue
        if tok in _ATTR:
            codes.append(_ATTR[tok])
        elif tok in _FG:
            codes.append(_FG[tok])
        i += 1
    return codes


def stylize(text: str, spec: str, *, enabled: bool = True) -> str:
    if not enabled or not spec:
        return text
    codes = _parse_style(spec)
    if not codes:
        return text
    return f"\x1b[{';'.join(str(c) for c in codes)}m{text}{RESET}"


def pad_visible(text: str, width: int, align: str = "left") -> str:
    """Pad `text` to `width` columns ignoring ANSI escapes."""
    pad = width - visible_len(text)
    if pad <= 0:
        return text
    if align == "right":
        return " " * pad + text
    if align == "center":
        left = pad // 2
        return " " * left + text + " " * (pad - left)
    return text + " " * pad
