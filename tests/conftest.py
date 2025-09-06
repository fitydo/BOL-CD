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
    # Provide a default superset of API keys covering all scopes used across tests
    # Format: scope:key
    os.environ["BOLCD_API_KEYS"] = ",".join([
        # Keys used by integration tests
        "admin:admin-key",
        "condensed:test-key",
        "full:full-key",
        "ingest:ingest-key",
        # Keys used by condensed API tests
        "admin:demo-key-admin",
        "condensed:demo-key-condensed",
        "full:demo-key-full",
        "ingest:demo-key-ingest",
        # Additional roles used in some RBAC tests
        "viewer:testviewer",
        "operator:testop",
    ])
    # Ensure tests use plain key matching and avoid rate limiting side-effects
    os.environ["BOLCD_HASH_METHOD"] = "plain"
    os.environ["BOLCD_RATE_LIMIT_ENABLED"] = "0"
    yield
