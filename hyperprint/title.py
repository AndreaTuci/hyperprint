"""Block-letter ASCII titles using a built-in 5-row font.

For announcement lines that need more weight than a `print_banner`. The
font is a small embedded dict (~50 entries, ~3 KB of source); zero
runtime dependencies, no file lookup, no parser.
"""

import shutil
import sys
from typing import Optional

from .ansi import stylize, visible_len
from .settings import Settings, DEFAULT


_HEIGHT = 5

# Most letters are 4 cols wide; M N V W X Y T are 5 wide for natural
# proportions. Glyphs are joined with a 1-col separator at render time.
GLYPHS: dict[str, list[str]] = {
    " ": ["   "] * 5,
    "A": [" ██ ", "█  █", "████", "█  █", "█  █"],
    "B": ["███ ", "█  █", "███ ", "█  █", "███ "],
    "C": [" ███", "█   ", "█   ", "█   ", " ███"],
    "D": ["███ ", "█  █", "█  █", "█  █", "███ "],
    "E": ["████", "█   ", "███ ", "█   ", "████"],
    "F": ["████", "█   ", "███ ", "█   ", "█   "],
    "G": [" ███", "█   ", "█ ██", "█  █", " ███"],
    "H": ["█  █", "█  █", "████", "█  █", "█  █"],
    "I": ["███", " █ ", " █ ", " █ ", "███"],
    "J": ["  ██", "   █", "   █", "█  █", " ██ "],
    "K": ["█  █", "█ █ ", "██  ", "█ █ ", "█  █"],
    "L": ["█   ", "█   ", "█   ", "█   ", "████"],
    "M": ["█   █", "██ ██", "█ █ █", "█   █", "█   █"],
    "N": ["█   █", "██  █", "█ █ █", "█  ██", "█   █"],
    "O": [" ██ ", "█  █", "█  █", "█  █", " ██ "],
    "P": ["███ ", "█  █", "███ ", "█   ", "█   "],
    "Q": [" ██ ", "█  █", "█  █", "█ ██", " ███"],
    "R": ["███ ", "█  █", "███ ", "█ █ ", "█  █"],
    "S": [" ███", "█   ", " ██ ", "   █", "███ "],
    "T": ["█████", "  █  ", "  █  ", "  █  ", "  █  "],
    "U": ["█  █", "█  █", "█  █", "█  █", " ██ "],
    "V": ["█   █", "█   █", "█   █", " █ █ ", "  █  "],
    "W": ["█   █", "█   █", "█ █ █", "██ ██", "█   █"],
    "X": ["█   █", " █ █ ", "  █  ", " █ █ ", "█   █"],
    "Y": ["█   █", " █ █ ", "  █  ", "  █  ", "  █  "],
    "Z": ["████", "   █", "  █ ", " █  ", "████"],
    "0": [" ██ ", "█  █", "█  █", "█  █", " ██ "],
    "1": [" █ ", "██ ", " █ ", " █ ", "███"],
    "2": [" ██ ", "█  █", "  █ ", " █  ", "████"],
    "3": ["███ ", "   █", " ██ ", "   █", "███ "],
    "4": ["█  █", "█  █", "████", "   █", "   █"],
    "5": ["████", "█   ", "███ ", "   █", "███ "],
    "6": [" ███", "█   ", "███ ", "█  █", " ██ "],
    "7": ["████", "   █", "  █ ", " █  ", "█   "],
    "8": [" ██ ", "█  █", " ██ ", "█  █", " ██ "],
    "9": [" ██ ", "█  █", " ███", "   █", "███ "],
    "!": ["█", "█", "█", " ", "█"],
    "?": ["███ ", "   █", " ██ ", "    ", " █  "],
    ".": ["  ", "  ", "  ", "  ", "█ "],
    ",": ["  ", "  ", "  ", " █", "█ "],
    "-": ["    ", "    ", "████", "    ", "    "],
    "_": ["    ", "    ", "    ", "    ", "████"],
    ":": ["  ", "█ ", "  ", "█ ", "  "],
    "/": ["    █", "   █ ", "  █  ", " █   ", "█    "],
}


def _terminal_columns(settings: Settings) -> int:
    try:
        cols = shutil.get_terminal_size(
            fallback=(settings.layout.fallback_terminal_width, 24)
        ).columns
    except OSError:
        cols = settings.layout.fallback_terminal_width
    return max(cols, 20)


def print_title(
    text: str,
    color: str = "bright_white",
    *,
    align: str = "left",
    settings: Optional[Settings] = None,
    file=None,
    silent: bool = False,
) -> str:
    """Render `text` as a 5-row block-letter title.

    Args:
        text: the title to render. Letters are uppercased automatically;
            characters not in the built-in font are rendered as blank
            space (so unsupported codepoints leave a gap rather than
            crashing).
        color: ANSI style spec applied uniformly to every row
            (e.g. ``"bright_red"``, ``"bold bright_yellow"``,
            ``"bright_white on red"``). Pass an empty string to skip
            styling.
        align: ``"left"`` (default), ``"center"``, or ``"right"`` —
            placement relative to the terminal width.

    Returns:
        The rendered multi-line string with ANSI escapes. Pass
        ``silent=True`` to skip writing to stdout.
    """
    s = settings or DEFAULT
    chars = text.upper()
    blank = GLYPHS[" "]

    rows: list[str] = []
    for r in range(_HEIGHT):
        parts = [GLYPHS.get(ch, blank)[r] for ch in chars]
        rows.append(" ".join(parts))

    if align in ("center", "right"):
        cols = _terminal_columns(s)
        max_w = max(visible_len(row) for row in rows)
        if max_w < cols:
            pad = cols - max_w
            offset = pad if align == "right" else pad // 2
            rows = [" " * offset + row for row in rows]
    elif align != "left":
        raise ValueError(f"align must be 'left', 'center', or 'right', got {align!r}")

    if color:
        rows = [stylize(row, color, enabled=s.use_color) for row in rows]

    output = "\n".join(rows)

    if not silent:
        stream = file or sys.stdout
        stream.write(output + "\n")
        stream.flush()
    return output
