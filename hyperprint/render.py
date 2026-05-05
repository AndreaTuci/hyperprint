"""Convert arbitrary Python data into a tree of styled lines.

The renderer never truncates. When `available` is supplied, long string
scalars and oversized flat sequences wrap onto multiple lines so the
caller can frame the output without overflowing the terminal.
"""

import datetime
import textwrap
from dataclasses import dataclass

from .ansi import stylize, visible_len, pad_visible
from .settings import Settings


@dataclass
class Block:
    lines: list[str]

    @property
    def width(self) -> int:
        return max((visible_len(l) for l in self.lines), default=0)


def _wrap_plain(text: str, width: int) -> list[str]:
    """Wrap raw (unstyled) text to `width`. Long words are broken."""
    if width <= 0:
        return [text]
    if not text:
        return [""]
    if len(text) <= width:
        return [text]
    out = textwrap.wrap(
        text,
        width=width,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=False,
        drop_whitespace=False,
    )
    return out or [text]


def _fmt_scalar(value, settings: Settings, available: int | None) -> list[str]:
    """Render a scalar as one or more styled lines.

    Only strings can produce more than one line (when wrapping kicks in).
    """
    p = settings.palette
    use = settings.use_color

    if value is None:
        return [stylize("None", p.none, enabled=use)]
    if isinstance(value, bool):
        spec = p.bool_true if value else p.bool_false
        return [stylize(str(value), spec, enabled=use)]
    if isinstance(value, (int, float)):
        return [stylize(str(value), p.number, enabled=use)]
    if isinstance(value, datetime.datetime):
        return [stylize(value.strftime(settings.layout.datetime_format), p.date, enabled=use)]
    if isinstance(value, datetime.date):
        return [stylize(value.strftime(settings.layout.date_format), p.date, enabled=use)]
    if isinstance(value, str):
        if available and len(value) > available:
            return [stylize(line, p.string, enabled=use) for line in _wrap_plain(value, available)]
        return [stylize(value, p.string, enabled=use)]
    return [stylize(repr(value), p.fallback, enabled=use)]


def _is_flat_sequence(seq) -> bool:
    return all(not isinstance(el, (dict, list, tuple)) for el in seq)


def render_value(value, settings: Settings, available: int | None = None) -> Block:
    """Render a value as a Block. `available` is the visible columns left
    on the current line for this value's first row."""
    if isinstance(value, dict):
        return _render_dict(value, settings, available)
    if isinstance(value, (list, tuple)):
        return _render_sequence(value, settings, available)
    return Block(_fmt_scalar(value, settings, available))


def _greedy_join(parts: list[str], sep: str, available: int | None) -> list[str]:
    """Pack already-styled parts onto lines no wider than `available`."""
    if not available or available <= 0:
        return [sep.join(parts)] if parts else [""]
    sep_w = visible_len(sep)
    out: list[str] = []
    cur: list[str] = []
    cur_w = 0
    for part in parts:
        pw = visible_len(part)
        added = pw + (sep_w if cur else 0)
        if cur and cur_w + added > available:
            out.append(sep.join(cur))
            cur = [part]
            cur_w = pw
        else:
            cur.append(part)
            cur_w += added
    if cur:
        out.append(sep.join(cur))
    return out or [""]


def _render_sequence(seq, settings: Settings, available: int | None) -> Block:
    p = settings.palette
    use = settings.use_color
    if not seq:
        return Block([stylize("[]", p.sequence, enabled=use)])

    if _is_flat_sequence(seq):
        sep = settings.layout.sequence_separator
        # Each scalar is single-line in a flat sequence (no wrap on individual
        # elements; we wrap by breaking the joined line into multiple rows).
        parts = [_fmt_scalar(el, settings, None)[0] for el in seq]
        return Block(_greedy_join(parts, sep, available))

    bullet = settings.glyphs.bullet
    bullet_styled = stylize(bullet, p.sequence, enabled=use)
    indent_w = settings.layout.nest_indent
    indent = " " * indent_w
    sub_avail = (available - indent_w) if available is not None else None
    lines: list[str] = []
    for el in seq:
        sub = render_value(el, settings, sub_avail)
        if not sub.lines:
            continue
        lines.append(f"{bullet_styled} {sub.lines[0]}")
        for rest in sub.lines[1:]:
            lines.append(f"{indent}{rest}")
    return Block(lines)


def _render_dict(data: dict, settings: Settings, available: int | None) -> Block:
    p = settings.palette
    use = settings.use_color
    if not data:
        return Block([stylize("{}", p.fallback, enabled=use)])

    raw_keys = [str(k) for k in data.keys()]
    key_width = max(visible_len(k) for k in raw_keys)
    gap = " " * (settings.layout.inner_padding + 1)
    indent = " " * (key_width + len(gap))
    value_avail = (available - key_width - len(gap)) if available is not None else None

    lines: list[str] = []
    for key, value in data.items():
        key_str = str(key)
        is_nested = isinstance(value, (dict, list, tuple)) and not (
            isinstance(value, (list, tuple)) and _is_flat_sequence(value)
        )
        key_spec = p.nested_key if is_nested else p.key
        key_styled = stylize(pad_visible(key_str, key_width), key_spec, enabled=use)

        sub = render_value(value, settings, value_avail)
        if not sub.lines:
            lines.append(f"{key_styled}{gap}")
            continue
        lines.append(f"{key_styled}{gap}{sub.lines[0]}")
        for rest in sub.lines[1:]:
            lines.append(f"{indent}{rest}")
    return Block(lines)
