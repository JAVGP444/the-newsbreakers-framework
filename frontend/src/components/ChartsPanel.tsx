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
import { shortChartDate, verdictLabel, diseaseUiLabel, kindLabel, type SourceKind } from "../display";
import { filtersToSearch, type ObservatoryFilters } from "../filters";
import { useLocale } from "../locale";
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
  const { t } = useLocale();
  return (
    <section className="viz">
      <h3>{title}</h3>
      <p className="chart-howto-label">{t("charts.howto")}</p>
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
  const { t } = useLocale();
  if (dbEmpty) {
    return (
      <section className="viz wide chart-empty">
        <h3>{t("charts.noMine")}</h3>
        <p>{t("charts.noMineBody")}</p>
      </section>
    );
  }
  return (
    <section className="viz wide chart-empty">
      <h3>{t("charts.noCut")}</h3>
      <p>{t("charts.noCutBody")}</p>
      <button type="button" className="run" onClick={onClear}>
        {t("filter.clear")}
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

function ingestCaption(data: ChartBundle, n: number, lang: "es" | "en", t: (k: string, v?: Record<string, string | number>) => string): string | null {
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
  return t("charts.ingest", { date: shortChartDate(topKey, lang) });
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
  const { t } = useLocale();
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
        {t("charts.goSala", { n: count })}
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
  const { t, lang } = useLocale();

  function goSala(extra?: ChartFilter) {
    navigate({ pathname: "/", search: salaSearch(filters, extra) });
  }

  const n = data?.n ?? 0;
  const diseases = useMemo(
    () =>
      withPct(
        (data?.volume_by_disease || []).map((row) => ({
          ...row,
          label: diseaseUiLabel(row.id, row.label || row.name, lang),
        })),
        n
      ),
    [data?.volume_by_disease, n, lang]
  );
  const origins = useMemo(
    () =>
      withPct(
        (data?.volume_by_origin || []).map((row) => ({
          ...row,
          label: kindLabel((row.id as SourceKind) || "prensa", lang) || row.label || row.name || row.id,
        })),
        n
      ),
    [data?.volume_by_origin, n, lang]
  );
  const verdicts = useMemo(
    () =>
      withPct(
        (data?.volume_by_verdict || []).map((row) => ({
          ...row,
          label: verdictLabel(row.label || row.name || row.id, lang),
        })),
        n
      ),
    [data?.volume_by_verdict, n, lang]
  );

  if (!data) return <p className="muted">{t("charts.loading")}</p>;
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

  const caption = ingestCaption(data, n, lang, t);
  const rankH = Math.max(240, diseases.length * 44 + 24);
  const notesUnit = t("charts.notes");
  const notesName = t("charts.notesName");

  return (
    <div className="chart-stack">
      <ChartFrame
        title={t("charts.diseaseTitle")}
        howto={[t("charts.disease1"), t("charts.disease2"), t("charts.disease3")]}
        caption={caption}
      >
        {diseases.length ? (
          <ResponsiveContainer width="100%" height={rankH}>
            <BarChart data={diseases} layout="vertical" margin={{ ...CHART_MARGIN, left: 8, right: 72 }}>
              <CartesianGrid stroke={GRID} horizontal={false} />
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="label" width={150} tick={TICK} interval={0} />
              <Tooltip content={<DoorTip unit={notesUnit} onGo={goSala} />} />
              <Bar dataKey="count" name={notesName} radius={[0, 4, 4, 0]} cursor="pointer" onClick={(row) => goSala((row as unknown as Slice)?.filter)}>
                {diseases.map((row, i) => (
                  <Cell key={row.id} fill={DISEASE_COLOR[row.id] || seriesColor(row.id, i)} />
                ))}
                <LabelList dataKey="barLabel" position="right" fill={AXIS} fontSize={12} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted">{t("charts.noDisease")}</p>
        )}
      </ChartFrame>

      <ChartFrame
        title={t("charts.originTitle")}
        howto={[t("charts.origin1"), t("charts.origin2"), t("charts.origin3")]}
      >
        {origins.length ? (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={origins} margin={{ ...CHART_MARGIN, top: 20 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="label" tick={TICK} interval={0} height={46} />
              <YAxis tick={TICK} allowDecimals={false} width={40} />
              <Tooltip content={<DoorTip unit={notesUnit} onGo={goSala} />} />
              <Bar dataKey="count" name={notesName} radius={[4, 4, 0, 0]} cursor="pointer" onClick={(row) => goSala((row as unknown as Slice)?.filter)}>
                {origins.map((row) => (
                  <Cell key={row.id} fill={ORIGIN_COLOR[row.id] || "#7a7a7a"} />
                ))}
                <LabelList dataKey="barLabel" position="top" fill={AXIS} fontSize={12} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted">{t("charts.noOrigin")}</p>
        )}
      </ChartFrame>

      <ChartFrame
        title={t("charts.verdictTitle")}
        howto={[t("charts.verdict1"), t("charts.verdict2"), t("charts.verdict3")]}
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
                onClick={(row) => goSala((row as unknown as Slice)?.filter)}
              >
                {verdicts.map((row) => (
                  <Cell key={row.id} fill={VERDICT_COLOR[row.id] || VERDICT_COLOR[row.label] || "#7a7a7a"} />
                ))}
              </Pie>
              <Tooltip content={<DoorTip unit={notesUnit} onGo={goSala} />} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted">{t("charts.noVerdict")}</p>
        )}
      </ChartFrame>
    </div>
  );
}
