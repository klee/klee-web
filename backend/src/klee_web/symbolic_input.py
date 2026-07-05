"""Structured symbolic-input specs and their rendering into KLEE POSIX-runtime args.

The three specs (--sym-stdin, --sym-files, --sym-args) are POSIX-runtime options
that go AFTER the bitcode, unlike the prefix flags. render_posix_args builds the
token string the backend hands to the runner (KLEE_POSIX_ARGS); the entrypoint
shlex-splits it and appends it after the bitcode.

These models live apart from models.py so KleeFlags can import them without a
cycle: render_posix_args takes the sub-models, never KleeFlags.
"""

import shlex
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class SymStdin(BaseModel):
    size: Annotated[int, Field(ge=1, le=256)]  # symbolic stdin bytes


class SymFiles(BaseModel):
    count: Annotated[int, Field(ge=1, le=10)]  # number of symbolic files
    size: Annotated[int, Field(ge=1, le=256)]  # bytes per file


class SymArgs(BaseModel):
    count_min: Annotated[int, Field(ge=0, le=10)]  # fewest symbolic argv entries
    count_max: Annotated[int, Field(ge=1, le=10)]  # most symbolic argv entries
    length: Annotated[int, Field(ge=1, le=100)]  # max chars per entry

    @model_validator(mode="after")
    def _max_not_below_min(self) -> "SymArgs":
        if self.count_max < self.count_min:
            raise ValueError("count_max must be >= count_min")
        return self


def render_posix_args(
    sym_files: SymFiles | None = None,
    sym_args: SymArgs | None = None,
    sym_stdin: SymStdin | None = None,
) -> str:
    parts: list[str] = []
    if sym_files is not None:
        parts += ["--sym-files", str(sym_files.count), str(sym_files.size)]
    if sym_args is not None:
        parts += [
            "--sym-args",
            str(sym_args.count_min),
            str(sym_args.count_max),
            str(sym_args.length),
        ]
    if sym_stdin is not None:
        parts += ["--sym-stdin", str(sym_stdin.size)]
    return shlex.join(parts)
