// Single-series magnitude → bar list: one hue, labels/values in ink tokens, value at the row end.
// It doubles as its own table view, so identity never rides on color.
export default function BarList({ title, data, unit }: { title: string; data: Record<string, number>; unit?: string }) {
  const rows = Object.entries(data);
  const max = Math.max(1, ...rows.map(([, v]) => v));
  return (
    <section className="card barlist" aria-label={title}>
      <h2>{title}</h2>
      {rows.length === 0 && <p className="muted">No data yet.</p>}
      {rows.map(([k, v]) => (
        <div className="bar-row" key={k} title={`${k}: ${v}${unit ?? ""}`}>
          <span className="bar-label">{k.replace(/_/g, " ")}</span>
          <span className="bar-track"><i style={{ width: `${(v / max) * 100}%` }} /></span>
          <span className="bar-value num">{v}</span>
        </div>
      ))}
    </section>
  );
}
