import { useState } from "react";
import { MAX_QUERY_LENGTH } from "../hooks/useChat";

export default function ChatInput({ onSend, loading, onStop }) {
  const [text, setText] = useState("");
  const tooLong = text.length > MAX_QUERY_LENGTH;
  const canSend = !loading && text.trim() && !tooLong;

  const submit = () => {
    if (!canSend) return;
    onSend(text);
    setText("");
  };

  return (
    <div className="chat-input">
      <textarea
        value={text}
        rows={2}
        placeholder="Nhập câu hỏi… (Enter để gửi, Shift+Enter xuống dòng)"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <div className="chat-input-side">
        <span className={tooLong ? "counter over" : "counter"}>
          {text.length}/{MAX_QUERY_LENGTH}
        </span>
        {loading ? (
          <button onClick={onStop}>Dừng</button>
        ) : (
          <button onClick={submit} disabled={!canSend}>
            Gửi
          </button>
        )}
      </div>
    </div>
  );
}