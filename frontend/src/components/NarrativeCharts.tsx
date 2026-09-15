import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { NarrativeOverview } from "../api";
import { AXIS, CHART_MARGIN, GRID, OKABE_ITO, TICK, seriesColor } from "../chartTheme";
import { shortChartDate } from "../display";
import { ChartFrame } from "./ChartsPanel";

function tickDate(iso: string) {
  if (/^\d{4}-\d{2}$/.test(iso)) {
    const d = new Date(`${iso}-01T12:00:00`);
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleDateString("es-MX", { month: "short", year: "2-digit" });
    }
  }
  return shortChartDate(iso);
}

function bucketPoints(points: { day: string; count: number }[]) {
  const live = points.filter((p) => Number(p.count) > 0 && p.day);
  if (!live.length) return [] as { day: string; count: number; label: string }[];
  const first = new Date(`${live[0].day.slice(0, 10)}T12:00:00`);
  const last = new Date(`${live[live.length - 1].day.slice(0, 10)}T12:00:00`);
  const span = Number.isNaN(first.getTime()) || Number.isNaN(last.getTime()) ? 0 : (last.getTime() - first.getTime()) / 86400000;
  const byMonth = span > 90 || live.length > 18;
  if (!byMonth) {
    return live.map((p) => ({ day: p.day.slice(0, 10), count: Number(p.count), label: tickDate(p.day.slice(0, 10)) }));
  }
  const months = new Map<string, number>();
  for (const p of live) {
    const key = p.day.slice(0, 7);
    months.set(key, (months.get(key) || 0) + Number(p.count));
  }
  return [...months.entries()].map(([day, count]) => ({ day, count, label: tickDate(day) }));
}

function SignalTip({
  active,
  payload,
  onGo,
}: {
  active?: boolean;
  payload?: { value?: number; payload?: { term: string; count: number; pct: number; category: string } }[];
  onGo: (term: string) => void;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload;
  if (!row) return null;
  return (
    <div className="chart-tip door-tip">
      <strong>
        {row.term} · {row.count} menciones · {row.pct}%
      </strong>
      <span className="muted">{row.category}. Es una señal, no un veredicto.</span>
      <button type="button" onClick={() => onGo(row.term)}>
        Ver notas con “{row.term}”
      </button>
    </div>
  );
}

function SeriesTip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value?: number; name?: string; color?: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const rows = payload.filter((p) => Number(p.value) > 0);
  if (!rows.length) return null;
  return (
    <div className="chart-tip">
      <strong>{label}</strong>
      {rows.map((p) => (
        <p key={p.name}>
          <i className="swatch" style={{ background: p.color }} /> {p.name}: {p.value}
        </p>
      ))}
    </div>
  );
}

