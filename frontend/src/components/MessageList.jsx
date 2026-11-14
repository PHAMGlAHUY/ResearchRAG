import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

export default function MessageList({ messages, loading, onRetry }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="message-list">
      {messages.length === 0 && (
        <div className="empty">Hỏi bất kỳ điều gì về bài báo RAG (Lewis và cộng sự, 2020).</div>
      )}
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} onRetry={onRetry} />
      ))}
      {loading && !messages.at(-1)?.streaming && (
        <div className="bubble assistant typing">Đang tìm và soạn câu trả lời…</div>
      )}

      <div ref={endRef} />
    </div>
  );
}