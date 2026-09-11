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

const TICK = { fill: "#9fb4c4", fontSize: 12 };
const TOOL = { background: "#0b1724", border: "1px solid #1e3a4c", color: "#e8f4f8" };

export default function CnnLab() {
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
      .catch(() => setErr("No se pudieron cargar las métricas del laboratorio."));
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
      setErr("La predicción falló.");
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
      setErr("No se pudo clasificar la muestra.");
    } finally {
      setBusy(false);
    }
  }

  const labels = metrics?.confusion_matrix?.labels || [];
  const matrix = metrics?.confusion_matrix?.matrix || [];
  const maxCell = Math.max(1, ...matrix.flat());
  const testAcc = metrics?.experimental_on_synthetic
    ? null
    : (metrics?.test_accuracy ?? metrics?.test_metrics?.test_accuracy);
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
        title="Laboratorio CNN"
        subtitle="Modelo productivo = CLIP/ResNet. La CNN de 8 clases es laboratorio académico; no decide si una noticia es verdadera."
      />
      {err && <p className="banner err">{err}</p>}

      <section className="viz">
        <h3>Arquitectura</h3>
        <div className="arch-row">
          {(metrics?.architecture || []).map((layer, i) => (
            <div key={`${layer.layer}-${i}`} className="arch-box">
              <strong>{layer.layer}</strong>
              <span>
                {layer.filters
                  ? `${layer.filters} filtros ${layer.kernel || ""}`
                  : layer.units
                    ? `${layer.units} unidades`
                    : layer.shape || layer.pool || ""}
              </span>
              {layer.activation && <em>{layer.activation}</em>}
            </div>
          ))}
        </div>
        <p className="muted">
          Adam · sparse_categorical_crossentropy · accuracy · split 70/15/15 ·{" "}
          {metrics?.model_version}
        </p>
        <LeerMas maxLines={2} className="muted">
          {`Dataset: ${metrics?.dataset_total ?? 0} imágenes. El reentrenamiento no ocurre en cada ciclo. Modelo productivo = CLIP/ResNet. La CNN de 8 clases es laboratorio académico; no decide si una noticia es verdadera.`}
        </LeerMas>
      </section>

      <div className="kpi cnn-acc">
        <span>Modelo productivo</span>
        <strong>{metrics?.production_encoder ? "CLIP / ResNet18" : "heurística URL"}</strong>
      </div>
      <div className="kpi cnn-acc">
        <span>CNN académica {metrics?.experimental_on_synthetic ? "(sintético, no producción)" : "(fotos minadas)"}</span>
        <strong>
          {metrics?.experimental_on_synthetic
            ? "no usar el % como métrica"
            : testAcc == null
              ? "—"
              : `${(Number(testAcc) * 100).toFixed(1)}% val/test`}
        </strong>
      </div>
      {metrics?.experimental_on_synthetic && metrics?.academic_test_accuracy != null ? (
        <p className="muted">
          Exactitud en dibujos de laboratorio: {(Number(metrics.academic_test_accuracy) * 100).toFixed(1)}% —
          no generaliza a fotos de prensa.
        </p>
      ) : null}

      <div className="chart-grid">
        <section className="viz">
          <h3>Exactitud train vs validación</h3>
          <LeerMas maxLines={2} className="chart-explain">
            Cada punto es una época. Si la línea de validación se queda atrás del entrenamiento, el modelo memoriza y no generaliza.
          </LeerMas>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={historyRows} margin={{ top: 8, right: 12, left: 8, bottom: 28 }}>
                <CartesianGrid stroke="#1e3a4c" vertical={false} />
                <XAxis
                  dataKey="epoch"
                  tick={TICK}
                  label={{ value: "Época", position: "insideBottom", offset: -4, fill: "#c5d5dc", fontSize: 12 }}
                />
                <YAxis
                  tick={TICK}
                  domain={[0, 1]}
                  tickFormatter={(v) => `${Math.round(Number(v) * 100)}%`}
                  label={{ value: "Exactitud", angle: -90, position: "insideLeft", style: { textAnchor: "middle", fill: "#c5d5dc", fontSize: 12 } }}
                />
                <Tooltip
                  contentStyle={TOOL}
                  formatter={(value, name) => [`${(Number(value) * 100).toFixed(1)} %`, name === "acc" ? "Entrenamiento" : "Validación"]}
                  labelFormatter={(epoch) => `Época ${epoch}`}
                />
                <Legend formatter={(v) => (v === "acc" ? "Entrenamiento" : "Validación")} />
                <Line type="monotone" dataKey="acc" name="acc" stroke="#14b8a6" dot={false} />
                <Line type="monotone" dataKey="val_acc" name="val_acc" stroke="#38bdf8" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="viz">
          <h3>Pérdida train vs validación</h3>
          <LeerMas maxLines={2} className="chart-explain">
            La pérdida (loss) debe bajar. Si validación sube mientras entrenamiento baja, hay sobreajuste.
          </LeerMas>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={historyRows} margin={{ top: 8, right: 12, left: 8, bottom: 28 }}>
                <CartesianGrid stroke="#1e3a4c" vertical={false} />
                <XAxis
                  dataKey="epoch"
                  tick={TICK}
                  label={{ value: "Época", position: "insideBottom", offset: -4, fill: "#c5d5dc", fontSize: 12 }}
                />
                <YAxis
                  tick={TICK}
                  label={{ value: "Pérdida (loss)", angle: -90, position: "insideLeft", style: { textAnchor: "middle", fill: "#c5d5dc", fontSize: 12 } }}
                />
                <Tooltip
                  contentStyle={TOOL}
                  formatter={(value, name) => [Number(value).toFixed(3), name === "loss" ? "Entrenamiento" : "Validación"]}
                  labelFormatter={(epoch) => `Época ${epoch}`}
                />
                <Legend formatter={(v) => (v === "loss" ? "Entrenamiento" : "Validación")} />
                <Line type="monotone" dataKey="loss" name="loss" stroke="#fbbf24" dot={false} />
                <Line type="monotone" dataKey="val_loss" name="val_loss" stroke="#f87171" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <section className="viz">
        <h3>Matriz de confusión (test)</h3>
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
          <p className="muted">Entrena el modelo para ver la matriz.</p>
        )}
      </section>

      <section className="viz">
        <h3>Probar imagen no vista</h3>
        <p className="muted">
          El resultado principal es CLIP/ResNet (tipo de imagen). No decide si la noticia es verdadera.
        </p>
        <label className="run file-btn file-btn-lg">
          {busy ? "Clasificando…" : "Subir imagen"}
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
          <p className="banner">Aún no hay fotos minadas; sube una captura de noticia o un meme real</p>
        ) : samples.length ? (
          <>
            <h4 className="sample-heading">Fotos reales del observatorio</h4>
            <p className="muted">YouTube y og:image de artículos. Clic predice esa foto.</p>
            <div className="sample-strip">
              {samples.map((s) => (
                <button type="button" key={s.id} className="sample-btn" onClick={() => runSample(s.id)} disabled={busy}>
                  <img src={`${API}${s.url}`} alt={s.title || s.label_es || "foto del observatorio"} />
                  <em>{s.origin || "noticia"}</em>
                  <span>{s.title || s.label_es}</span>
                </button>
              ))}
            </div>
          </>
        ) : null}
        {(preview || pred) && (
          <div className="predict-box">
            {preview && <img src={preview} alt="consulta" />}
            <div>
              {pred ? (
                <>
                  {prodAvailable ? (
                    <>
                      <p className="clip-line">
                        {prodEncoder || "CLIP/ResNet"} · modelo productivo
                      </p>
                      <p>
                        <strong>{prodLabel || pred.class || "—"}</strong>{" "}
                        {prodConf != null ? (
                          <span className="risk">{(Number(prodConf) * 100).toFixed(1)}%</span>
                        ) : null}
                      </p>
                      <LeerMas maxLines={3} className="muted">
                        {pred.note || ""}
                      </LeerMas>
                      <SoftmaxBars scores={prodScores} />
                    </>
                  ) : (
                    <p className="muted">
                      CLIP/ResNet no está disponible en este equipo. Sube una imagen de noticia; la CNN experimental
                      queda abajo y no es el veredicto.
                    </p>
                  )}
                  <details className="cnn-compare">
                    <summary>Comparar con CNN experimental</summary>
                    {academic ? (
                      <>
                        <p>
                          <strong className="cnn-class">{academic.label_es || academic.class || "SIN_CLASE"}</strong>{" "}
                          {academic.confidence != null ? (
                            <span className="risk">{(Number(academic.confidence) * 100).toFixed(1)}%</span>
                          ) : null}
                        </p>
                        <p className="muted">
                          {academic.note ||
                            "CNN académica de 8 clases (64×64). No es el modelo de producción ni un veredicto de verdad."}
                        </p>
                        <SoftmaxBars scores={academic.scores} />
                      </>
                    ) : (
                      <p className="muted">Sin comparación académica para esta imagen.</p>
                    )}
                  </details>
                  <LeerMas maxLines={3} className="ocr-box">
                    {`${prodEncoder || pred.encoder || "encoder"} · pHash ${pred.phash_short || "—"} · OCR: ${pred.ocr_text?.trim() || "sin texto"}${
                      pred.animal_health_relevance != null
                        ? ` · relevancia sanidad ${(Number(pred.animal_health_relevance) * 100).toFixed(0)}%`
                        : ""
                    }`}
                  </LeerMas>
                </>
              ) : (
                <p className="muted">Clasificando…</p>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
