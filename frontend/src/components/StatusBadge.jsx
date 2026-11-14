import { useHealth } from "../hooks/useHealth";

export default function StatusBadge({ paused }) {
  const health = useHealth(paused);
  if (!health) return <div className="status">Đang kiểm tra…</div>;

  const items = health.offline
    ? [{ name: "Backend", ok: false, detail: "Không kết nối được backend" }]
    : [
        { name: "Qdrant", ok: health.qdrant.ok, detail: health.qdrant.detail },
        { name: "Ollama", ok: health.ollama.ok, detail: health.ollama.detail },
      ];

  return (
    <div className="status">
      {items.map((s) => (
        <span key={s.name} className="status-item" title={s.ok ? "Hoạt động" : s.detail}>
          <span className={`dot ${s.ok ? "ok" : "bad"}`} />
          {s.name}
        </span>
      ))}
    </div>
  );
}