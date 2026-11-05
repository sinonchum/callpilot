import { useEffect, useRef, useState } from "react";
import { applyEvent, initialView, parseJsonl, type PanelEvent, type ViewState } from "./view";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://127.0.0.1:8765/events";

export function App() {
  const [view, setView] = useState<ViewState>(initialView);
  const [link, setLink] = useState("未连接");
  const [error, setError] = useState("");
  const timer = useRef<number | null>(null);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    socket.addEventListener("open", () => setLink("已连接"));
    socket.addEventListener("message", (message) => {
      const event = JSON.parse(String(message.data)) as PanelEvent;
      setView((current) => applyEvent(current, event));
    });
    socket.addEventListener("close", () => setLink("未连接"));
    socket.addEventListener("error", () => setLink("连接失败"));
    return () => {
      socket.close();
      if (timer.current !== null) {
        window.clearInterval(timer.current);
      }
    };
  }, []);

  async function replay() {
    setError("");
    if (timer.current !== null) {
      window.clearInterval(timer.current);
    }
    const response = await fetch("/fixtures/panel_replay.jsonl");
    if (!response.ok) {
      setError("读不到回放文件");
      return;
    }
    const events = parseJsonl(await response.text());
    setView(initialView());
    let index = 0;
    timer.current = window.setInterval(() => {
      const event = events[index];
      if (!event) {
        if (timer.current !== null) {
          window.clearInterval(timer.current);
        }
        return;
      }
      index += 1;
      setView((current) => applyEvent(current, event));
    }, 280);
  }

  const corrected = view.status === "corrected";

  return (
    <main>
      <header>
        <div>
          <h1>CallPilot</h1>
          <p>mock 回放 · 不需要手机</p>
        </div>
        <div className="toolbar">
          <button type="button" onClick={() => void replay()}>
            回放剧本
          </button>
          <div className="status mono" aria-live="polite">
            {link}
          </div>
        </div>
      </header>
      <section className="grid">
        <article className="column">
          <h2>转写</h2>
          <ul>
            {view.lines.map((line) => (
              <li key={line.id} className={line.final ? "final" : "partial"}>
                {line.text}
              </li>
            ))}
          </ul>
        </article>
        <article className="column">
          <h2>槽位</h2>
          <p className={corrected ? "time corrected" : "time"} aria-live="polite">
            {view.time}
          </p>
          <div className="slots">
            <Slot label="日期" value={view.date || "—"} />
            <Slot label="地点" value={view.location || "—"} />
            <Slot label="标题" value={view.title || "—"} />
            <Slot label="状态" value={view.status || "—"} />
            <Slot label="提醒" value={view.reminder || "—"} />
          </div>
        </article>
        <article className="column">
          <h2>步骤</h2>
          <ul className="mono">
            {view.steps.map((step, index) => (
              <li key={`${step}-${index}`}>{step}</li>
            ))}
          </ul>
          <ul className="mono">
            {view.verifies.map((line, index) => (
              <li key={`${line}-${index}`}>{line}</li>
            ))}
          </ul>
        </article>
      </section>
      <section className="card">
        <h2>确认卡</h2>
        {view.card === null ? (
          <p>挂断之后才会列出日历、提醒和便签。</p>
        ) : (
          <ul>
            {view.card.map((item) => (
              <li key={item.label}>
                <strong>{item.label}</strong> {item.summary}
              </li>
            ))}
          </ul>
        )}
        <p className="mono">{view.decision ? `decision ${view.decision}` : "等待确认"}</p>
        {error ? <p>{error}</p> : null}
        <p>{view.note}</p>
      </section>
    </main>
  );
}

function Slot({ label, value }: { label: string; value: string }) {
  return (
    <div className="slot">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
