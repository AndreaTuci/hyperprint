"""Exception walking, structured extraction, and pretty rendering.

The flow is:
    1. `_build_chain(exc, settings)` walks `__cause__` / `__context__` and
       turns each exception into a structured `ExceptionInfo`.
    2. `_render_chain(chain, settings)` produces the colored ANSI block.
    3. `build_report(exc, settings)` packages everything (structured data,
       rendered output, plain traceback, fingerprint) into an
       `ExceptionReport` for callers to inspect or persist.
"""

import datetime
import hashlib
import linecache
import os
import sys
import sysconfig
import traceback as _tb
from types import FrameType, TracebackType
from typing import Optional

from .ansi import stylize, visible_len, pad_visible
from .render import Block, render_value
from .frame import frame, RULE, content_available_width
from .report import ExceptionInfo, ExceptionReport, FrameInfo, LinkKind
from .settings import Settings


_STDLIB_PATHS = tuple(
    p for p in {sysconfig.get_paths().get("stdlib"), sysconfig.get_paths().get("platstdlib")}
    if p
)

_CAUSE_LINK = "The above exception was the direct cause of the following exception:"
_CONTEXT_LINK = "During handling of the above exception, another exception occurred:"


def _is_stdlib(path: str) -> bool:
    return any(path.startswith(p) for p in _STDLIB_PATHS) or "site-packages" in path


def _safe_repr(value, limit: int) -> str:
    try:
        text = repr(value)
    except Exception as e:  # repr can raise for broken __repr__
        return f"<unreprable: {type(e).__name__}: {e}>"
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _walk_frames(tb: Optional[TracebackType]):
    while tb is not None:
        yield tb.tb_frame, tb.tb_lineno
        tb = tb.tb_next


# ----- structured extraction ------------------------------------------------


def _build_frame_info(frame_obj: FrameType, lineno: int, settings: Settings) -> FrameInfo:
    code = frame_obj.f_code
    source = linecache.getline(code.co_filename, lineno).rstrip("\n") or None

    flt = settings.layout.locals_filter
    raw = frame_obj.f_locals
    if flt is not None:
        raw = {k: v for k, v in raw.items() if flt(k, v)}

    cap = settings.layout.locals_max_repr
    locals_repr = {k: _safe_repr(v, cap) for k, v in raw.items()}

    return FrameInfo(
        filename=code.co_filename,
        lineno=lineno,
        function=code.co_name,
        source_line=source,
        locals=dict(raw),
        locals_repr=locals_repr,
    )


def _build_exception_info(exc: BaseException, settings: Settings) -> ExceptionInfo:
    frames_iter = _walk_frames(exc.__traceback__)
    frames = [_build_frame_info(f, l, settings) for f, l in frames_iter]
    if settings.layout.skip_stdlib_frames:
        filtered = [fi for fi in frames if not _is_stdlib(fi.filename)]
        frames = filtered or frames
    return ExceptionInfo(
        type_name=type(exc).__name__,
        module=type(exc).__module__,
        message=str(exc),
        frames=frames,
    )


def _build_chain(exc: BaseException, settings: Settings) -> list[ExceptionInfo]:
    """Return the chain ordered oldest → newest, with link annotations."""
    raw_chain: list[BaseException] = []
    current: Optional[BaseException] = exc
    while current is not None:
        raw_chain.append(current)
        if current.__cause__ is not None:
            current = current.__cause__
        elif current.__context__ is not None and not current.__suppress_context__:
            current = current.__context__
        else:
            current = None
    raw_chain.reverse()  # oldest first

    infos = [_build_exception_info(e, settings) for e in raw_chain]
    for i, e in enumerate(raw_chain[:-1]):
        nxt = raw_chain[i + 1]
        link: Optional[LinkKind] = None
        if nxt.__cause__ is e:
            link = "cause"
        elif nxt.__context__ is e and not nxt.__suppress_context__:
            link = "context"
        infos[i].link_to_next = link
    return infos


# ----- rendering ------------------------------------------------------------


def _render_code_context(filename: str, lineno: int, settings: Settings) -> Block:
    p = settings.palette
    use = settings.use_color
    ctx = settings.layout.code_context_lines
    start = max(1, lineno - ctx)
    end = lineno + ctx
    lines: list[str] = []
    width = len(str(end))
    for n in range(start, end + 1):
        src = linecache.getline(filename, n)
        if not src:
            continue
        src = src.rstrip("\n")
        marker = "▸" if n == lineno else " "
        gutter = f"{marker} {str(n).rjust(width)} │ "
        if n == lineno:
            row = stylize(f"{gutter}{src}", p.code_highlight, enabled=use)
        else:
            row = stylize(gutter, p.frame_lineno, enabled=use) + stylize(src, p.code_normal, enabled=use)
        lines.append(row)
    return Block(lines or [stylize("(source unavailable)", p.none, enabled=use)])


