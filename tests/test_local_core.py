import os
import sys
import py_compile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
import carver


def test_core_modules_and_signatures():
    assert hasattr(config, "APP_NAME")
    assert hasattr(config, "CATEGORIES")
    assert len(config.CATEGORIES) > 0
    assert carver is not None


def test_all_python_modules_compile():
    errors = []
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".venv", "yedekler", "tests"}]
        for f in files:
            if f.endswith(".py"):
                fp = os.path.join(root, f)
                try:
                    py_compile.compile(fp, doraise=True)
                except Exception as exc:
                    errors.append(f"{fp}: {exc}")
    assert not errors, f"Syntax errors: {errors}"
