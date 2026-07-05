"""Default-deny allowlist for the free-text ``extra_flags`` field (ADR-0019).

Power users pass arbitrary KLEE flags as free text. Rather than deny known-bad
flags (whack-a-mole), only flags vetted into ``ALLOWED_FLAGS`` are permitted, each
with a value policy. The list grows only as a flag is reviewed in. Flags we manage
ourselves (``--output-dir``, ``--max-time``, ``--external-calls``, ...) are absent
on purpose, so a user can neither override our contract nor loosen isolation.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Protocol


class FlagError(ValueError):
    """An extra flag is not on the allowlist or carries an invalid value."""


class FlagPolicy(Protocol):
    def check(self, flag: str, value: str | None) -> None: ...


_BOOL_VALUES = {"true", "false", "1", "0"}


@dataclass(frozen=True)
class BoolPolicy:
    """Bare (``--optimize``) or an explicit ``=true|false``, for on/off flags."""

    def check(self, flag: str, value: str | None) -> None:
        if value is not None and value.lower() not in _BOOL_VALUES:
            raise FlagError(f"{flag} takes true or false, got {value!r}")


@dataclass(frozen=True)
class IntPolicy:
    lo: int
    hi: int

    def check(self, flag: str, value: str | None) -> None:
        if value is None:
            raise FlagError(f"{flag} needs a value, for example {flag}={self.lo}")
        try:
            n = int(value)
        except ValueError:
            raise FlagError(f"{flag} takes a whole number, got {value!r}") from None
        if not self.lo <= n <= self.hi:
            raise FlagError(f"{flag} must be between {self.lo} and {self.hi}, got {n}")


@dataclass(frozen=True)
class EnumPolicy:
    values: frozenset[str]

    def check(self, flag: str, value: str | None) -> None:
        if value is None or value not in self.values:
            allowed = ", ".join(sorted(self.values))
            raise FlagError(f"{flag} must be one of: {allowed}")


_BOOL = BoolPolicy()

_SEARCH_HEURISTICS = frozenset(
    {
        "dfs",
        "bfs",
        "random-state",
        "random-path",
        "nurs:covnew",
        "nurs:cpicnt",
        "nurs:depth",
        "nurs:icnt",
        "nurs:md2u",
        "nurs:qc",
        "nurs:rp",
    }
)

ALLOWED_FLAGS: dict[str, FlagPolicy] = {
    "--optimize": _BOOL,
    "--emit-all-errors": _BOOL,
    "--only-output-states-covering-new": _BOOL,
    "--use-cex-cache": _BOOL,
    "--use-branch-cache": _BOOL,
    "--use-independent-solver": _BOOL,
    "--use-forked-solver": _BOOL,
    "--max-forks": IntPolicy(1, 1_000_000),
    "--max-depth": IntPolicy(1, 1_000_000),
    "--max-instructions": IntPolicy(1, 1_000_000_000),
    "--search": EnumPolicy(_SEARCH_HEURISTICS),
    "--solver-backend": EnumPolicy(frozenset({"stp", "z3"})),
}


def validate_extra_flags(raw: str) -> str:
    """Return ``raw`` unchanged if every token is an allowed flag with a valid value.

    Raises :class:`FlagError` otherwise. The runner re-tokenises the string when it
    builds the klee command, so this validates the string without rewriting it.
    """
    try:
        tokens = shlex.split(raw)
    except ValueError as e:
        raise FlagError(f"could not parse flags: {e}") from None
    for token in tokens:
        flag, sep, value = token.partition("=")
        policy = ALLOWED_FLAGS.get(flag)
        if policy is None:
            raise FlagError(f"{flag} is not an allowed flag")
        policy.check(flag, value if sep else None)
    return raw
