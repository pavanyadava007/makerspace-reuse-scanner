import type { LiveDet } from "../api";
import { materialHue } from "../api";
export default function Overlay({ w, h, dets, link = true }: { w: number; h: number; dets: LiveDet[]; link?: boolean }) {
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="xMidYMid meet" aria-hidden>
      {dets.map((d, i) => {
        const [x1, y1, x2, y2] = d.xyxy; const c = materialHue[d.material ?? ""] ?? "var(--other)";
        const label = `${d.cls} ${(d.conf * 100).toFixed(0)}%${d.material ? " · " + d.material : ""}`;
        const g = (<g key={i}>
          <rect className="box" x={x1} y={y1} width={x2 - x1} height={y2 - y1} style={{ stroke: c }} />
          <rect className="tagbg" x={x1} y={Math.max(0, y1 - 18)} width={label.length * 6.6 + 10} height={18} style={{ fill: c }} />
          <text className="tag" x={x1 + 5} y={Math.max(13, y1 - 5)}>{label}</text>
        </g>);
        return link && d.item_id ? <a key={i} href={`/items/${d.item_id}`}>{g}</a> : g;
      })}
    </svg>
  );
}
