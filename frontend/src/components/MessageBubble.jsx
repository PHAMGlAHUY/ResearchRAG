import { useState } from "react";
import CopyButton from "./CopyButton";
import Markdown from "./Markdown";
import SourceList from "./SourceList";

export default function MessageBubble({ message, onRetry }) {
  const [openIndex, setOpenIndex] = useState(null);
  const toggle = (n) => setOpenIndex((cur) => (cur === n ? null : n));

  if (message.role === "user") {
    return <div className="bubble user">{message.content}</div>;
  }

  if (message.error) {
    return (
      <div className="bubble assistant error">
        <p>{message.error}</p>
        {message.status !== 400 && (
          <button className="retry" onClick={() => onRetry(message.id, message.question)}>
            Thử lại
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="bubble assistant">
      <div className={`answer ${message.streaming ? "streaming" : ""}`}>
        <Markdown text={message.content} sources={message.sources} onCite={toggle} />
      </div>
      {message.warning && <div className="warning">{message.warning}</div>}
      <SourceList sources={message.sources} openIndex={openIndex} onToggle={toggle} />
      <div className="meta">
        {message.latencyMs != null && <span>{(message.latencyMs / 1000).toFixed(1)}s</span>}
        {!message.streaming && message.content && (
          <CopyButton text={message.content} className="copy-answer" />
        )}
      </div>
    </div>
  );
}