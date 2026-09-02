import { useEffect, useRef, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { wsUrl, type Frame, type Status } from "./api";
import Live from "./pages/Live";
import Inventory from "./pages/Inventory";
import ItemDetail from "./pages/ItemDetail";
import Ask from "./pages/Ask";
import System from "./pages/System";

export default function App() {
  const [status, setStatus] = useState<Status["edges"]>({});
  const [frame, setFrame] = useState<Frame | null>(null);
  const [connected, setConnected] = useState(false);
  const retry = useRef(0);
  useEffect(() => {
    let ws: WebSocket; let alive = true;
    const open = () => {
      ws = new WebSocket(wsUrl("/ws/live"));
      ws.onopen = () => { setConnected(true); retry.current = 0; };
      ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.type === "status") setStatus(m.edges); else if (m.type === "frame") setFrame(m); };
      ws.onclose = () => { setConnected(false); if (alive) setTimeout(open, Math.min(8000, 500 * 2 ** retry.current++)); };
    };
    open(); return () => { alive = false; ws.close(); };
  }, []);
  const edges = Object.entries(status);
  return (<>
    <header className="topbar">
      <h1>Makerspace Reuse Scanner</h1>
      <nav>
        <NavLink to="/" end>Live</NavLink>
        <NavLink to="/inventory">Inventory</NavLink>
        <NavLink to="/ask">Ask</NavLink>
        <NavLink to="/system">System</NavLink>
      </nav>
      <div className="edges">
        {!connected && <span className="edge off">API offline</span>}
        {connected && edges.length === 0 && <span className="edge off">no edge node connected</span>}
        {edges.map(([dev, s]) => (
          <span key={dev} className="edge" title={`${s.model ?? "model unknown"} · ${(s.providers ?? []).join(", ")}`}>
            <b>{dev}</b> {s.fps != null ? `${s.fps.toFixed(1)} FPS · ${s.infer_ms} ms` : "idle"}
          </span>
        ))}
      </div>
    </header>
    <main>
      <Routes>
        <Route path="/" element={<Live frame={frame} edges={status} />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/items/:id" element={<ItemDetail />} />
        <Route path="/ask" element={<Ask />} />
        <Route path="/system" element={<System />} />
      </Routes>
    </main>
    <footer className="foot">
      Honesty rules: FPS is always labelled with the device it was measured on · mAP comes only from committed reports
      (<code>training/reports/</code>) · every material prediction records its backend (clip / qwen / class-prior).
    </footer>
  </>);
}
