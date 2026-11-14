import { useCallback, useEffect, useRef, useState } from "react";
import { streamQuestion } from "../api/chatApi";

export const MAX_QUERY_LENGTH = 512; // khớp MAX_QUERY_LENGTH ở backend
const STORAGE_KEY = "my_rag.chat.v1";
const MAX_SAVED = 50;

let counter = 0;
const newId = () => `${Date.now()}-${counter++}`;

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw)
      .filter((m) => !(m.streaming && !m.content))
      .map((m) =>
        m.streaming ? { ...m, streaming: false, warning: "Câu trả lời bị gián đoạn." } : m
      );
  } catch {
    return [];
  }
}

function save(messages) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_SAVED)));
  } catch {
    /* hết dung lượng hoặc bị chặn: bỏ qua */
  }
}

export function useChat() {
  const [messages, setMessages] = useState(load);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef(null);

  useEffect(() => {
    if (!loading) save(messages);
  }, [messages, loading]);

  const ask = useCallback(async (question) => {
    const id = newId();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);

    const patch = (fn) => setMessages((m) => m.map((x) => (x.id === id ? fn(x) : x)));

    try {
      await streamQuestion(question, {
        signal: controller.signal,
        onSources: (sources) =>
          setMessages((m) => [
            ...m,
            { id, role: "assistant", content: "", sources, streaming: true },
          ]),
        onToken: (t) => patch((x) => ({ ...x, content: x.content + t })),
        onDone: (d) => patch((x) => ({ ...x, streaming: false, latencyMs: d.latency_ms })),
      });
    } catch (e) {
      if (e.name === "AbortError") {
        // Người dùng bấm Dừng: giữ phần đã có, bỏ tin nhắn rỗng
        setMessages((m) =>
          m.flatMap((x) => (x.id !== id ? [x] : x.content ? [{ ...x, streaming: false }] : []))
        );
      } else {
        setMessages((m) => {
          const errorMsg = { id, role: "assistant", error: e.message, status: e.status, question };
          if (!m.some((x) => x.id === id)) return [...m, errorMsg];
          // Lỗi giữa chừng: giữ phần đã nhận và hiện cảnh báo; chưa có gì thì hiện lỗi + Thử lại
          return m.map((x) =>
            x.id !== id ? x : x.content ? { ...x, streaming: false, warning: e.message } : errorMsg
          );
        });
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  }, []);

  const send = useCallback(
    (text) => {
      const question = text.trim();
      if (!question || loading || question.length > MAX_QUERY_LENGTH) return;
      setMessages((m) => [...m, { id: newId(), role: "user", content: question }]);
      ask(question);
    },
    [ask, loading]
  );

  const retry = useCallback(
    (errorMessageId, question) => {
      if (loading) return;
      setMessages((m) => m.filter((x) => x.id !== errorMessageId));
      ask(question);
    },
    [ask, loading]
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages([]);
    setLoading(false);
  }, []);

  return { messages, loading, send, retry, stop, reset };
}