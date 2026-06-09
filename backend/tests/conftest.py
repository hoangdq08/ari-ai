"""Pytest configuration: ensure backend root is importable.

Run from `backend/` with:

    venv/bin/python -m pytest

`pytest.ini` declares `testpaths = tests` and adds the project root to
`sys.path` so `from app...` imports work the same way the production server
sees them.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # backend/
sys.path.insert(0, str(ROOT))

# Keep LLM disabled by default in tests; individual tests can opt in.
os.environ.setdefault("NONGTRI_LLM_ENABLED", "false")

# Force the deterministic hashing embedder in tests so the suite does not
# hit Ollama or any network service. Individual tests can override the
# provider via monkeypatching the env var + reloading the module.
os.environ.setdefault("NONGTRI_EMBEDDING_PROVIDER", "hashing")
os.environ.setdefault("NONGTRI_EMBEDDING_FALLBACK", "")
