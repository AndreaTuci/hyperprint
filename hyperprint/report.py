"""Structured value objects returned by `print_exception`.

Designed to be useful in real apps: send `.plain` to Sentry / log files,
group by `.fingerprint`, drill into `.last.frames[-1].locals` for the
variables that mattered when the error happened.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, Literal, Optional


LinkKind = Literal["cause", "context"]


@dataclass
class FrameInfo:
    filename: str
    lineno: int
    function: str
    source_line: Optional[str]      # the failing source line (raw, no styling)
    locals: dict[str, Any]          # filtered user locals (live values)
    locals_repr: dict[str, str]     # repr'd + length-capped, safe to serialize


@dataclass
class ExceptionInfo:
    type_name: str
    module: str                     # e.g. "builtins", "myapp.errors"
    message: str
    frames: list[FrameInfo]         # outer-first, raise-site last (Python order)
    link_to_next: Optional[LinkKind] = None  # how this links to the next exc

    @property
    def qualified_name(self) -> str:
        if self.module in ("builtins", "__main__"):
            return self.type_name
        return f"{self.module}.{self.type_name}"


@dataclass
class ExceptionReport:
    exception: BaseException
    type_name: str
    module: str
    message: str
    timestamp: datetime.datetime
    chain: list[ExceptionInfo] = field(repr=False)  # oldest → newest
    rendered: str = field(repr=False)               # ANSI-colored output
    plain: str = field(repr=False)                  # plain text (no ANSI)
    fingerprint: str                                # short hash for grouping

    @property
    def last(self) -> ExceptionInfo:
        """The current (most recently raised) exception in the chain."""
        return self.chain[-1]

    @property
    def root_cause(self) -> ExceptionInfo:
        """The original exception that started the chain."""
        return self.chain[0]

    @property
    def is_chained(self) -> bool:
        return len(self.chain) > 1

    def __str__(self) -> str:
        return self.rendered
