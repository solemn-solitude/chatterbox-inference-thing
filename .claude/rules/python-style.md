# Python Style Guide

## Target

Python 3.11+. Use features accordingly.

## Types

- Use union types, never `typing` aliases: `str | None` not `Optional[str]`, `list[str]` not `List[str]`, `dict[str, str]` not `Dict[str, str]`, etc.
- **No `Any`** — not even `dict[str, Any]`. Model the data properly with dataclasses.
- No string forward references (`"ClassName"`). Use real imports.
- No `TYPE_CHECKING`. If there's a circular import, surface it — don't paper over it. Use `from __future__ import annotations` if needed to break cycles.

## Imports

- Absolute imports only — never relative.
- Never import inside functions or classes. The only valid exception is an optional feature with a runtime availability check. Circular imports are an architecture problem, not an import placement problem.
- No `global` keyword.

## Print statements

Multiple lines: use a single multiline string with `textwrap.dedent`, not multiple `print()` calls.

## Comments

No arbitrary comments. Code should be self-explanatory. Only comment when the logic is genuinely non-obvious and cannot be made clearer by restructuring.

## General

Write professional code. Reference: Twisted Matrix codebase.

## Environment (when running code)

Activate the venv first: `source .venv/bin/activate`. If imports still fail after activation, the package is missing — add it with `uv`.
