import { useMemo, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartBundle, ChartFilter } from "../api";
import { AXIS, CHART_MARGIN, DISEASE_COLOR, GRID, ORIGIN_COLOR, TICK, VERDICT_COLOR, seriesColor } from "../chartTheme";
import { shortChartDate, verdictLabel } from "../display";
import { filtersToSearch, type ObservatoryFilters } from "../filters";
import LeerMas from "./LeerMas";

type Slice = { id: string; name?: string; label: string; count: number; filter?: ChartFilter; pct?: number; barLabel?: string };
type TipRow = Slice & { sample_titles?: string[]; unit?: string };

type Props = {
  data: ChartBundle | null;
  filters: ObservatoryFilters;
  onPatch: (patch: Partial<ObservatoryFilters>) => void;
};

export function ChartFrame({
  title,
  howto,
  caption,
  children,
}: {
  title: string;
  howto: [string, string, string];
  caption?: string | null;
  children: ReactNode;
}) {
  return (
    <section className="viz">
      <h3>{title}</h3>
      <p className="chart-howto-label">Cómo leerlo</p>
      <LeerMas maxItems={1} className="chart-howto-wrap">
        {howto.map((line) => (
          <p key={line} className="chart-explain">
            {line}
          </p>
        ))}
      </LeerMas>
      <div className="chart-box">{children}</div>
      {caption ? <p className="chart-foot">{caption}</p> : null}
    </section>
  );
}

function EmptyChart({
  dbEmpty,
  onClear,
}: {
  dbEmpty?: boolean;
  onClear: () => void;
}) {
  if (dbEmpty) {
    return (
      <section className="viz wide chart-empty">
        <h3>Aún no hay minería</h3>
        <p>No hay notas todavía. Ejecuta un ciclo desde la sala.</p>
      </section>
    );
  }
  return (
    <section className="viz wide chart-empty">
      <h3>Este recorte no deja notas</h3>
      <p>Prueba a quitar filtros para volver a ver el panorama.</p>
      <button type="button" className="run" onClick={onClear}>
        Limpiar filtros
      </button>
    </section>
  );
}

function salaSearch(filters: ObservatoryFilters, extra?: ChartFilter) {
  return filtersToSearch({
    ...filters,
    page: 1,
    disease: extra?.disease != null ? String(extra.disease) : filters.disease,
    from: extra?.from != null ? String(extra.from) : filters.from,
    to: extra?.to != null ? String(extra.to) : filters.to,
    country: extra?.country != null ? String(extra.country) : filters.country,
    verdict: extra?.verdict != null ? String(extra.verdict) : filters.verdict,
    source: extra?.source != null ? String(extra.source) : filters.source,
    origin: extra?.origin != null ? String(extra.origin) : filters.origin,
    stance: extra?.stance != null ? String(extra.stance) : filters.stance,
    raw_format: extra?.raw_format != null ? String(extra.raw_format) : filters.raw_format,
    risk_min: extra?.risk_min != null ? Number(extra.risk_min) : filters.risk_min,
    risk_max: extra?.risk_max != null ? Number(extra.risk_max) : filters.risk_max,
    risk_null: extra?.risk_null === true,
  });
}

function withPct(rows: Slice[], total: number): Slice[] {
  const base = total > 0 ? total : rows.reduce((s, r) => s + (Number(r.count) || 0), 0);
  return rows
    .filter((r) => Number(r.count) > 0)
    .map((r) => {
      const pct = base > 0 ? Math.round((Number(r.count) / base) * 100) : 0;
      return { ...r, pct, barLabel: `${r.count} · ${pct}%` };
    })
    .sort((a, b) => Number(b.count) - Number(a.count));
}

function weekMonday(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return d.toISOString().slice(0, 10);
}

function ingestCaption(data: ChartBundle, n: number): string | null {
  const days = (data.by_day?.length ? data.by_day : data.volume_by_day || []).filter((d) => Number(d.count) > 0);
  if (days.length < 2 || n < 4) return null;
  const weeks = new Map<string, number>();
  for (const day of days) {
    const key = weekMonday(String(day.day));
    weeks.set(key, (weeks.get(key) || 0) + Number(day.count || 0));
  }
  if (weeks.size < 2) return null;
  let topKey = "";
  let topN = 0;
  for (const [key, value] of weeks) {
    if (value > topN) {
      topKey = key;
      topN = value;
    }
  }
  if (!topKey || topN / n < 0.45) return null;
  const mineHit = (data.annotations || []).some((a) => a.kind === "mine" && weekMonday(a.day) === topKey);
  if (!mineHit) return null;
  return `La mayoría se concentró en la semana del ${shortChartDate(topKey)}: suele ser el día en que el sistema las guardó, no siempre el día de publicación.`;
}

