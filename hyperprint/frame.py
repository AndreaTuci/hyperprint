"""Draw a box around a block of pre-styled lines.

The box width is computed from the widest visible line plus optional
heading; nothing is ever truncated. With `fit_terminal_width`, the box
also grows to fill the terminal so it never looks narrower than the
shell window.
"""

import shutil

from .ansi import stylize, visible_len, pad_visible
from .render import Block
from .settings import Settings


# Sentinel: any line in a Block equal to RULE becomes an in-box tee-rule
# `├──────┤` instead of the usual `│ … │`, used to visually divide sections.
RULE = "\x00hyperprint:rule\x00"


def _terminal_width(settings: Settings) -> int:
    try:
        cols = shutil.get_terminal_size(
            fallback=(settings.layout.fallback_terminal_width, 24)
        ).columns
    except OSError:
        cols = settings.layout.fallback_terminal_width
    return max(cols, 20)


def content_available_width(settings: Settings) -> int | None:
    """Visible columns left for content inside a top-level box.

    Returns None when the box is allowed to grow with the content
    (so wrapping is disabled).
    """
    if not settings.layout.fit_terminal_width:
        return None
    pad = settings.layout.inner_padding
    return _terminal_width(settings) - 2 - 2 * pad


def frame(block: Block, heading: str | None, settings: Settings) -> str:
    g = settings.glyphs
    p = settings.palette
    use = settings.use_color
    pad = settings.layout.inner_padding

    content_w = max(block.width, visible_len(heading or ""))
    inner = content_w + pad * 2

    if settings.layout.fit_terminal_width:
        # Box outer width = inner + 2 borders. Match the terminal at minimum.
        inner = max(inner, _terminal_width(settings) - 2)

    h = stylize(g.h * inner, p.border, enabled=use)
    v = stylize(g.v, p.border, enabled=use)
    tl = stylize(g.tl, p.border, enabled=use)
    tr = stylize(g.tr, p.border, enabled=use)
    bl = stylize(g.bl, p.border, enabled=use)
    br = stylize(g.br, p.border, enabled=use)
    tee_r = stylize(g.tee_r, p.border, enabled=use)
    tee_l = stylize(g.tee_l, p.border, enabled=use)

    out: list[str] = []
    out.append(f"{tl}{h}{tr}")

    if heading:
        head_padded = pad_visible(stylize(f" {heading} ", p.heading, enabled=use), inner)
        out.append(f"{v}{head_padded}{v}")
        out.append(f"{tee_r}{h}{tee_l}")

    pad_str = " " * pad
    for line in block.lines:
        if line == RULE:
            out.append(f"{tee_r}{h}{tee_l}")
            continue
        body = pad_visible(line, inner - pad * 2)
        out.append(f"{v}{pad_str}{body}{pad_str}{v}")

    out.append(f"{bl}{h}{br}")
    return "\n".join(out)
