"""Centralized configuration: colors, glyphs, layout knobs.

Every visual choice in hyperprint flows through this module so that
restyling the output never requires touching the renderers.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


def _default_locals_filter(name: str, value: Any) -> bool:
    """Hide dunders, modules, callables, and classes — keep user data."""
    import types

    if name.startswith("__") and name.endswith("__"):
        return False
    if isinstance(value, types.ModuleType):
        return False
    if isinstance(value, (types.FunctionType, types.BuiltinFunctionType,
                         types.MethodType, types.BuiltinMethodType,
                         types.LambdaType)):
        return False
    if isinstance(value, type):
        return False
    return True


@dataclass(frozen=True)
class Palette:
    key: str = "dim"
    nested_key: str = "bold yellow"
    heading: str = "bold bright_white on blue"
    border: str = "bright_black"

    string: str = "bright_blue"
    number: str = "bright_green"
    date: str = "bright_cyan"
    bool_true: str = "bright_green"
    bool_false: str = "bright_red"
    none: str = "bright_black italic"
    sequence: str = "magenta"
    fallback: str = "bright_red"

    exception_title: str = "bold bright_white on red"
    exception_type: str = "bold bright_red"
    exception_message: str = "bright_red"
    frame_path: str = "cyan"
    frame_lineno: str = "bright_yellow"
    frame_func: str = "bright_white"
    code_normal: str = "white"
    code_highlight: str = "bold bright_white on red"
    locals_title: str = "bold bright_white on bright_black"
    locals_name: str = "bright_yellow"
    locals_value: str = "bright_white"


@dataclass(frozen=True)
class Glyphs:
    """Box-drawing characters. Swap to ASCII fallbacks if needed."""

    h: str = "─"   # ─
    v: str = "│"   # │
    tl: str = "╭"  # ╭
    tr: str = "╮"  # ╮
    bl: str = "╰"  # ╰
    br: str = "╯"  # ╯
    tee_d: str = "┬"  # ┬
    tee_u: str = "┴"  # ┴
    tee_r: str = "├"  # ├
    tee_l: str = "┤"  # ┤
    cross: str = "┼"  # ┼

    bullet: str = "·"   # ·
    arrow: str = "→"    # →
    nest: str = "╶"     # ╶


ASCII_GLYPHS = Glyphs(
    h="-", v="|", tl="+", tr="+", bl="+", br="+",
    tee_d="+", tee_u="+", tee_r="+", tee_l="+", cross="+",
    bullet="*", arrow="->", nest="-",
)


@dataclass(frozen=True)
class Layout:
    inner_padding: int = 1
    nest_indent: int = 2
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    sequence_separator: str = ", "
    code_context_lines: int = 2
    skip_stdlib_frames: bool = False
    locals_max_repr: int = 200

    # N1: never produce a box narrower than the terminal.
    fit_terminal_width: bool = True
    # Fallback when stdout is not a TTY (e.g. piped output).
    fallback_terminal_width: int = 100

    # N3: filter locals + collapse locals to the innermost frame only.
    locals_filter: Optional[Callable[[str, Any], bool]] = _default_locals_filter
    show_locals_only_on_last_frame: bool = True

    # Banners. Most pictographic emoji render 2 columns wide on monospace
    # terminals; tune if your shell renders them differently.
    banner_emoji_width: int = 2
    banner_message_padding: int = 2


@dataclass(frozen=True)
class Settings:
    palette: Palette = field(default_factory=Palette)
    glyphs: Glyphs = field(default_factory=Glyphs)
    layout: Layout = field(default_factory=Layout)
    use_color: bool = True


DEFAULT = Settings()
