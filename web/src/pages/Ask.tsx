import { useState } from "react";
import { api, type Ask as AskResult } from "../api";

const EXAMPLES = [
  "Wohin mit PLA-Fehldrucken?",
  "Wohin mit einem defekten Lithium-Akku?",
  "Kann ich PETG-Drucke in den Gelben Sack werfen?",
  "How do I reuse plywood offcuts?",
  "Wie viele Schrauben haben wir gesammelt, und in welchen Behälter gehören sie?",
  "What is currently in stock and where does each thing belong?",
];

type Entry = AskResult & { q: string; t: number };

export default function Ask() {
  const [q, setQ] = useState(""); const [lang, setLang] = useState("de");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const [history, setHistory] = useState<Entry[]>([]);
  const submit = (question: string) => {
    const text = question.trim(); if (!text || busy) return;
    setBusy(true); setErr("");
    api.ask(text, lang)
      .then((r) => { setHistory((h) => [{ ...r, q: text, t: Date.now() }, ...h]); setQ(""); })
      .catch((e) => setErr(`${e} - is Ollama running with its models pulled?`))
      .finally(() => setBusy(false));
  };
  return (
    <section className="ask">
      <div className="card askbox">
        <h2>Ask the knowledge base</h2>
        <p className="muted">Answers come from the local corpus (<code>rag/corpus/</code>) via the on-premise LLM,
          cite their sources as [n], and say so when the corpus has no answer.</p>
        <details className="scope">
          <summary>What can I ask?</summary>
          <ul className="muted">
            <li><b>Waste sorting (DE rules):</b> Restmüll, Gelber Sack, Papiertonne, Glascontainer, Wertstoffhof - what goes where.</li>
            <li><b>Electronics &amp; batteries:</b> e-waste rules (ElektroG), lithium cells (BattG, taping poles, damaged cells), desoldering parts, reusing motors and cables.</li>
            <li><b>Plastics &amp; 3D printing:</b> PLA / PETG / ABS disposal &amp; recycling, failed prints, filament spools, acrylic (and why PVC is never lasered).</li>
            <li><b>Metal &amp; wood:</b> scrap metal, sorting screws, aluminium profiles, waste-wood categories A I-IV, reusing plywood/MDF offcuts.</li>
            <li><b>Reuse &amp; condition:</b> reuse-first hierarchy, judging if a part is still usable.</li>
            <li><b>Live stock:</b> a snapshot of the current inventory (counts per object class, statuses, and the correct
              bin per material) is included with every question - ask “how many screws do we have?” or “which bin for the PCBs?”.</li>
          </ul>
          <p className="muted">Everything else is answered ONLY from these sources - questions outside them are declined
            instead of guessed. Full tables and charts live on the <b>Inventory</b> tab.</p>
        </details>
        <form onSubmit={(e) => { e.preventDefault(); submit(q); }}>
          <textarea value={q} onChange={(e) => setQ(e.target.value)} rows={3}
            placeholder="e.g. Wohin mit Acrylglas-Resten? / What belongs in the battery box?" aria-label="question" />
          <div className="toolbar">
            <button className="btn" type="submit" disabled={busy || !q.trim()}>{busy ? "Asking local model…" : "Ask"}</button>
            <select value={lang} onChange={(e) => setLang(e.target.value)} aria-label="answer language">
              <option value="de">Deutsch</option><option value="en">English</option>
            </select>
            <span className="muted">{busy ? "retrieval + generation runs locally; first call after idle can take longer" : ""}</span>
          </div>
        </form>
        <div className="chips">
          {EXAMPLES.map((e) => <button key={e} className="chipbtn" onClick={() => submit(e)} disabled={busy}>{e}</button>)}
        </div>
        {err && <p className="err">{err}</p>}
      </div>
      {history.map((h) => (
        <div key={h.t} className="card qa">
          <p className="q">“{h.q}”</p>
          <div className="answer">{h.answer}</div>
          <ol className="sources">{h.sources.map((s) => <li key={s.n}>{s.doc} › {s.section}</li>)}</ol>
          <p className="muted meta">{h.model} · {new Date(h.t).toLocaleTimeString()}</p>
        </div>
      ))}
      {history.length === 0 && <p className="muted center">Session history appears here. Nothing is stored on the server for free-form questions;
        per-item suggestions on the detail pages are persisted.</p>}
    </section>
  );
}
