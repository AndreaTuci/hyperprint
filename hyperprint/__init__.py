"""hyperprint — pretty structured logging without external dependencies.

Public API (everything in `__all__` is what `from hyperprint import *` exposes):

    print_info(data, heading=None, *, settings=None, file=None, silent=False) -> str
        Returns the rendered string (with ANSI). Use silent=True to skip stdout.
    print_exception(*, settings=None, file=None, silent=False) -> ExceptionReport | None
        Returns a structured report you can store, send to Sentry, or
        re-render. Returns None if called outside an `except` block.
    print_banner(message="", level="info", *, style="line", ...) -> str
        Emoji banner / divider. See banner.LEVELS for built-in keys.
    print_title(text, color="bright_white", *, align="left", ...) -> str
        5-row block-letter headline using the embedded font.

    Settings, Palette, Glyphs, Layout, ASCII_GLYPHS — visual configuration
    ExceptionReport, ExceptionInfo, FrameInfo — returned by print_exception
    BannerLevel, BANNER_LEVELS — banner customization
    strip_ansi — utility to remove ANSI codes from a rendered string

Internal helpers are imported under `_`-prefixed aliases so they don't
pollute the public namespace.
"""

import sys as _sys

__version__ = "0.2.0"

from .settings import Settings, Palette, Glyphs, Layout, ASCII_GLYPHS
from .settings import DEFAULT as _DEFAULT
from .render import render_value as _render_value
from .frame import frame as _frame, content_available_width as _content_available_width
from .exception import build_report as _build_report, fallback_text as _fallback_text
from .report import ExceptionReport, ExceptionInfo, FrameInfo
from .banner import print_banner, BannerLevel, LEVELS as BANNER_LEVELS
from .title import print_title
from .ansi import strip_ansi


__all__ = [
    "__version__",
    # functions
    "print_info",
    "print_exception",
    "print_banner",
    "print_title",
    # configuration
    "Settings",
    "Palette",
    "Glyphs",
    "Layout",
    "ASCII_GLYPHS",
    # exception data
    "ExceptionReport",
    "ExceptionInfo",
    "FrameInfo",
    # banner data
    "BannerLevel",
    "BANNER_LEVELS",
    # utilities
    "strip_ansi",
]


def _stream(file):
    return file or _sys.stdout


def print_info(
    data,
    heading: str | None = None,
    *,
    settings: Settings | None = None,
    file=None,
    silent: bool = False,
) -> str:
    """Print structured data inside a framed block.

    Returns the rendered string (with ANSI). Pass `silent=True` to build
    the string without writing to stdout — useful for tests or when you
    want to forward the output elsewhere.
    """
    s = settings or _DEFAULT
    block = _render_value(data, s, available=_content_available_width(s))
    rendered = _frame(block, heading, s)
    if not silent:
        stream = _stream(file)
        stream.write(rendered + "\n")
        stream.flush()
    return rendered


def print_exception(
    *,
    settings: Settings | None = None,
    file=None,
    silent: bool = False,
) -> ExceptionReport | None:
    """Pretty-print the current exception. Must be called from inside `except`.

    Returns an `ExceptionReport` you can use for logging / error tracking,
    or `None` if there is no active exception. The report carries:
      - `.rendered` (ANSI), `.plain` (stdlib-style traceback)
      - `.chain` of `ExceptionInfo` (oldest → newest)
      - `.last`, `.root_cause`, `.is_chained`
      - `.fingerprint` (12-hex hash for grouping similar errors)
      - `.timestamp`, `.exception` (live object), `.type_name`, `.module`
    """
    s = settings or _DEFAULT
    exc = _sys.exc_info()[1]
    if exc is None:
        return None

    try:
        report = _build_report(exc, s)
    except Exception as render_err:
        # If our own renderer blows up, never swallow the original error.
        stream = _stream(file)
        stream.write(f"hyperprint: failed to render exception ({render_err})\n")
        stream.write(_fallback_text(exc))
        stream.flush()
        return None

    if not silent:
        stream = _stream(file)
        stream.write(report.rendered + "\n")
        stream.flush()
    return report
