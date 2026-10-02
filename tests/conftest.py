"""Shared test fixtures and path setup."""

import os
import sys

# Ensure project root is importable when running pytest from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
