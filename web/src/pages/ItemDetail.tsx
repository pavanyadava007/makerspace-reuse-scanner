import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Overlay from "../components/Overlay";
import { api, type Detection, type ItemDetail as T, type Material } from "../api";

const HISTORY_ROWS = 200;   // a looping demo produces thousands of sightings per item; the table shows the latest ones

export default function ItemDetail() {
  const id = Number(useParams().id);
  const nav = useNavigate();
  const [it, setIt] = useState<T | null>(null); const [mats, setMats] = useState<Material[]>([]);
  const [busy, setBusy] = useState(false); const [dim, setDim] = useState({ w: 1280, h: 720 });
  const [err, setErr] = useState(""); const [lang, setLang] = useState("de");
  const [sel, setSel] = useState<Detection | null>(null);
  const load = () => api.item(id).then((d) => { setIt(d); setSel((s) => s ?? d.detections.find((x) => x.image_id === d.first_image_id) ?? d.detections[0] ?? null); }).catch((e) => setErr(String(e)));
  useEffect(() => { load(); api.materials().then(setMats).catch(() => undefined); }, [id]);
  if (err) return <p className="err">{err}</p>;
  if (!it) return <p className="muted">Loading…</p>;
  const patch = (b: Parameters<typeof api.patch>[1]) => api.patch(id, b).then(load).catch((e) => setErr(String(e)));
  const suggest = () => { setBusy(true); api.suggest(id, lang).then(load).catch((e) => setErr(String(e))).finally(() => setBusy(false)); };
  const remove = () => {
    if (!window.confirm(`Delete item #${it.id} (${it.label})?`)) return;
    api.del(id).then(() => nav("/inventory")).catch((e) => setErr(String(e)));
  };
  return (
    <section className="detail">
      <div>
        <div className="stage">
          {sel ? <>
            <img src={`/api/images/${sel.image_id}`} alt={it.label} onLoad={(e) => setDim({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })} />
            <Overlay w={dim.w} h={dim.h} link={false}
              dets={[{ cls: sel.cls, conf: sel.conf, xyxy: [sel.x1, sel.y1, sel.x2, sel.y2], material: sel.material_pred, item_id: null }]} />
          </> : <div className="empty">Added by hand - no camera image.</div>}
        </div>
        <h2>Detection history <span className="muted">({it.detections.length > HISTORY_ROWS ? `latest ${HISTORY_ROWS} of ${it.detections.length}` : it.detections.length} - click a row to show its frame)</span></h2>
        <div className="card tablewrap">
          <table>
            <thead><tr><th>When</th><th className="num">Conf</th><th>Material (backend)</th><th>Device</th><th className="num">FPS / ms</th></tr></thead>
            <tbody>{it.detections.slice(0, HISTORY_ROWS).map((d) => (
              <tr key={d.id} className={sel?.id === d.id ? "sel" : "clickable"} onClick={() => setSel(d)}>
                <td className="num">{new Date(d.created_at).toLocaleString()}</td><td className="num">{(d.conf * 100).toFixed(0)}%</td>
                <td>{d.material_pred ?? "-"} <span className="muted">({d.vlm_backend})</span></td><td>{d.device}</td>
                <td className="num">{d.fps} / {d.infer_ms}</td>
              </tr>))}
              {it.detections.length === 0 && <tr><td colSpan={5} className="muted">No detections - this item was added manually.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      <aside>
        <div className="titlerow">
          <h2 className="pagetitle">{it.label.replace(/_/g, " ")} <span className="muted num">#{it.id}</span></h2>
          <button className="btn danger sm" onClick={remove}>delete</button>
        </div>
        <dl className="kv card">
          <dt>Material</dt><dd><select value={it.material?.id ?? ""} onChange={(e) => patch({ material_id: Number(e.target.value) })}>
            <option value="">unknown</option>{mats.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select></dd>
          <dt>Disposal (DE)</dt><dd>{it.material?.disposal_de ?? "-"}</dd>
          <dt>Recyclable</dt><dd>{it.material ? (it.material.recyclable ? "yes" : "no") : "-"}</dd>
          <dt>Condition</dt><dd><select value={it.condition ?? ""} onChange={(e) => patch({ condition: e.target.value })}>
            <option value="">unknown</option>{["like new", "lightly used", "worn", "damaged", "scrap"].map((c) => <option key={c}>{c}</option>)}</select></dd>
          <dt>Quantity</dt><dd><input type="number" min={1} value={it.quantity} onChange={(e) => patch({ quantity: Number(e.target.value) })} /></dd>
          <dt>Location</dt><dd>{it.location ?? "-"}</dd>
          <dt>Status</dt><dd><select value={it.status} onChange={(e) => patch({ status: e.target.value })}>
            {["available", "reserved", "reused", "disposed"].map((s) => <option key={s}>{s}</option>)}</select></dd>
          <dt>First seen</dt><dd className="num">{new Date(it.created_at).toLocaleString()}</dd>
        </dl>
        <div className="toolbar">
          <button className="btn" onClick={suggest} disabled={busy}>{busy ? "Asking local model…" : "Suggest reuse"}</button>
          <select value={lang} onChange={(e) => setLang(e.target.value)} aria-label="language"><option value="de">Deutsch</option><option value="en">English</option></select>
        </div>
        {it.suggestions.map((s) => <div key={s.id} className="suggestion">
          <div className="answer">{s.text}</div>
          <ol className="sources">{s.sources?.map((x) => <li key={x.n}>{x.doc} › {x.section}</li>)}</ol>
          <p className="muted meta">{s.model} · {new Date(s.created_at).toLocaleString()}</p>
        </div>)}
      </aside>
    </section>
  );
}
