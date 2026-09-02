import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DemoSource from "../components/DemoSource";
import Overlay from "../components/Overlay";
import { api, materialHue, type Frame, type LiveDet, type Status } from "../api";

export default function Live({ frame, edges }: { frame: Frame | null; edges: Status["edges"] }) {
  const [feed, setFeed] = useState<(LiveDet & { t: number; device: string })[]>([]);
  const [bins, setBins] = useState<Record<string, string>>({});
  useEffect(() => {
    api.materials().then((ms) => setBins(Object.fromEntries(ms.filter((m) => m.disposal_de).map((m) => [m.name, m.disposal_de!]))))
      .catch(() => undefined);
  }, []);
  const [lastTs, setLastTs] = useState(0);
  const [, tick] = useState(0);
  useEffect(() => {
    if (!frame) return;
    setLastTs(Date.now());
    setFeed((f) => [...frame.detections.map((d) => ({ ...d, t: Date.now(), device: frame.device })), ...f].slice(0, 40));
  }, [frame]);
  useEffect(() => { const t = setInterval(() => tick((n) => n + 1), 1000); return () => clearInterval(t); }, []);
  const stale = frame != null && Date.now() - lastTs > 6000;
  const edge = frame ? edges[frame.device] : undefined;
  return (
    <section className="live">
      <div>
        <div className="stage">
          {frame ? <>
            <img src={`data:image/jpeg;base64,${frame.frame}`} alt="camera frame" />
            <Overlay w={frame.width} h={frame.height} dets={frame.detections} />
            {stale && <span className="stale">stream idle — last frame {Math.round((Date.now() - lastTs) / 1000)} s ago</span>}
          </> : <div className="empty">
            No frames yet. Start an edge node where the camera is:<br />
            <code>cd edge && python capture.py</code><br />
            or, without a camera or model:<br />
            <code>python scripts/simulate_edge.py</code>
          </div>}
        </div>
        {frame && <dl className="kv wide">
          <dt>Device</dt><dd>{frame.device}</dd>
          <dt>Model</dt><dd>{edge?.model ?? "—"}</dd>
          <dt>Providers</dt><dd>{(edge?.providers ?? []).join(", ") || "—"}</dd>
          <dt>Throughput</dt><dd className="num">{frame.fps.toFixed(1)} FPS end-to-end · {frame.infer_ms} ms inference · {frame.width}×{frame.height}</dd>
        </dl>}
      </div>
      <aside className="sidecol">
      <DemoSource />
      <div className="feed card">
        <h2>Recent detections</h2>
        {feed.length === 0 ? <p className="muted">Detections appear here as they are saved to the inventory.</p> :
        <ul>{feed.map((d, i) => (
          <li key={i}>
            <i style={{ background: materialHue[d.material ?? ""] ?? "var(--other)" }} />
            <span>{d.item_id ? <Link to={`/items/${d.item_id}`}>{d.cls.replace(/_/g, " ")}</Link> : d.cls.replace(/_/g, " ")}
              <br /><small>{d.material ?? "material pending"}{d.material && bins[d.material] ? <> · bin: <b>{bins[d.material]}</b></> : null}</small></span>
            <span className="num muted">{(d.conf * 100).toFixed(0)}%</span>
          </li>))}</ul>}
      </div>
      </aside>
    </section>
  );
}