function DoorTip({
  active,
  payload,
  unit,
  onGo,
}: {
  active?: boolean;
  payload?: { value?: number; name?: string; payload?: TipRow }[];
  unit: string;
  onGo: (filter?: ChartFilter) => void;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload || { id: "", label: "", count: 0 };
  const count = Number(row.count ?? payload[0]?.value ?? 0);
  if (!count) return null;
  const pct = row.pct != null ? ` · ${row.pct}%` : "";
  return (
    <div className="chart-tip door-tip">
      <strong>
        {row.label || payload[0]?.name} · {count} {unit}
        {pct}
      </strong>
      <button type="button" onClick={() => onGo(row.filter)}>
        Ver las {count} en la sala
      </button>
    </div>
  );
}

function pieLabel(props: { name?: string; percent?: number; value?: number }) {
  const value = Number(props.value || 0);
  if (!value) return "";
  const pct = Math.round((props.percent || 0) * 100);
  if (pct <= 0) return "";
  return `${props.name} ${pct}%`;
}

export default function ChartsPanel({ data, filters, onPatch }: Props) {
  const navigate = useNavigate();

  function goSala(extra?: ChartFilter) {
    navigate({ pathname: "/", search: salaSearch(filters, extra) });
  }

  const n = data?.n ?? 0;
  const diseases = useMemo(
    () => withPct(data?.volume_by_disease || [], n),
    [data?.volume_by_disease, n]
  );
  const origins = useMemo(
    () => withPct(data?.volume_by_origin || [], n),
    [data?.volume_by_origin, n]
  );
  const verdicts = useMemo(
    () =>
      withPct(
        (data?.volume_by_verdict || []).map((row) => ({
          ...row,
          label: verdictLabel(row.label || row.name || row.id),
        })),
        n
      ),
    [data?.volume_by_verdict, n]
  );

  if (!data) return <p className="muted">Cargando gráficas…</p>;
  if (data.empty || !n) {
    return (
      <EmptyChart
        dbEmpty={data.db_empty}
        onClear={() =>
          onPatch({
            disease: null,
            from: null,
            to: null,
            country: null,
            verdict: null,
            source: null,
            q: null,
            origin: null,
            stance: null,
          })
        }
      />
    );
  }

  const caption = ingestCaption(data, n);
  const rankH = Math.max(240, diseases.length * 44 + 24);

  return (
    <div className="chart-stack">
      <ChartFrame
        title="¿De qué enfermedades hablan?"
        howto={[
          "Cada barra es una enfermedad, no un día.",
          "El número es cuántas notas la mencionan; el % es su parte del total.",
          "Una nota puede hablar de más de una. Pulsa una barra para verlas en la sala.",
        ]}
        caption={caption}
      >
        {diseases.length ? (
          <ResponsiveContainer width="100%" height={rankH}>
            <BarChart data={diseases} layout="vertical" margin={{ ...CHART_MARGIN, left: 8, right: 72 }}>
              <CartesianGrid stroke={GRID} horizontal={false} />
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="label" width={150} tick={TICK} interval={0} />
              <Tooltip content={<DoorTip unit="notas" onGo={goSala} />} />
              <Bar dataKey="count" name="Notas" radius={[0, 4, 4, 0]} cursor="pointer" onClick={(row) => goSala((row as Slice)?.filter)}>
                {diseases.map((row, i) => (
                  <Cell key={row.id} fill={DISEASE_COLOR[row.id] || seriesColor(row.id, i)} />
                ))}
                <LabelList dataKey="barLabel" position="right" fill={AXIS} fontSize={12} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted">No se identificó ninguna enfermedad en este recorte.</p>
        )}
      </ChartFrame>

      <ChartFrame
        title="¿De dónde sale el contenido?"
        howto={[
          "Oficial: gobiernos y organismos (SENASICA, OMSA, CDC…).",
          "Científico: artículos y bases académicas. Redes y YouTube son publicaciones en redes o video.",
          "Prensa son medios de noticias. Pulsa una barra para ver solo ese origen.",
        ]}
      >
        {origins.length ? (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={origins} margin={{ ...CHART_MARGIN, top: 20 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="label" tick={TICK} interval={0} height={46} />
              <YAxis tick={TICK} allowDecimals={false} width={40} />
              <Tooltip content={<DoorTip unit="notas" onGo={goSala} />} />
              <Bar dataKey="count" name="Notas" radius={[4, 4, 0, 0]} cursor="pointer" onClick={(row) => goSala((row as Slice)?.filter)}>
                {origins.map((row) => (
                  <Cell key={row.id} fill={ORIGIN_COLOR[row.id] || "#7a7a7a"} />
                ))}
                <LabelList dataKey="barLabel" position="top" fill={AXIS} fontSize={12} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted">No hay origen clasificado en este recorte.</p>
        )}
      </ChartFrame>

      <ChartFrame
        title="¿Qué concluyó el análisis?"
        howto={[
          "Respaldado: hay evidencia a favor. Contradicho: la evidencia lo niega.",
          "Insuficiente: no alcanza para decidir. Revisión humana: alguien debe mirarlo.",
          "Pulsa un color para abrir esos casos en la sala.",
        ]}
        caption={data.risk_note || undefined}
      >
        {verdicts.length ? (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={verdicts}
                dataKey="count"
                nameKey="label"
                innerRadius={58}
                outerRadius={92}
                paddingAngle={3}
                label={pieLabel}
                labelLine
                onClick={(row) => goSala((row as Slice)?.filter)}
              >
                {verdicts.map((row) => (
                  <Cell key={row.id} fill={VERDICT_COLOR[row.id] || VERDICT_COLOR[row.label] || "#7a7a7a"} />
                ))}
              </Pie>
              <Tooltip content={<DoorTip unit="notas" onGo={goSala} />} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted">Todavía no hay un veredicto en este recorte.</p>
        )}
      </ChartFrame>
    </div>
  );
}
