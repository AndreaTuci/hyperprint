# hyperprint

[![PyPI version](https://img.shields.io/pypi/v/hyperprint.svg)](https://pypi.org/project/hyperprint/)
[![Python versions](https://img.shields.io/pypi/pyversions/hyperprint.svg)](https://pypi.org/project/hyperprint/)
[![License: MIT](https://img.shields.io/pypi/l/hyperprint.svg)](https://github.com/AndreaTuci/hyperprint/blob/main/LICENSE)

Pretty structured printing for Python — colored, framed, never truncated.
Zero runtime dependencies.

`hyperprint` is a small drop-in utility for inspecting data structures and
exceptions in real applications. Output is a single self-contained box drawn
with Unicode glyphs, dimensioned to the terminal but always large enough to
fit the content. Nested data is rendered as aligned columns instead of
nested ASCII tables, so deeply structured payloads stay readable.

## What's in the box

| function | what it does |
| --- | --- |
| `print_info(data, heading=None)` | structured data → framed colored box |
| `print_exception()` | the active exception → framed traceback + `ExceptionReport` |
| `print_banner(message, level=…)` | emoji bar across the terminal — divider or attention mark |
| `print_title(text, color=…)` | 5-row block-letter ASCII headline |

All four functions write synchronously to stdout (so they stay in order with
plain `print()` calls) and return their rendered string for further use.

## Why

Existing pretty-print libraries either truncate long values or buffer their
output in a way that interleaves badly with regular `print()` calls.
`hyperprint` writes synchronously to `stdout` (so its lines never appear out
of order with surrounding logs) and never abbreviates content with `…`.

It also offers a colored `print_exception` that:

- Walks the full `__cause__` / `__context__` chain.
- Shows source context with the failing line highlighted.
- Filters frame locals (no module / function / dunder noise — only what your
  code declared).
- Returns a structured `ExceptionReport` you can persist, fingerprint, or
  forward to your error tracker.

## Install

```bash
pip install hyperprint
```

Requires Python 3.10+. No runtime dependencies.

```python
# Curated public surface — safe to star-import:
from hyperprint import *
```

## Usage

### Print structured data

```python
import datetime
from hyperprint import print_info

print_info(
    {
        "user": "alice",
        "joined": datetime.date(2024, 5, 1),
        "roles": ["admin", "editor"],
        "stats": {"logins": 1287, "last_login": datetime.date.today()},
    },
    heading="Account",
)
```

`print_info` returns the rendered string (with ANSI escapes). Pass
`silent=True` to build the string without writing to stdout.

### Print an exception

```python
from hyperprint import print_exception

try:
    do_work()
except Exception:
    report = print_exception()
```

`print_exception` returns an `ExceptionReport` (or `None` if called outside
an `except` block) with everything you typically need:

| field | description |
| --- | --- |
| `.exception` | the live exception object |
| `.type_name`, `.module`, `.message` | basic identity |
| `.timestamp` | when the report was captured |
| `.chain` | `list[ExceptionInfo]` ordered oldest → newest |
| `.last`, `.root_cause`, `.is_chained` | shortcuts |
| `.rendered` | the colored ANSI output (also `str(report)`) |
| `.plain` | stdlib-style traceback (no colors) — perfect for log files / Sentry |
| `.fingerprint` | 12-hex hash of the failure signature, stable across runs |

Each `ExceptionInfo` carries a list of `FrameInfo` (filename, lineno,
function, source line, and filtered locals — both live values and
length-capped reprs).

```python
try:
    do_work()
except Exception:
    report = print_exception()
    if report:
        my_logger.error(report.plain, extra={"err.id": report.fingerprint})
```

### Block-letter titles

For announcement headlines, render text as a 5-row block-letter title:

```python
from hyperprint import print_title

print_title("HYPERPRINT", color="bright_magenta", align="center")
print_title("DEPLOY", color="bold bright_red")
```

Built-in font covers `A-Z`, `0-9`, and common punctuation. Letters are
uppercased automatically; unknown characters become blanks. `align` is
`"left"`, `"center"`, or `"right"` relative to the terminal width.

### Emoji banners

For lines that really need to jump out of the log stream:

```python
from hyperprint import print_banner

print_banner("Deploy started", level="rocket")        # 🚀 …  Deploy started  … 🚀
print_banner(level="warning")                          # 🟡 divider, full width
print_banner("PROD INCIDENT", level="critical", style="sandwich")
```

Built-in levels: `info` 💡, `success` ✅, `warning` 🟡, `error` 🚩,
`critical` 🚨, `debug` 🐞, `note` 📝, `fire` 🔥, `rocket` 🚀, `party` 🎉,
`lock` 🔒, `star` ⭐, `sparkles` ✨, `ok` ✅, `ko` ❌. Or pass any emoji
string directly as `level`, or build your own:

```python
from hyperprint import print_banner, BannerLevel

mine = BannerLevel("🦄", "bright_magenta")
print_banner("Release shipped", level=mine)
```

## Customization

All visual choices flow through a single `Settings` object.

```python
from hyperprint import print_info, Settings, Palette, Layout, ASCII_GLYPHS

custom = Settings(
    palette=Palette(string="green", date="bright_magenta"),
    layout=Layout(
        date_format="%d/%m/%Y",
        show_locals_only_on_last_frame=False,  # show locals on every frame
        fit_terminal_width=True,
    ),
)
print_info(data, heading="Custom", settings=custom)

# For terminals without Unicode support:
ascii_settings = Settings(glyphs=ASCII_GLYPHS)
```

### Local filtering

By default the locals you see in an exception are restricted to user-declared
variables (no dunders, modules, functions, or classes). You can override the
filter with any callable:

```python
from hyperprint import Settings, Layout

# only keep names starting with "user_"
s = Settings(layout=Layout(locals_filter=lambda name, value: name.startswith("user_")))

# disable filtering — show everything Python has in the frame
s = Settings(layout=Layout(locals_filter=None))
```

## Demo

A self-contained example covering all four functions — deeply nested data
with long strings, a chained exception, banners, and a title — lives in
[`examples/demo.py`](examples/demo.py):

```bash
git clone https://github.com/AndreaTuci/hyperprint
cd hyperprint
uv venv && source .venv/bin/activate
uv pip install -e .
python examples/demo.py
```

## Versioning

`hyperprint` follows [SemVer](https://semver.org/). Versions are released by
tagging on GitHub; the [PyPI page](https://pypi.org/project/hyperprint/)
always points at the latest stable release.

## License

MIT — see [LICENSE](LICENSE).