export default function NarrativeCharts({ data }: { data: NarrativeOverview }) {
  const navigate = useNavigate();
  const bank = data.bank || {};

  const signals = useMemo(() => {
    const rows = (data.cloud || []).filter((c) => c.count > 0);
    const total = rows.reduce((s, r) => s + r.count, 0) || 1;
    const cats = Object.entries(bank);
    return rows.slice(0, 14).map((row) => {
      const hit = cats.find(([, cat]) => cat.terms.some((t) => t.toLowerCase() === row.term.toLowerCase()));
      const category = hit?.[1]?.label || hit?.[0] || "otras";
      const pct = Math.round((row.count / total) * 100);
      return { term: row.term, count: row.count, pct, barLabel: `${row.count} · ${pct}%`, category };
    });
  }, [data.cloud, bank]);

  const stories = useMemo(() => (data.narratives || []).filter((n) => (n.series || []).some((p) => p.count > 0)).slice(0, 4), [data.narratives]);

  const timeline = useMemo(() => {
    const buckets = stories.map((n) => ({ n, points: bucketPoints(n.series || []) }));
    const days = new Set<string>();
    for (const b of buckets) for (const p of b.points) days.add(p.day);
    const ordered = [...days].sort();
    return ordered.map((day) => {
      const row: Record<string, string | number> = { day, label: tickDate(day) };
      for (const b of buckets) {
        row[b.n.narrative_id] = b.points.find((p) => p.day === day)?.count || 0;
      }
      return row;
    });
  }, [stories]);

  const peak = useMemo(() => {
    if (!timeline.length || !stories.length) return null;
    let best = { day: "", count: 0, label: "" };
    for (const row of timeline) {
      for (const s of stories) {
        const n = Number(row[s.narrative_id] || 0);
        if (n > best.count) best = { day: String(row.label), count: n, label: s.label };
      }
    }
    return best.count ? best : null;
  }, [timeline, stories]);

  function goTerm(term: string) {
    navigate({ pathname: "/", search: `?q=${encodeURIComponent(term)}` });
  }

  const barH = Math.max(260, signals.length * 36 + 20);

  return (
    <div className="chart-stack">
      <ChartFrame
        title="Señales más frecuentes"
        howto={[
          "Cada barra es un término del banco, no un veredicto.",
          "El número es cuántas veces aparece en el recorte; el % es su parte entre estas señales.",
          "Pulsa una barra para ver las notas que lo mencionan en la sala.",
        ]}
        caption={signals[0] ? `La más citada ahora es “${signals[0].term}” (${signals[0].count}). Peso no es malicia.` : null}
      >
        {signals.length ? (
          <ResponsiveContainer width="100%" height={barH}>
            <BarChart data={signals} layout="vertical" margin={{ ...CHART_MARGIN, left: 4, right: 72 }}>
              <CartesianGrid stroke={GRID} horizontal={false} />
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="term" width={168} tick={TICK} interval={0} />
              <Tooltip content={<SignalTip onGo={goTerm} />} />
              <Bar dataKey="count" name="Menciones" radius={[0, 4, 4, 0]} cursor="pointer" onClick={(row) => goTerm(String((row as { term?: string })?.term || ""))}>
                {signals.map((row, i) => (
                  <Cell key={row.term} fill={seriesColor(row.category, i)} />
                ))}
                <LabelList dataKey="barLabel" position="right" fill={AXIS} fontSize={12} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted">Sin términos del banco en este recorte.</p>
        )}
      </ChartFrame>

      <ChartFrame
        title="Cómo evolucionan los relatos"
        howto={[
          "Cada línea es un relato agrupado, no una enfermedad.",
          "El eje es tiempo real de las notas (meses si el recorte es largo); se ocultan los años vacíos.",
          "Un pico pide atención. No declara que el relato sea falso.",
        ]}
        caption={
          peak
            ? `Pico: ${peak.label} el ${peak.day} (${peak.count} notas).`
            : stories.length
              ? null
              : "Aún no hay serie temporal para estos relatos."
        }
      >
        {timeline.length && stories.length ? (
          <ResponsiveContainer width="100%" height={320}>
            {stories.length === 1 ? (
              <AreaChart data={timeline} margin={{ ...CHART_MARGIN, top: 16, right: 16 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="label" tick={TICK} interval="preserveStartEnd" minTickGap={28} />
                <YAxis tick={TICK} allowDecimals={false} width={36} />
                <Tooltip content={<SeriesTip />} />
                <Legend wrapperStyle={{ color: AXIS, fontSize: 12 }} />
                <Area
                  type="monotone"
                  dataKey={stories[0].narrative_id}
                  name={stories[0].label}
                  stroke={OKABE_ITO[0]}
                  fill={OKABE_ITO[0]}
                  fillOpacity={0.22}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              </AreaChart>
            ) : (
              <LineChart data={timeline} margin={{ ...CHART_MARGIN, top: 16, right: 16 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="label" tick={TICK} interval="preserveStartEnd" minTickGap={28} />
                <YAxis tick={TICK} allowDecimals={false} width={36} />
                <Tooltip content={<SeriesTip />} />
                <Legend wrapperStyle={{ color: AXIS, fontSize: 12 }} />
                {stories.map((n, i) => (
                  <Line
                    key={n.narrative_id}
                    type="monotone"
                    dataKey={n.narrative_id}
                    name={n.label}
                    stroke={OKABE_ITO[i % OKABE_ITO.length]}
                    strokeWidth={2.2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                ))}
              </LineChart>
            )}
          </ResponsiveContainer>
        ) : (
          <p className="muted">No hay fechas con volumen para dibujar la evolución.</p>
        )}
      </ChartFrame>
    </div>
  );
}
