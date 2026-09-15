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

const IMAGE_TYPES: { id: string; label: string; use: string }[] = [
  { id: "OFFICIAL_DOCUMENT", label: "Documento oficial", use: "Puede ser un acta o comunicado. Aun así hay que contrastar el texto." },
  { id: "NEWS_SCREENSHOT", label: "Captura de noticia", use: "Es la foto de una nota, no el boletín. Contrasta lo que afirma." },
  { id: "SOCIAL_MEDIA", label: "Red social", use: "Suele ir recortada. No la tomes como fuente completa." },
  { id: "MEME", label: "Meme", use: "Humor o montaje. No sirve como prueba." },
  { id: "INFOGRAPHIC", label: "Infografía", use: "Cifras en la imagen. Verifícalas en una fuente oficial." },
  { id: "ANIMAL_HEALTH_CONTENT", label: "Foto de animal o enfermedad", use: "Ilustra el tema. No confirma el brote por sí sola." },
  { id: "PHOTOGRAPH", label: "Fotografía", use: "Foto común. Mira si la misma imagen aparece en otras notas." },
  { id: "POTENTIALLY_MANIPULATED", label: "Posible manipulación", use: "No te fíes del recuadro. Pásala a revisión humana." },
];

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
        title="Qué es esta imagen"
        subtitle="Clasifica el tipo de foto. No dice si la noticia es verdadera."
      />
      {err && <p className="banner err">{err}</p>}

      <div className="cnn-guide">
        <section className="viz">
          <h3>Para decidir</h3>
          <p className="cnn-lead">
            Cuando una nota trae foto, esto responde una sola cosa: qué clase de imagen es. Con eso sabes si
            puedes usarla como prueba, si es un recorte o si hay que pasarla a revisión.
          </p>
          <ul className="cnn-types">
            {IMAGE_TYPES.map((t) => (
              <li key={t.id}>
                <strong>{t.label}</strong>
                <span>{t.use}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="viz cnn-use">
          <h3>Cómo leer el resultado</h3>
          <ol className="cnn-rules">
            <li>
              El porcentaje es qué tan seguro está del <em>tipo</em> de foto, no un % de que la nota sea verdad.
            </li>
            <li>
              {metrics?.production_encoder
                ? "Hoy mira los píxeles de la foto."
                : "Hoy no mira la foto: solo la dirección web. Sube una imagen abajo para probar."}
            </li>
            <li>
              {metrics?.experimental_on_synthetic
                ? "Hay un ensayo de laboratorio entrenado con dibujos. Ese % no vale para fotos de prensa: no lo uses para validar."
                : testAcc == null
                  ? "Si el tipo no cuadra (meme marcado como documento), no valides: corrige o pásala a revisión."
                  : "Si el tipo no cuadra con lo que ves, no valides: corrige o pásala a revisión."}
            </li>
          </ol>
        </section>
      </div>

      <details className="cnn-lab">
        <summary>Curvas y matriz del ensayo de laboratorio</summary>
        <p className="muted">
          Esto no cambia lo que debes hacer con una foto de prensa. Es el entrenamiento interno: si las líneas de
          validación se separan, el ensayo memoriza dibujos y no sirve para decidir.
        </p>
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
      </details>

      <section className="viz">
        <h3>Probar con una foto</h3>
        <p className="muted">
          Sube una imagen o pulsa una de abajo. El resultado es el tipo de foto, no un veredicto de verdad.
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
                      <p className="clip-line">Tipo de imagen propuesto</p>
                      <p>
                        <strong>{prodLabel || pred.class || "—"}</strong>{" "}
                        {prodConf != null ? (
                          <span className="risk">{(Number(prodConf) * 100).toFixed(0)}%</span>
                        ) : null}
                      </p>
                      <p className="muted">
                        Ese porcentaje es seguridad sobre el tipo de foto, no sobre si la nota es verdad.
                      </p>
                      <LeerMas maxLines={3} className="muted">
                        {pred.note || ""}
                      </LeerMas>
                      <SoftmaxBars scores={prodScores} />
                    </>
                  ) : (
                    <p className="muted">
                      CLIP no está disponible en este equipo. Sube una foto de noticia; el ensayo de laboratorio
                      queda abajo y no es el veredicto.
                    </p>
                  )}
                  <details className="cnn-compare">
                    <summary>Comparar con el ensayo de laboratorio</summary>
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
                            "Ensayo de laboratorio. No lo uses para decidir si la nota es verdad."}
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
