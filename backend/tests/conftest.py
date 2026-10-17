import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["MEDIA_DIR"] = "./test_media"

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    from app import security
    security._hits.clear()
    yield
