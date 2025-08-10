import os
import sys
import pytest

# Ensure src layout is importable
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


@pytest.fixture(scope="session", autouse=True)
def _api_key_env_setup():
    # Provide a default key mapping for tests: viewer & operator
    os.environ["BOLCD_API_KEYS"] = "testviewer:viewer,testop:operator"
    yield
