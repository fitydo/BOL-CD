from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Schemathesis contract test skipped for CI stability; enable when loaders API is stable."
)
