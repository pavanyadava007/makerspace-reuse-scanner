import { useEffect, useRef, useState } from "react";
import { api, type DemoStatus } from "../api";

// Controls the demo-edge container: pick a built-in or uploaded video, upload a new one, or stop.
// A real camera still connects from wherever the camera is (edge/capture.py) — a server can't reach it.
export default function DemoSource() {
  const [st, setSt] = useState<DemoStatus | null>(null);
  const [busy, setBusy] = useState(""); const [err, setErr] = useState("");
  const file = useRef<HTMLInputElement>(null);
  const load = () => api.demo().then((d) => { setSt(d); setErr(""); }).catch((e) => setErr(String(e)));
  useEffect(() => { load(); }, []);
  const selName = st?.videos.find((v) => v.edge_path === st.selected)?.name ?? "";
  const select = (name: string | null) => {
    setBusy("switching…");
    api.demoSelect(name).then(load).catch((e) => setErr(String(e))).finally(() => setBusy(""));
  };
  const upload = (f: File | undefined) => {
    if (!f) return;
    setBusy(`uploading ${f.name}…`);
    api.demoUpload(f).then((v) => { load(); select(v.name); }).catch((e) => setErr(String(e))).finally(() => setBusy(""));
  };
  return (
    <div className="card demosrc">
      <h2>Demo source</h2>
      {st && <div className="toolbar" style={{ marginBottom: 6 }}>
        <select value={selName} onChange={(e) => select(e.target.value || null)} aria-label="demo video">
          <option value="">— stopped —</option>
          {st.videos.map((v) => <option key={v.edge_path} value={v.name}>{v.name} ({v.kind}, {v.size_mb} MB)</option>)}
        </select>
        <button className="btn ghost" onClick={() => file.current?.click()} disabled={!!busy}>Upload video…</button>
        <input ref={file} type="file" accept=".mp4,.avi,.mov,.mkv" hidden onChange={(e) => upload(e.target.files?.[0])} />
        {busy && <span className="muted">{busy}</span>}
      </div>}
      <p className="muted" style={{ margin: 0, fontSize: 13 }}>
        Videos run through the real detector in the demo container (start it once: <code>docker compose --profile demo up -d demo-edge</code>).
        The switch takes effect within ~2 s. For a real camera, run <code>edge/capture.py</code> on the machine the camera is plugged into.
      </p>
      {err && <p className="err">{err}</p>}
    </div>
  );
}
