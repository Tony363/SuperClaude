"""Command-line helpers for inspecting MCP integrations.

Usage:
    python -m SuperClaude.MCP --list
    python -m SuperClaude.MCP --describe rube
"""

from __future__ import annotations

import argparse
import json
import textwrap
from typing import Any, Dict

def _summarize_docstring(obj: Any) -> str:
    doc = (getattr(obj, "__doc__", "") or "").strip()
    if not doc:
        return ""
    first_line = doc.splitlines()[0].strip()
    return first_line


def _load_registry():
    from . import (  # pylint: disable=import-outside-toplevel
        MCP_SERVERS,
        integration_import_errors,
    )

    return MCP_SERVERS, integration_import_errors()


def _describe_server(registry: Dict[str, Any], name: str) -> Dict[str, Any]:
    cls = registry[name]
    info: Dict[str, Any] = {
        "name": name,
        "class": f"{cls.__module__}.{cls.__name__}",
        "summary": _summarize_docstring(cls),
    }

    # Collect common class-level metadata when present.
    for attr in ("DEFAULT_ENDPOINT", "NETWORK_OK_VALUES", "DRY_RUN_VALUES"):
        if hasattr(cls, attr):
            value = getattr(cls, attr)
            if isinstance(value, set):
                value = sorted(value)
            info[attr.lower()] = value

    # Best-effort instance attributes (constructor has no required args).
    try:
        instance = cls()  # type: ignore[call-arg]
    except Exception as exc:  # pragma: no cover - defensive
        info["warning"] = f"failed to instantiate: {exc}"  # noqa: TRY401
        return info

    for attr in ("enabled", "requires_network", "endpoint", "timeout_seconds"):
        value = getattr(instance, attr, None)
        if callable(value):
            # Skip callables – we only want plain attribute values.
            continue
        if value is not None:
            if isinstance(value, set):
                value = sorted(value)
            info[attr] = value

    return info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect available Model Context Protocol integrations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              python -m SuperClaude.MCP --list
              python -m SuperClaude.MCP --describe rube --json
            """
        ).strip(),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available MCP server names.",
    )
    parser.add_argument(
        "--describe",
        metavar="NAME",
        help="Describe the specified server (name from --list).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON when used with --describe.",
    )

    args = parser.parse_args(argv)

    if not args.list and not args.describe:
        parser.print_help()
        return 0

    registry, import_errors = _load_registry()

    if args.list:
        print("Available MCP servers:")
        for name in sorted(registry):
            summary = _summarize_docstring(registry[name])
            if summary:
                print(f"  - {name}: {summary}")
            else:
                print(f"  - {name}")
        for name, error in sorted(import_errors.items()):
            missing = error.name or "dependency"
            print(f"  - {name}: unavailable (missing dependency '{missing}')")

    if args.describe:
        key = args.describe.lower()
        if key not in registry:
            if key in import_errors:
                missing = import_errors[key].name or "dependency"
                parser.error(
                    f"server '{args.describe}' is unavailable: missing optional dependency '{missing}'."
                )
            parser.error(f"unknown server '{args.describe}'. Run with --list to see options.")

        info = _describe_server(registry, key)

        if args.json:
            print(json.dumps(info, indent=2, sort_keys=True))
        else:
            print(f"Details for '{info['name']}':")
            for field, value in info.items():
                if field == "name":
                    continue
                if isinstance(value, (set, tuple, list)):
                    value_repr = ", ".join(map(str, value))
                else:
                    value_repr = str(value)
                print(f"  {field}: {value_repr}")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
