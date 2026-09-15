import { Fragment, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { API, api, type CnnMetrics, type CnnPredict, type CnnRealSample } from "./api";
import AppHeader from "./components/AppHeader";
import { SoftmaxBars } from "./components/ImageCard";
import LeerMas from "./components/LeerMas";
import { useLocale } from "./locale";

const TICK = { fill: "#9fb4c4", fontSize: 12 };
const TOOL = { background: "#0b1724", border: "1px solid #1e3a4c", color: "#e8f4f8" };

export default function CnnLab() {
  const { t } = useLocale();
  const types = [
    "OFFICIAL_DOCUMENT",
    "NEWS_SCREENSHOT",
    "SOCIAL_MEDIA",
    "MEME",
    "INFOGRAPHIC",
    "ANIMAL_HEALTH_CONTENT",
    "PHOTOGRAPH",
    "POTENTIALLY_MANIPULATED",
  ].map((id) => ({ id, label: t(`cnn.type.${id}`), use: t(`cnn.use.${id}`) }));
  const [metrics, setMetrics] = useState<CnnMetrics | null>(null);
  const [samples, setSamples] = useState<CnnRealSample[]>([]);
  const [samplesLoaded, setSamplesLoaded] = useState(false);
  const [err, setErr] = useState("");
  const [pred, setPred] = useState<CnnPredict | null>(null);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState("");

  useEffect(() => {
    api
      .cnnMetrics()
      .then(setMetrics)
      .catch(() => setErr(t("cnn.metricsFail")));
    api
      .cnnSamples(12)
      .then((res) => setSamples(res.samples || []))
      .catch(() => setSamples([]))
      .finally(() => setSamplesLoaded(true));
  }, []);

  const historyRows = useMemo(() => {
    const h = metrics?.history;
    if (!h) return [];
    const n = Math.max(h.acc?.length || 0, h.loss?.length || 0);
    return Array.from({ length: n }, (_, i) => ({
      epoch: i + 1,
      acc: h.acc?.[i],
      val_acc: h.val_acc?.[i],
      loss: h.loss?.[i],
      val_loss: h.val_loss?.[i],
    }));
  }, [metrics]);

  async function runFile(file: File) {
    setBusy(true);
    setErr("");
    setPreview(URL.createObjectURL(file));
    try {
      setPred(await api.cnnPredictFile(file));
    } catch {
      setErr(t("cnn.predFail"));
    } finally {
      setBusy(false);
    }
  }

  async function runSample(id: string) {
    setBusy(true);
    setErr("");
    const sample = samples.find((s) => s.id === id);
    const path = sample?.url || `/cnn/samples/${encodeURIComponent(id)}`;
    setPreview(path.startsWith("http") ? path : `${API}${path}`);
    try {
      setPred(await api.cnnPredictSample(id));
    } catch {
      setErr(t("cnn.sampleFail"));
    } finally {
      setBusy(false);
    }
  }

  const labels = metrics?.confusion_matrix?.labels || [];
  const matrix = metrics?.confusion_matrix?.matrix || [];
  const maxCell = Math.max(1, ...matrix.flat());
  const prod = pred?.production;
  const prodAvailable = Boolean(prod?.available ?? (pred?.encoder && pred.encoder !== "unavailable" && pred.encoder !== "academic_cnn"));
  const prodLabel = prod?.label_es || pred?.label_es;
  const prodConf = prod?.confidence ?? pred?.confidence;
  const prodScores = prod?.scores || pred?.scores;
  const prodEncoder = prod?.encoder || pred?.encoder;
  const academic = pred?.academic;

  return (
    <div className="shell observatory">
      <AppHeader
        title={t("cnn.title")}
        subtitle={t("cnn.subtitle")}
      />
      {err && <p className="banner err">{err}</p>}

      <div className="cnn-guide">
        <section className="viz">
          <h3>{t("cnn.decide")}</h3>
          <p className="cnn-lead">{t("cnn.lead")}</p>
          <ul className="cnn-types">
            {types.map((row) => (
              <li key={row.id}>
                <strong>{row.label}</strong>
                <span>{row.use}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="viz cnn-use">
          <h3>{t("cnn.read")}</h3>
          <ol className="cnn-rules">
            <li>
              {t("cnn.rule1")}
            </li>
            <li>
              {metrics?.production_encoder ? t("cnn.rule2on") : t("cnn.rule2off")}
            </li>
            <li>
              {metrics?.experimental_on_synthetic ? t("cnn.rule3synth") : t("cnn.rule3")}
            </li>
          </ol>
        </section>
      </div>

      <details className="cnn-lab">
        <summary>{t("cnn.lab")}</summary>
        <p className="muted">{t("cnn.labLead")}</p>
      <div className="chart-grid">
        <section className="viz">
          <h3>{t("cnn.accTitle")}</h3>
          <LeerMas maxLines={2} className="chart-explain">
            {t("cnn.accHow")}
          </LeerMas>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={historyRows} margin={{ top: 8, right: 12, left: 8, bottom: 28 }}>
                <CartesianGrid stroke="#1e3a4c" vertical={false} />
                <XAxis
                  dataKey="epoch"
                  tick={TICK}
                  label={{ value: t("cnn.epoch"), position: "insideBottom", offset: -4, fill: "#c5d5dc", fontSize: 12 }}
                />
                <YAxis
                  tick={TICK}
                  domain={[0, 1]}
                  tickFormatter={(v) => `${Math.round(Number(v) * 100)}%`}
                  label={{ value: t("cnn.accuracy"), angle: -90, position: "insideLeft", style: { textAnchor: "middle", fill: "#c5d5dc", fontSize: 12 } }}
                />
                <Tooltip
                  contentStyle={TOOL}
                  formatter={(value, name) => [`${(Number(value) * 100).toFixed(1)} %`, name === "acc" ? t("cnn.train") : t("cnn.val")]}
                  labelFormatter={(epoch) => `${t("cnn.epoch")} ${epoch}`}
                />
                <Legend formatter={(v) => (v === "acc" ? t("cnn.train") : t("cnn.val"))} />
                <Line type="monotone" dataKey="acc" name="acc" stroke="#14b8a6" dot={false} />
                <Line type="monotone" dataKey="val_acc" name="val_acc" stroke="#38bdf8" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="viz">
          <h3>{t("cnn.lossTitle")}</h3>
          <LeerMas maxLines={2} className="chart-explain">
            {t("cnn.lossHow")}
          </LeerMas>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={historyRows} margin={{ top: 8, right: 12, left: 8, bottom: 28 }}>
                <CartesianGrid stroke="#1e3a4c" vertical={false} />
                <XAxis
                  dataKey="epoch"
                  tick={TICK}
                  label={{ value: t("cnn.epoch"), position: "insideBottom", offset: -4, fill: "#c5d5dc", fontSize: 12 }}
                />
                <YAxis
                  tick={TICK}
                  label={{ value: t("cnn.lossAxis"), angle: -90, position: "insideLeft", style: { textAnchor: "middle", fill: "#c5d5dc", fontSize: 12 } }}
                />
                <Tooltip
                  contentStyle={TOOL}
                  formatter={(value, name) => [Number(value).toFixed(3), name === "loss" ? t("cnn.train") : t("cnn.val")]}
                  labelFormatter={(epoch) => `${t("cnn.epoch")} ${epoch}`}
                />
                <Legend formatter={(v) => (v === "loss" ? t("cnn.train") : t("cnn.val"))} />
                <Line type="monotone" dataKey="loss" name="loss" stroke="#fbbf24" dot={false} />
                <Line type="monotone" dataKey="val_loss" name="val_loss" stroke="#f87171" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <section className="viz">
        <h3>{t("cnn.matrix")}</h3>
        {matrix.length ? (
          <div className="cm-wrap">
            <div
              className="cm-grid"
              style={{ gridTemplateColumns: `minmax(88px, 1.4fr) repeat(${labels.length}, 1fr)` }}
            >
              <div className="cm-corner">real \\ pred</div>
              {labels.map((l) => (
                <div key={`c-${l}`} className="cm-head" title={l}>
                  {l.replace(/_/g, " ").split(" ")[0]}
                </div>
              ))}
              {matrix.map((row, i) => (
                <Fragment key={labels[i] || i}>
                  <div className="cm-head" title={labels[i]}>
                    {labels[i]?.replace(/_/g, " ").split(" ")[0]}
                  </div>
                  {row.map((v, j) => (
                    <div
                      key={`${i}-${j}`}
                      className="cm-cell"
                      style={{
                        background: `rgba(20, 184, 166, ${0.08 + (v / maxCell) * 0.85})`,
                        color: v / maxCell > 0.55 ? "#042018" : "#eef6f8",
                      }}
                    >
                      {v}
                    </div>
                  ))}
                </Fragment>
              ))}
            </div>
          </div>
        ) : (
          <p className="muted">{t("cnn.noMatrix")}</p>
        )}
      </section>
      </details>

      <section className="viz">
        <h3>{t("cnn.try")}</h3>
        <p className="muted">
          {t("cnn.tryLead")}
        </p>
        <label className="run file-btn file-btn-lg">
          {busy ? t("cnn.classifying") : t("cnn.upload")}
          <input
            type="file"
            accept="image/*"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) runFile(f);
            }}
          />
        </label>
        {samplesLoaded && samples.length === 0 ? (
          <p className="banner">{t("cnn.noSamples")}</p>
        ) : samples.length ? (
          <>
            <h4 className="sample-heading">{t("cnn.realPhotos")}</h4>
            <p className="muted">{t("cnn.realLead")}</p>
            <div className="sample-strip">
              {samples.map((s) => (
                <button type="button" key={s.id} className="sample-btn" onClick={() => runSample(s.id)} disabled={busy}>
                  <img src={`${API}${s.url}`} alt={s.title || s.label_es || t("cnn.photo")} />
                  <em>{s.origin || t("cnn.news")}</em>
                  <span>{s.title || s.label_es}</span>
                </button>
              ))}
            </div>
          </>
        ) : null}
        {(preview || pred) && (
          <div className="predict-box">
            {preview && <img src={preview} alt={t("cnn.query")} />}
            <div>
              {pred ? (
                <>
                  {prodAvailable ? (
                    <>
                      <p className="clip-line">{t("cnn.proposed")}</p>
                      <p>
                        <strong>{prodLabel || pred.class || "—"}</strong>{" "}
                        {prodConf != null ? (
                          <span className="risk">{(Number(prodConf) * 100).toFixed(0)}%</span>
                        ) : null}
                      </p>
                      <p className="muted">
                        {t("cnn.pctType")}
                      </p>
                      <LeerMas maxLines={3} className="muted">
                        {pred.note || ""}
                      </LeerMas>
                      <SoftmaxBars scores={prodScores} />
                    </>
                  ) : (
                    <p className="muted">
                      {t("cnn.noClip")}
                    </p>
                  )}
                  <details className="cnn-compare">
                    <summary>{t("cnn.compare")}</summary>
                    {academic ? (
                      <>
                        <p>
                          <strong className="cnn-class">{academic.label_es || academic.class || "SIN_CLASE"}</strong>{" "}
                          {academic.confidence != null ? (
                            <span className="risk">{(Number(academic.confidence) * 100).toFixed(1)}%</span>
                          ) : null}
                        </p>
                        <p className="muted">
                          {academic.note || t("cnn.academicNote")}
                        </p>
                        <SoftmaxBars scores={academic.scores} />
                      </>
                    ) : (
                      <p className="muted">{t("cnn.noAcademic")}</p>
                    )}
                  </details>
                  <LeerMas maxLines={3} className="ocr-box">
                    {`${prodEncoder || pred.encoder || "encoder"} · pHash ${pred.phash_short || "—"} · OCR: ${pred.ocr_text?.trim() || t("article.noOcr")}`}
                  </LeerMas>
                </>
              ) : (
                <p className="muted">{t("cnn.classifying")}</p>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
