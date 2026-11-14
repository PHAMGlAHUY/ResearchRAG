const BASE = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

const networkError = () =>
  new ApiError("Không kết nối được tới backend. Kiểm tra uvicorn đã chạy chưa.", 0);

const sentence = (s) => (/[.!?]$/.test(s) ? s : s + ".");

function friendly(status, detail) {
  if (status === 503)
    return `${sentence(detail)} Hãy kiểm tra Qdrant (docker compose up -d) và Ollama (ollama serve), rồi bấm Thử lại.`;
  if (status === 504) return `${sentence(detail)} Bạn có thể bấm Thử lại.`;
  return detail; // 400, 429, 500 đã có thông báo rõ từ backend
}

async function toApiError(res) {
  let detail = `Lỗi ${res.status}`;
  try {
    const body = await res.json();
    if (typeof body.detail === "string") detail = body.detail;
  } catch {
    /* giữ thông báo mặc định */
  }
  return new ApiError(friendly(res.status, detail), res.status);
}

export async function fetchHealth() {
  const res = await fetch(`${BASE}/api/health`);
  if (!res.ok) throw new ApiError(`Lỗi ${res.status}`, res.status);
  return res.json();
}

function parseEvent(raw) {
  let event = "message";
  const data = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  return { event, data: data.length ? JSON.parse(data.join("\n")) : null };
}

export async function streamQuestion(question, { signal, onSources, onToken, onDone }) {
  let res;
  try {
    res = await fetch(`${BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
    });
  } catch (e) {
    if (e.name === "AbortError") throw e;
    throw networkError();
  }
  if (!res.ok) throw await toApiError(res);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;

  while (true) {
    let chunk;
    try {
      chunk = await reader.read();
    } catch (e) {
      if (e.name === "AbortError") throw e;
      throw new ApiError("Mất kết nối khi đang nhận câu trả lời.", 0);
    }
    if (chunk.done) break;

    buffer += decoder.decode(chunk.value, { stream: true });
    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const { event, data } = parseEvent(buffer.slice(0, sep));
      buffer = buffer.slice(sep + 2);
      if (event === "sources") onSources(data);
      else if (event === "token") onToken(data.t);
      else if (event === "done") {
        finished = true;
        onDone(data);
      } else if (event === "error") throw new ApiError(friendly(data.status, data.detail), data.status);
    }
  }
  if (!finished) throw new ApiError("Kết nối bị ngắt trước khi câu trả lời hoàn tất.", 0);
}