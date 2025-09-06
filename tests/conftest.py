# tests/conftest.py
import sys, types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# If PyMuPDF isn't importable during collection, stub it
try:
    import fitz  # noqa: F401
except Exception:
    sys.modules["fitz"] = types.ModuleType("fitz")
