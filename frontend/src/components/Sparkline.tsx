export function Sparkline({ values, color = "#00bcd4" }: { values: number[]; color?: string }) {
  const nums = values.length ? values : [0];
  const max = Math.max(...nums, 1);
  const w = 88;
  const h = 28;
  const step = nums.length > 1 ? w / (nums.length - 1) : w;
  const pts = nums.map((v, i) => `${i * step},${h - (v / max) * (h - 4) - 2}`).join(" ");
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} width={w} height={h} aria-hidden>
      <polyline fill="none" stroke={color} strokeWidth="2" points={pts} />
    </svg>
  );
}

export function MiniBars({ values, color = "#26c6a0" }: { values: number[]; color?: string }) {
  const nums = values.length ? values : [0];
  const max = Math.max(...nums, 1);
  return (
    <div className="mini-bars" aria-hidden>
      {nums.map((v, i) => (
        <span key={i} style={{ height: `${Math.max(12, (v / max) * 100)}%`, background: color }} />
      ))}
    </div>
  );
}