def _render_locals_block(frame_info: FrameInfo, settings: Settings, available: Optional[int]) -> Block:
    p = settings.palette
    use = settings.use_color
    if not frame_info.locals:
        return Block([stylize("(no user locals)", p.none, enabled=use)])

    name_w = max(visible_len(str(k)) for k in frame_info.locals)
    gap = " " * (settings.layout.inner_padding + 1)
    indent = " " * (name_w + len(gap))
    value_avail = (available - name_w - len(gap)) if available is not None else None
    lines: list[str] = []
    for name, value in frame_info.locals.items():
        name_styled = stylize(pad_visible(str(name), name_w), p.locals_name, enabled=use)
        sub = render_value(value, settings, value_avail)
        if not sub.lines:
            lines.append(f"{name_styled}{gap}")
            continue
        lines.append(f"{name_styled}{gap}{sub.lines[0]}")
        for rest in sub.lines[1:]:
            lines.append(f"{indent}{rest}")
    return Block(lines)


def _render_exception_lines(
    info: ExceptionInfo,
    settings: Settings,
    *,
    show_locals_on_last: bool,
    available: Optional[int],
) -> list[str]:
    p = settings.palette
    use = settings.use_color
    msg = info.message or "(no message)"
    lines: list[str] = [
        stylize(info.type_name, p.exception_type, enabled=use)
        + "  "
        + stylize(msg, p.exception_message, enabled=use)
    ]

    last_idx = len(info.frames) - 1
    for i, fi in enumerate(info.frames):
        lines.append(RULE)
        path = os.path.relpath(fi.filename) if os.path.isabs(fi.filename) else fi.filename
        head = (
            stylize(f"#{i} ", p.border, enabled=use)
            + stylize(path, p.frame_path, enabled=use)
            + stylize(":", p.border, enabled=use)
            + stylize(str(fi.lineno), p.frame_lineno, enabled=use)
            + "  "
            + stylize(f"in {fi.function}", p.frame_func, enabled=use)
        )
        ctx = _render_code_context(fi.filename, fi.lineno, settings)
        lines.extend([head, "", *ctx.lines])

        emit_locals = show_locals_on_last and (
            i == last_idx
            or not settings.layout.show_locals_only_on_last_frame
        )
        if emit_locals:
            loc = _render_locals_block(fi, settings, available)
            sep = stylize("locals", p.locals_title, enabled=use)
            lines += ["", sep, *loc.lines]

    return lines


def _render_chain(chain: list[ExceptionInfo], settings: Settings) -> str:
    p = settings.palette
    use = settings.use_color
    avail = content_available_width(settings)
    last_idx = len(chain) - 1
    body: list[str] = []
    for i, info in enumerate(chain):
        show_locals = (i == last_idx) or not settings.layout.show_locals_only_on_last_frame
        if i > 0:
            body.append(RULE)
        body.extend(_render_exception_lines(info, settings, show_locals_on_last=show_locals, available=avail))
        if info.link_to_next:
            link_msg = _CAUSE_LINK if info.link_to_next == "cause" else _CONTEXT_LINK
            body.append(RULE)
            body.append(stylize(link_msg, p.exception_message, enabled=use))
    return frame(Block(body), "Traceback", settings)


# ----- public API helpers ---------------------------------------------------


def _fingerprint(chain: list[ExceptionInfo]) -> str:
    """12-hex-char hash of the last exception's identity + frame signature.

    Stable across runs as long as the failing call sites and exception type
    stay the same — suitable for grouping similar errors in a dashboard.
    """
    last = chain[-1]
    parts = [last.qualified_name]
    for f in last.frames:
        parts.append(f"{os.path.basename(f.filename)}:{f.function}:{f.lineno}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:12]


def fallback_text(exc: BaseException) -> str:
    """Plain `traceback.format_exception` output, no colors, no locals."""
    return "".join(_tb.format_exception(type(exc), exc, exc.__traceback__))


def build_report(exc: BaseException, settings: Settings) -> ExceptionReport:
    chain = _build_chain(exc, settings)
    rendered = _render_chain(chain, settings)
    return ExceptionReport(
        exception=exc,
        type_name=type(exc).__name__,
        module=type(exc).__module__,
        message=str(exc),
        timestamp=datetime.datetime.now(),
        chain=chain,
        rendered=rendered,
        plain=fallback_text(exc),
        fingerprint=_fingerprint(chain),
    )


def render_current_exception(settings: Settings) -> Optional[ExceptionReport]:
    exc = sys.exc_info()[1]
    if exc is None:
        return None
    return build_report(exc, settings)
