import os
import sys
import pytest

# Ensure project root is importable so that `src` package can be resolved
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
    
# Also add the inner `src` directory to support imports like `import bolcd`
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


@pytest.fixture(scope="session", autouse=True)
def _api_key_env_setup():
    # Provide a default key mapping for tests: viewer & operator
    os.environ["BOLCD_API_KEYS"] = "testviewer:viewer,testop:operator"
    yield
