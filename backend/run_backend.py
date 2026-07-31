"""Dev entrypoint: `python backend/run_backend.py`.

Adds this directory to sys.path (so `app.*` / `data.*` imports resolve the
same way pytest resolves them via pyproject.toml's pythonpath) and starts
uvicorn with autoreload.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=[os.path.dirname(os.path.abspath(__file__))])
