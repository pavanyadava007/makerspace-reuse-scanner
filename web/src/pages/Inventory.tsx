import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import BarList from "../components/BarList";
import { api, materialHue, type Item, type Material, type Stats } from "../api";

type SortKey = "updated_at" | "label" | "quantity" | "status";

export default function Inventory() {
  const [items, setItems] = useState<Item[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [mats, setMats] = useState<Material[]>([]);
  const [status, setStatus] = useState(""); const [material, setMaterial] = useState(""); const [q, setQ] = useState("");
  const [sort, setSort] = useState<SortKey>("updated_at"); const [dir, setDir] = useState<1 | -1>(-1);
  const [err, setErr] = useState(""); const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState({ label: "", material_id: "", quantity: 1, location: "bench-1" });

  const load = () => {
    const f: Record<string, string> = {}; if (status) f.status = status; if (material) f.material = material;
    Promise.all([api.items(f), api.stats()]).then(([i, s]) => { setItems(i); setStats(s); setErr(""); }).catch((e) => setErr(String(e)));
  };
  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, [status, material]);
  useEffect(() => { api.materials().then(setMats).catch(() => undefined); }, []);

  const flip = (k: SortKey) => { if (sort === k) setDir((d) => (d === 1 ? -1 : 1)); else { setSort(k); setDir(k === "updated_at" ? -1 : 1); } };
  const arrow = (k: SortKey) => (sort === k ? (dir === 1 ? " ↑" : " ↓") : "");
  const rows = items
    .filter((i) => !q || i.label.includes(q.toLowerCase()) || i.material?.name.toLowerCase().includes(q.toLowerCase()) || i.location?.includes(q))
    .sort((a, b) => {
      const va = a[sort] ?? "", vb = b[sort] ?? "";
      return (typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb))) * dir;
    });

  const add = () => {
    if (!draft.label.trim()) return;
    api.create({ label: draft.label.trim().replace(/ /g, "_"), material_id: draft.material_id ? Number(draft.material_id) : undefined,
                 quantity: draft.quantity, location: draft.location || undefined })
      .then(() => { setAdding(false); setDraft({ label: "", material_id: "", quantity: 1, location: "bench-1" }); load(); })
      .catch((e) => setErr(String(e)));
  };
  const remove = (i: Item) => {
    if (!window.confirm(`Delete item #${i.id} (${i.label})? Its detection history is kept but unlinked.`)) return;
    api.del(i.id).then(load).catch((e) => setErr(String(e)));
  };

  return (
    <section className="inv">
      {stats && <div className="tiles">
        <div className="tile"><b className="num">{stats.items}</b><span>items</span></div>
        <div className="tile"><b className="num">{stats.detections}</b><span>detections stored</span></div>
        <div className="tile ok"><b className="num">{stats.by_status.available ?? 0}</b><span>available</span></div>
        <div className="tile warn"><b className="num">{stats.by_status.reserved ?? 0}</b><span>reserved</span></div>
        <div className="tile"><b className="num">{stats.by_status.reused ?? 0}</b><span>reused</span></div>
        <div className="tile bad"><b className="num">{stats.by_status.disposed ?? 0}</b><span>disposed</span></div>
      </div>}
      {stats && <div className="charts">
        <BarList title="Top labels (items)" data={stats.top_labels} />
        <BarList title="Material categories (items)" data={stats.by_category} />
      </div>}

      <div className="toolbar">
        <input placeholder="Filter by label, material, location" value={q} onChange={(e) => setQ(e.target.value)} aria-label="filter" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="status filter">
          <option value="">All statuses</option><option>available</option><option>reserved</option><option>reused</option><option>disposed</option>
        </select>
        <select value={material} onChange={(e) => setMaterial(e.target.value)} aria-label="material filter">
          <option value="">All materials</option>{mats.map((m) => <option key={m.id} value={m.name}>{m.name}</option>)}
        </select>
        <button className="btn ghost" onClick={() => setAdding((a) => !a)}>{adding ? "Cancel" : "+ Add item"}</button>
        <button className="btn danger" style={{ marginLeft: "auto" }} onClick={() => {
          if (window.confirm("Clear the ENTIRE inventory? Deletes all items, detections, suggestions and saved frames. Materials and the knowledge base are kept.")) {
            api.reset().then((r) => { window.alert(`Deleted ${r.deleted.items} items, ${r.deleted.detections} detections.`); load(); })
              .catch((e) => setErr(String(e)));
          }
        }}>Clear inventory</button>
      </div>

      {adding && <div className="card addform">
        <input placeholder="label, e.g. wood_offcut" value={draft.label} onChange={(e) => setDraft({ ...draft, label: e.target.value })} aria-label="label" />
        <select value={draft.material_id} onChange={(e) => setDraft({ ...draft, material_id: e.target.value })} aria-label="material">
          <option value="">material unknown</option>{mats.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
        <input type="number" min={1} value={draft.quantity} onChange={(e) => setDraft({ ...draft, quantity: Number(e.target.value) })} aria-label="quantity" />
        <input placeholder="location" value={draft.location} onChange={(e) => setDraft({ ...draft, location: e.target.value })} aria-label="location" />
        <button className="btn" onClick={add} disabled={!draft.label.trim()}>Save</button>
      </div>}

      {err && <p className="err">Could not load inventory: {err}</p>}
      <div className="card tablewrap">
        <table>
          <thead><tr>
            <th><button className="th" onClick={() => flip("label")}>Item{arrow("label")}</button></th>
            <th>Material</th><th>Condition</th>
            <th className="num"><button className="th" onClick={() => flip("quantity")}>Qty{arrow("quantity")}</button></th>
            <th>Location</th>
            <th><button className="th" onClick={() => flip("status")}>Status{arrow("status")}</button></th>
            <th className="num"><button className="th" onClick={() => flip("updated_at")}>Last seen{arrow("updated_at")}</button></th>
            <th aria-label="actions" />
          </tr></thead>
          <tbody>
            {rows.map((i) => <tr key={i.id}>
              <td><Link to={`/items/${i.id}`}>{i.label.replace(/_/g, " ")}</Link></td>
              <td>{i.material ? <span className="chip" style={{ background: materialHue[i.material.name] }}
                title={i.material.disposal_de ? `bin: ${i.material.disposal_de}` : undefined}>{i.material.name}</span> : <span className="muted">unknown</span>}</td>
              <td>{i.condition ?? "-"}</td><td className="num">{i.quantity}</td><td>{i.location ?? "-"}</td>
              <td className={`status-${i.status}`}>{i.status}</td>
              <td className="num muted">{new Date(i.updated_at).toLocaleString()}</td>
              <td><button className="btn danger sm" onClick={() => remove(i)} aria-label={`delete item ${i.id}`}>delete</button></td>
            </tr>)}
            {rows.length === 0 && !err && <tr><td colSpan={8} className="muted">Nothing here yet. Detections from the live feed create items automatically, or use “Add item”.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}
