import { useState } from "react";

export default function CopyButton({ text, className = "" }) {
  const [done, setDone] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    } catch {
      /* trình duyệt chặn clipboard: bỏ qua */
    }
  };

  return (
    <button className={`copy ${className}`} onClick={copy}>
      {done ? "Đã chép" : "Sao chép"}
    </button>
  );
}