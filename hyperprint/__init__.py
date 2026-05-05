"""hyperprint — pretty structured logging without external dependencies.

Public API:
    print_info(data, heading=None, *, settings=None, file=None, silent=False) -> str
        Returns the rendered string (with ANSI). Use silent=True to skip stdout.
    print_exception(*, settings=None, file=None, silent=False) -> ExceptionReport | None
        Returns a structured report you can store, send to Sentry, or
        re-render. Returns None if called outside an `except` block.

    Settings, Palette, Glyphs, Layout, ASCII_GLYPHS — visual configuration
    ExceptionReport, ExceptionInfo, FrameInfo — returned by print_exception
"""

import sys

__version__ = "0.1.0"

from .settings import Settings, Palette, Glyphs, Layout, ASCII_GLYPHS, DEFAULT
from .render import render_value
from .frame import frame, content_available_width
from .exception import build_report, fallback_text
from .report import ExceptionReport, ExceptionInfo, FrameInfo
from .ansi import strip_ansi


__all__ = [
    "__version__",
    "print_info",
    "print_exception",
    "Settings",
    "Palette",
    "Glyphs",
    "Layout",
    "ASCII_GLYPHS",
    "ExceptionReport",
    "ExceptionInfo",
    "FrameInfo",
    "strip_ansi",
]


def _stream(file):
    return file or sys.stdout


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
    s = settings or DEFAULT
    block = render_value(data, s, available=content_available_width(s))
    rendered = frame(block, heading, s)
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
    s = settings or DEFAULT
    exc = sys.exc_info()[1]
    if exc is None:
        return None

    try:
        report = build_report(exc, s)
    except Exception as render_err:
        # If our own renderer blows up, never swallow the original error.
        stream = _stream(file)
        stream.write(f"hyperprint: failed to render exception ({render_err})\n")
        stream.write(fallback_text(exc))
        stream.flush()
        return None

    if not silent:
        stream = _stream(file)
        stream.write(report.rendered + "\n")
        stream.flush()
    return report
