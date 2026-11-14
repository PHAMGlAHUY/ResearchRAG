from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.rate_limit import limiter

@pytest.fixture(autouse=True)
def _reset_limiter():
    limiter.reset()
    yield
    limiter.reset()

@pytest.fixture
def client():
    # Không dùng `with`, nên lifespan (warmup tải model) không chạy.
    # raise_server_exceptions=False để lỗi 500 trả về response thay vì ném ra test.
    return TestClient(app, raise_server_exceptions=False)

@pytest.fixture
def docs():
    return [
        SimpleNamespace(
            text="RAG-Sequence dùng cùng một tài liệu cho toàn bộ chuỗi đầu ra.",
            score=0.82,
            metadata={"Header 1": "Methods", "Header 2": "RAG-Sequence Model"},
        )
    ]

