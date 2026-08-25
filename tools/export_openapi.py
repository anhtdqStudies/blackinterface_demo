#!/usr/bin/env python3
"""Write the API schema to `backend/openapi.json`.

This file is the contract between backend and frontend. `npm run api:types`
turns it into TypeScript, so a renamed field becomes a compile error in the
frontend instead of `undefined` at 2 a.m. in a substation.

    python tools/export_openapi.py            # write it
    python tools/export_openapi.py --check    # fail if it is out of date

`--check` runs in tools/check.py: if someone changes an endpoint and forgets to
export, the repo check goes red rather than the frontend drifting silently.

Run with the backend environment:
    cd backend && uv run python ../tools/export_openapi.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "backend" / "openapi.json"
SRC = ROOT / "backend" / "src"


def build_schema() -> str:
    sys.path.insert(0, str(SRC))
    from blackinterface.api.app import app  # noqa: PLC0415  (needs sys.path first)

    return json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify instead of writing")
    args = parser.parse_args()

    schema = build_schema()
    if not args.check:
        OUT.write_text(schema, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}")
        return 0

    if not OUT.exists():
        print(f"MISSING {OUT.relative_to(ROOT)} - run: python tools/export_openapi.py")
        return 1
    if OUT.read_text(encoding="utf-8") != schema:
        print(
            f"STALE {OUT.relative_to(ROOT)} - the API changed but the schema was not "
            "exported.\nRun: python tools/export_openapi.py"
        )
        return 1
    print(f"{OUT.relative_to(ROOT)} is up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
