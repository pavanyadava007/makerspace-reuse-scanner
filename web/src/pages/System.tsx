import { useEffect, useState } from "react";
import { api, type ModelCard } from "../api";

// Everything an operator should know: how stock updates, what the detector covers/misses (from the
// committed eval report only), where data lives and in which format, and how the assistant uses it.
export default function System() {
  const [card, setCard] = useState<ModelCard | null>(null);
  useEffect(() => { api.modelCard().then(setCard).catch(() => undefined); }, []);
  const ev = card?.eval;
  const classes = ev ? Object.entries(ev.per_class).sort((a, b) => b[1].ap50 - a[1].ap50) : [];
  return (
    <section className="system">
      <div className="card">
        <h2>Detector — what it covers and what it misses</h2>
        {ev ? <>
          <p>Model <code>{card?.model}</code>, measured on the held-out test split ({ev.date}); numbers come only from the
            committed report, never from prose:</p>
          <div className="tiles">
            <div className="tile"><b className="num">{(ev.map50 * 100).toFixed(0)}%</b><span>mAP@50 (all classes)</span></div>
            <div className="tile"><b className="num">{(ev.precision * 100).toFixed(0)}%</b><span>precision — how often a box is right</span></div>
            <div className="tile"><b className="num">{(ev.recall * 100).toFixed(0)}%</b><span>recall — how much it finds (rest is missed)</span></div>
          </div>
          <div className="card tablewrap">
            <table>
              <thead><tr><th>class</th><th className="num">AP@50</th><th>reading</th></tr></thead>
              <tbody>{classes.map(([c, v]) => <tr key={c}>
                <td>{c.replace(/_/g, " ")}</td><td className="num">{(v.ap50 * 100).toFixed(1)}%</td>
                <td className="muted">{v.ap50 > 0.9 ? "strong (studio-shot test images — flattering)" : v.ap50 > 0.35 ? "usable" :
                  v.ap50 > 0.1 ? "weak — expect misses" : "not usable yet (too little training data)"}</td>
              </tr>)}</tbody>
            </table>
          </div>
          <p className="muted">The confusion matrix shows the dominant failure is <b>missing small/distant objects</b>, not
            confusing classes. Six classes (filament_spool, wood_offcut, cable, 3d_print_part, acrylic_sheet, metal_profile)
            have no public training data yet and are never detected — they need own photos.</p>
        </> : <p className="muted">No eval report found — run <code>make eval</code> after training.</p>}
      </div>

      <div className="card">
        <h2>How the inventory updates (and how to reset it)</h2>
        <ul>
          <li>The edge node sends every 3rd frame's detections over WebSocket; each detection is classified for material and saved.</li>
          <li><b>Dedupe rule:</b> the same label at the same location seen within <b>20 s of its last sighting</b> is the SAME item —
            re-detections refresh the timer. Quantity = the most same-class boxes ever seen in one frame.</li>
          <li>An object that disappears for more than 20 s and returns becomes a <i>new</i> item (no visual tracker yet — that's the
            documented next step). Looping demo videos therefore grow the item count over time.</li>
          <li><b>Reset:</b> the “Clear inventory” button on the Inventory tab (or <code>POST /api/admin/reset</code>) deletes all items,
            detections, suggestions and stored frames — materials and the knowledge base stay. Use it before a fresh demo run.</li>
        </ul>
      </div>

      <div className="card">
        <h2>Where the data lives, and in what format</h2>
        <div className="card tablewrap"><table>
          <thead><tr><th>data</th><th>store</th><th>format</th></tr></thead>
          <tbody>
            <tr><td>items, detections, suggestions, materials</td><td>PostgreSQL 16 (<code>pgdata</code> volume)</td>
              <td>relational rows — item(label, material, qty, status, location), detection(box, confidence, material + backend, device, FPS)</td></tr>
            <tr><td>camera frames</td><td><code>imagestore</code> volume</td><td>JPEG files; the DB stores the path + capture metadata</td></tr>
            <tr><td>knowledge base</td><td>same PostgreSQL, table <code>rag_chunk</code></td>
              <td>markdown sections + a 768-d embedding vector (pgvector, HNSW index) per chunk</td></tr>
            <tr><td>demo videos</td><td><code>./models</code> (built-in) + <code>demostore</code> volume (uploads)</td><td>mp4/avi/mov</td></tr>
            <tr><td>accuracy numbers</td><td><code>training/reports/</code> (committed files)</td><td>markdown + JSON, generated only by <code>eval_report.py</code></td></tr>
          </tbody>
        </table></div>
      </div>

      <div className="card">
        <h2>How the assistant (Ask) uses this data</h2>
        <ol>
          <li>Your question is embedded (nomic-embed-text) and the closest knowledge-base chunks are retrieved from pgvector; chunks that
            share <b>rare literal terms</b> with the question (Postgres full-text search, e.g. “Kamin”, “PVC”) are added, because
            embeddings alone missed them in the evaluation (<code>rag/eval/reports/</code>).</li>
          <li>A <b>live inventory snapshot</b> is generated from the database at that moment — counts per class, statuses, and the
            correct bin per material — and added to the context as its own cited source (<code>live-inventory</code>).</li>
          <li>The local LLM (llama3.1:8b via Ollama) must answer <b>only from that context</b>, cite [n], and decline anything not
            covered — so stock numbers are real and disposal rules are never invented. Everything runs on-premise.</li>
        </ol>
      </div>
    </section>
  );
}
