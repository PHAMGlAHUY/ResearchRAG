import pytest

from api.rate_limit import RateLimiter, limiter
from api.routers import health
from api.services import chat_service
from llm.generator import LLMError

Q = {"question": "What is RAG-Sequence?"}


# ---------- /api/health ----------
def test_health_ok(client, monkeypatch):
    monkeypatch.setattr(health, "check_qdrant", lambda: (True, ""))
    monkeypatch.setattr(health, "check_ollama", lambda: (True, ""))
    body = client.get("/api/health").json()
    assert body["status"] == "ok"


def test_health_degraded(client, monkeypatch):
    monkeypatch.setattr(health, "check_qdrant", lambda: (True, ""))
    monkeypatch.setattr(health, "check_ollama", lambda: (False, "Model chưa được pull"))
    body = client.get("/api/health").json()
    assert body["status"] == "degraded"
    assert body["ollama"] == {"ok": False, "detail": "Model chưa được pull"}


# ---------- /api/chat ----------
def test_chat_ok(client, monkeypatch, docs):
    monkeypatch.setattr(chat_service, "answer_question", lambda q: ("RAG-Sequence là ... [1]", docs))
    r = client.post("/api/chat", json=Q)
    assert r.status_code == 200
    body = r.json()
    assert body["answer"].endswith("[1]")
    assert body["sources"][0]["index"] == 1
    assert body["sources"][0]["section"] == "Methods > RAG-Sequence Model"
    assert body["latency_ms"] >= 0


@pytest.mark.parametrize("question", ["", "   ", "x" * 10_000])
def test_invalid_question_is_400(client, question):
    r = client.post("/api/chat", json={"question": question})
    assert r.status_code == 400
    assert "detail" in r.json()


@pytest.mark.parametrize(
    "exc,status",
    [
        (ConnectionError("down"), 503),
        (TimeoutError("slow"), 504),
        (LLMError("bad"), 500),
        (RuntimeError("boom"), 500),
    ],
)
def test_error_mapping(client, monkeypatch, exc, status):
    def boom(question):
        raise exc

    monkeypatch.setattr(chat_service, "answer_question", boom)
    r = client.post("/api/chat", json=Q)
    assert r.status_code == status
    assert "detail" in r.json()


# ---------- /api/chat/stream ----------
def _text(r):
    return r.content.decode("utf-8")


def test_stream_ok(client, monkeypatch, docs):
    monkeypatch.setattr(chat_service, "prepare_question", lambda q: (q.strip(), docs))
    monkeypatch.setattr(chat_service, "generate_answer_stream",
                        lambda context, question: iter(["Xin ", "chào [1]"]))
    r = client.post("/api/chat/stream", json=Q)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    text = _text(r)
    assert text.index("event: sources") < text.index("event: token") < text.index("event: done")
    assert "chào [1]" in text


def test_stream_no_documents(client, monkeypatch):
    monkeypatch.setattr(chat_service, "prepare_question", lambda q: (q.strip(), []))
    text = _text(client.post("/api/chat/stream", json=Q))
    assert "event: sources\ndata: []" in text
    assert "event: done" in text


def test_stream_failure_before_start_is_http_error(client, monkeypatch, docs):
    monkeypatch.setattr(chat_service, "prepare_question", lambda q: (q.strip(), docs))

    def broken(context, question):
        raise ConnectionError("Ollama down")
        yield  # biến hàm thành generator

    monkeypatch.setattr(chat_service, "generate_answer_stream", broken)
    r = client.post("/api/chat/stream", json=Q)
    assert r.status_code == 503


def test_stream_failure_midway_sends_error_event(client, monkeypatch, docs):
    monkeypatch.setattr(chat_service, "prepare_question", lambda q: (q.strip(), docs))

    def flaky(context, question):
        yield "a"
        raise TimeoutError("slow")

    monkeypatch.setattr(chat_service, "generate_answer_stream", flaky)
    r = client.post("/api/chat/stream", json=Q)
    text = _text(r)
    assert r.status_code == 200
    assert "event: error" in text and '"status": 504' in text
    assert "event: done" not in text


# ---------- giới hạn tốc độ ----------
def test_rate_limit_returns_429(client, monkeypatch, docs):
    monkeypatch.setattr(limiter, "max_requests", 2)
    monkeypatch.setattr(chat_service, "answer_question", lambda q: ("ok", docs))
    responses = [client.post("/api/chat", json=Q) for _ in range(3)]
    assert [r.status_code for r in responses] == [200, 200, 429]
    assert int(responses[2].headers["retry-after"]) >= 1


def test_rate_limiter_unit():
    rl = RateLimiter(max_requests=2, window_s=60)
    assert rl.check("a") == 0
    assert rl.check("a") == 0
    assert rl.check("a") > 0      # bị chặn
    assert rl.check("b") == 0     # IP khác không bị ảnh hưởng