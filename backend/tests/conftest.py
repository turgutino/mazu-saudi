"""Pytest-wide fixtures for the backend test suite.

Points ``MAZU_DB_PATH`` at a throwaway temp file *before* any ``app.*``
module is imported, so ``app.repositories.db``'s module-level SQLite engine
never touches the real dev database (``backend/var/mazu.db``). This module
is collected by pytest before any test module in this directory, which is
what makes the ordering guarantee hold.
"""

from __future__ import annotations

import os
import tempfile

_tmp_db_dir = tempfile.mkdtemp(prefix="mazu-test-db-")
os.environ["MAZU_DB_PATH"] = os.path.join(_tmp_db_dir, "test.db")
