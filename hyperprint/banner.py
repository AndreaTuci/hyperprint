"""Eye-catching emoji banners for highlighting log rows.

A banner is a single line (or sandwich) of repeating pictographic glyphs
that stretches across the terminal, optionally framing a centered message.
Useful as a section divider or as an "this row matters" mark in long
log streams.

The default level set picks single-codepoint emoji that reliably render at
two columns on most monospace terminals. If yours doesn't, tweak
`Layout.banner_emoji_width`.
"""

import shutil
import sys
from dataclasses import dataclass
from typing import Optional, Union

from .ansi import stylize, visible_len
from .settings import Settings, DEFAULT


@dataclass(frozen=True)
class BannerLevel:
    """A pairing of pictographic glyph and ANSI style for the message."""
    emoji: str
    color: str


LEVELS: dict[str, BannerLevel] = {
    "info":     BannerLevel("💡", "bright_blue"),
    "success":  BannerLevel("✅", "bright_green"),
    "warning":  BannerLevel("🟡", "bright_yellow"),
    "error":    BannerLevel("🚩", "bright_red"),
    "critical": BannerLevel("🚨", "bold bright_red"),
    "debug":    BannerLevel("🐞", "magenta"),
    "note":     BannerLevel("📝", "cyan"),
    "fire":     BannerLevel("🔥", "bright_red"),
    "rocket":   BannerLevel("🚀", "bright_magenta"),
    "party":    BannerLevel("🎉", "bright_yellow"),
    "lock":     BannerLevel("🔒", "bright_white"),
    "star":     BannerLevel("⭐", "bright_yellow"),
    "sparkles": BannerLevel("✨", "bright_magenta"),
    "ok":       BannerLevel("✅", "bright_green"),
    "ko":       BannerLevel("❌", "bright_red"),
}


LevelSpec = Union[str, BannerLevel]


def _resolve_level(level: LevelSpec) -> BannerLevel:
    if isinstance(level, BannerLevel):
        return level
    if isinstance(level, str):
        if level in LEVELS:
            return LEVELS[level]
        # Treat unknown strings as a literal emoji with neutral color.
        return BannerLevel(level, "bright_white")
    raise TypeError(f"level must be a key, BannerLevel, or emoji string, got {type(level).__name__}")


def _terminal_columns(settings: Settings) -> int:
    try:
        cols = shutil.get_terminal_size(
            fallback=(settings.layout.fallback_terminal_width, 24)
        ).columns
    except OSError:
        cols = settings.layout.fallback_terminal_width
    return max(cols, 20)


def _render_emoji_row(emoji: str, unit_w: int, total_w: int) -> str:
    """A row of `emoji ` repeated to fit `total_w` columns."""
    n = max(1, total_w // unit_w)
    row = (emoji + " ") * n
    # The trailing space is harmless and keeps the visible width predictable.
    return row.rstrip()


def _render_banner_line(
    lvl: BannerLevel,
    message: str,
    *,
    total_w: int,
    emoji_w: int,
    msg_pad: int,
    use_color: bool,
) -> str:
    unit_w = emoji_w + 1  # emoji + 1 space separator
    if not message:
        return _render_emoji_row(lvl.emoji, unit_w, total_w)

    pad = " " * msg_pad
    msg_styled = stylize(f"{pad}{message}{pad}", lvl.color, enabled=use_color)
    msg_w = visible_len(msg_styled)

    if msg_w >= total_w:
        return msg_styled  # message alone is wider than the terminal

    remaining = total_w - msg_w
    left_w = remaining // 2
    right_w = remaining - left_w
    left_units = max(1, left_w // unit_w)
    right_units = max(1, right_w // unit_w)
    left = (lvl.emoji + " ") * left_units
    right = (lvl.emoji + " ") * right_units

    used = left_units * unit_w + msg_w + right_units * unit_w
    leftover = max(0, total_w - used)
    left_extra = leftover // 2
    right_extra = leftover - left_extra
    return left + " " * left_extra + msg_styled + " " * right_extra + right.rstrip()


def print_banner(
    message: str = "",
    level: LevelSpec = "info",
    *,
    style: str = "line",
    settings: Optional[Settings] = None,
    file=None,
    silent: bool = False,
) -> str:
    """Print an emoji banner across the terminal.

    Args:
        message: text to center inside the banner. Empty string → divider only.
        level: one of `LEVELS` keys (`"info"`, `"warning"`, `"error"`, …),
            a `BannerLevel`, or a raw emoji string.
        style: `"line"` (single row, default) or `"sandwich"` (emoji row,
            message row, emoji row — for really loud announcements).

    Returns:
        The rendered string (with ANSI). Pass `silent=True` to suppress
        stdout output and just receive the string.
    """
    s = settings or DEFAULT
    lvl = _resolve_level(level)
    total_w = _terminal_columns(s)
    emoji_w = s.layout.banner_emoji_width
    msg_pad = s.layout.banner_message_padding

    if style == "sandwich":
        bar = _render_banner_line(
            lvl, "", total_w=total_w, emoji_w=emoji_w, msg_pad=msg_pad, use_color=s.use_color
        )
        if message:
            msg_styled = stylize(message, lvl.color, enabled=s.use_color)
            msg_w = visible_len(msg_styled)
            left = max(0, (total_w - msg_w) // 2)
            mid = " " * left + msg_styled
            output = "\n".join([bar, mid, bar])
        else:
            output = bar
    elif style == "line":
        output = _render_banner_line(
            lvl, message, total_w=total_w, emoji_w=emoji_w,
            msg_pad=msg_pad, use_color=s.use_color,
        )
    else:
        raise ValueError(f"style must be 'line' or 'sandwich', got {style!r}")

    if not silent:
        stream = file or sys.stdout
        stream.write(output + "\n")
        stream.flush()
    return output
