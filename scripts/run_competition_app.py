#!/usr/bin/env python3
"""Start the local MAZU historical warning application after preflight."""

from __future__ import annotations

import argparse
import json

import uvicorn

from mazu_saudi.competition.settings import AppSettings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MAZU historical warning console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    settings = AppSettings()
    print(json.dumps(settings.preflight(), ensure_ascii=False, indent=2))
    uvicorn.run("mazu_saudi.competition.app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
