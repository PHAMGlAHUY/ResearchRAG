import { useEffect, useState } from "react";
import { fetchHealth } from "../api/chatApi";

export function useHealth(paused = false, intervalMs = 15000) {
  const [health, setHealth] = useState(null); // null = đang kiểm tra

  useEffect(() => {
    if (paused) return;
    let alive = true;
    const check = async () => {
      if (document.hidden) return;
      try {
        const h = await fetchHealth();
        if (alive) setHealth(h);
      } catch {
        if (alive) setHealth({ offline: true });
      }
    };
    check();
    const t = setInterval(check, intervalMs);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [paused, intervalMs]);

  return health;
}