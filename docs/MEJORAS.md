# Plan de mejoras — observatorio The NewsBreakers

**Fecha:** 10 de septiembre de 2026  
**Ámbito:** `C:\Users\javie\OneDrive\Escritorio\the-newsbreakers-framework`  
**UI:** Vite :5173 · **API:** FastAPI :8010 · **Lectura:** SQLite `data/processed/tnb.db`  
**Complementa:** [`AUDITORIA.md`](AUDITORIA.md) (arquitectura y pipeline). Este documento es el plan **de producto**: sala, mapa, gráficas, grafo, lab CNN, HITL, ficha, fuentes, minería, NLP y visión.

**Veredicto:** el dashboard es un MVP navegable, no un puesto de analista. Las pantallas existen y se ven “completas”, pero casi ninguna **cruza filtros**, **cuenta una historia** ni **distingue vacío de cero**. Las gráficas son el síntoma más visible; el problema es de todo el marco.

No implementar este documento de un golpe. Priorizar P0 del sprint de 2 semanas. No fusionar con el verificador Next.js (`the-newsbreakers`). No hacer git commit de este plan.

---

## Cómo leer este plan

| Prioridad | Significado |
|-----------|-------------|
| **P0** | Sin esto el analista no confía ni puede trabajar. Semanas 1–2. |
| **P1** | Calidad de señal o de lectura. Tras el contrato de filtros. |
| **P2** | Pulido, escala, ML real. Fuera del sprint salvo que sobre tiempo. |

Cada apartado: **qué hay** (honesto) → **por qué se siente pobre** → **qué harías** → **cómo**. Al final: matriz P0/P1/P2 y sprint de 14 días.

Nota sobre la auditoría: `AUDITORIA.md` describe un HITL “API sí / UI no”. Hoy ya hay ruta `/revision` con Validar/Descartar/Modificar y `html_fetcher` para cuerpos RSS. El resto del veredicto (scrape diferido, NLI léxico, CNN sintética, MySQL dual-write, 4 Recharts) sigue vigente.

---

## Contrato compartido (antes de pintar más charts)

Hoy cada ruta (`/`, `/mapa`, `/graficas`, `/grafo`, `/fuentes`, `/revision`) es un panel dentro de `Observatory.tsx` que **igual dispara** `stats + geo + charts + graph + articles + sources + alerts` cada 60 s. El querystring solo guarda `disease`, `q` y `page`. El mapa abre **el primer artículo** del país; las gráficas **no navegan**; el grafo filtra a medias; la ficha no hereda el filtro.

Sin un contrato único, cualquier gráfica “bonita” seguirá siendo un póster.

**Querystring canónico** (todos los paneles lo leen y lo escriben):

```
?disease=gripe_aviar
&compare=gusano_barrenador,fiebre_porcina_clasica
&from=2026-08-01&to=2026-09-10
&country=MX
&state=CHIS
&verdict=CONTRADICHO
&stance=Unknown
&q=senasica
&source=SRC002
&raw_format=rss
&page=1
```

**API (extender, no inventar otro gateway):**

| Endpoint | Cambio |
|----------|--------|
| `GET /articles` | `disease`, `from`, `to`, `country`, `verdict`, `q`, `source_id`, `raw_format`, `page`, `page_size`. Devolver `{ count, page, page_size, articles }`. Dejar de filtrar 400 filas en el cliente. |
| `GET /charts` | Mismos filtros + `compare`. Series por día × enfermedad, `risk_mean`, ids de muestra por cubo, `empty: true/false`. |
| `GET /geo` | Mismos filtros + `level=country\|state`. |
| `GET /graph` | Mismos filtros + `limit` de nodos artículo. |
| `GET /alerts` | Filtros + `status`. |

Navegación: clic en barra / punto / país / nodo → `navigate({ pathname: "/", search })` (sala filtrada), no a un `content_id` al azar. La ficha se abre desde la tarjeta.

---

## 1. Sala de vigilancia

### Qué hay ahora

- Grid de tarjetas (`ArticleCard` + `CardThumb`): veredicto, riesgo, resumen de 2 líneas, fuente, fecha.
- Pills **hardcodeadas** a 3 enfermedades (`gusano_barrenador`, `gripe_aviar`, `fiebre_porcina_clasica`) aunque `/diseases` ya cuenta más.
- Búsqueda substring en título/texto/fuente **en el cliente** sobre hasta 400 filas.
- Paginación de 12; thumbs se backfilleán por página.
- KPIs (artículos, claims, alertas, fuentes) con sparklines **mal cableadas**: la de claims usa los 3 valores del donut de postura, no una serie temporal (`sparkline_series` en `store.py`).
- Polling 60 s de **todo** el observatorio. Banner de minería / MySQL.
- Empty: una línea “No hay artículos con este filtro…”.

### Por qué se siente pobre

Parece un timeline de noticias, no una sala de crisis. No se puede ordenar por riesgo, ni filtrar veredicto, ni ver solo RSS vs seed vs corpus. Las 3 pills mienten sobre el catálogo. El KPI “Alertas” mezcla pendientes con total. Las miniaturas sintéticas / corpus siguen colándose y dan sensación de teatro. Recargar 7 endpoints en cada visita a la sala retrasa el primer paint.

### Qué harías (3–6)

1. **P0** Filtros de trabajo: veredicto, rango de riesgo, país, `raw_format` (rss/api/scrape/fixture/corpus), orden (`collected_at` \| `risk_score` \| `published_at`).
2. **P0** Pills de enfermedad **desde** `GET /diseases` (todas las que tengan menciones + “Otras”).
3. **P0** Empty states distintos: (a) base vacía / sin minería; (b) filtro demasiado estrecho + botón “Limpiar”; **nunca** una tarjeta fantasma.
4. **P1** Badge de origen en la tarjeta (`RSS`, `GDELT`, `seed`, `YouTube`) y ocultar thumbs genéricos (`is_news_thumb=false`).
5. **P1** KPI de alertas = `alerts_pending`; sparkline real de volumen diario.
6. **P1** Cargar sala sin esperar geo/charts/grafo: fetch por panel.

### Cómo implementarlo

- **UI:** `Observatory.tsx` toolbar (selects nativos). `ArticleGrid` recibe `count` del servidor.
- **API:** `store.filtered_articles` con SQL `WHERE collected_at BETWEEN ? AND ?` + `AND verdict=?`. En SQLite añadir índice por `collected_at` (MySQL ya tiene `idx_articles_collected`).
- **Diseño:** densidad compacta opcional (lista de una línea) para HITL rápido; grid actual como default. Color de veredicto **y** patrón (borde punteado = revisión humana) para daltónicos.
- **Libs:** ninguna nueva. Playwright: filtro gripe aviar → N tarjetas → clic → ficha.

---

## 2. Mapa

### Qué hay ahora

- Leaflet + teselas OSM. Círculos en **centroides de país** (`database/geo.py` + `geoCentroids.ts`).
- Popup: hasta 4 títulos. **Clic = abre el artículo más reciente** de ese país (`pickFromGeo`).
- Dock lateral: nombre + conteo, mismo comportamiento.
- `fitBounds` con `maxZoom: 5`. Puntos `INT` / `XX` caen en el Atlántico.
- Entidades `STATE` existen en el gazetteer (`entities.py`) y **no se pintan**.
- El mapa se destruye y se recrea en cada `useEffect(points)` (`MapView.tsx`).

### Por qué se siente pobre

Un mapa de “menciones en México / EE. UU. / Internacional” no es vigilancia epidemiológica. El clic traiciona: el analista quiere **la cola de ese país**, no un artículo al azar. Sin coropleta ni estados, Chiapas y Sonora son el mismo punto. Teselas OSM claras chocan con el tema oscuro. El parpadeo al filtrar se siente barato.

### Qué harías (3–6)

1. **P0** Clic en país → sala con `?country=MX` (el popup sigue ofreciendo “abrir ficha X”).
2. **P0** No pintar `XX`/`INT` como islas en el mar: lista “Sin ubicar (N)” debajo del mapa.
3. **P1** Nivel estado MX: centroides de `STATES` + GeoJSON ligero (32 polígonos simplificados).
4. **P1** Coropleta por quintiles de conteo (secuencial azul `#0072B2` → beige) **más** círculo de riesgo medio.
5. **P1** Brush temporal compartido con gráficas (`from`/`to`).
6. **P2** Cluster de marcadores; teselas Carto Dark / Positron.

### Cómo implementarlo

- **API:** `GET /geo?level=state&country=MX&from=&to=&disease=`. Resolver estado desde entidades `STATE` + `claim.location`; fallback país.
- **Front:** `react-leaflet` (hoy Leaflet a mano se destruye entero). Popup HTML ya usa hash routes; mantener `articleHref`.
- **Diseño:** leyenda “documentos (tamaño) / riesgo medio (color)”. Empty: mapa vacío + “No hay coordenadas en el filtro; N artículos sin ubicar”.
- **Libs:** `react-leaflet` + GeoJSON en `frontend/public/mx-states.json`. No Mapbox (clave y coste).

---

## 3. Gráficas *(prioridad de producto)*

Esta sección es más larga a propósito. Cuatro Recharts genéricos no se “arreglan” con un tooltip más. Hay que cambiar **payload, clic y empty**.

### Qué hay ahora

Cuatro charts en `ChartsPanel.tsx`, alimentados por `GET /charts` → `store.chart_payload`:

| Chart | Tipo | Datos reales |
|-------|------|----------------|
| Volumen por enfermedad | `BarChart` vertical | 3 IDs fijos (`DISEASE_META`) + extras |
| Documentos recientes | `BarChart` por día | últimos **24** días recortados **en el cliente** |
| Histograma de riesgo | 5 cubos 0–20 … 81–100 | `risk_score` o **0 si null** |
| Postura de claims | `PieChart` donut | Supported / Contradicted / Unknown |

Tooltips (`ChartTip`): `N documentos` / `N claims`. Sin clic. Sin zoom. Sin eje dual. Sin series apiladas. Paleta teal / sky / ámbar / rojo / violeta.

Si no hay datos, **se inventa** una fila y se dibuja igual:

```ts
const diseaseRows = disease.length ? disease : [{ id: "—", name: "Sin datos", label: "Sin datos", count: 0 }];
const dayRows = days.length ? days : [{ day: "Sin fecha", count: 0 }];
```

Eso es el fallo más grave de UX analítica: el vacío se disfraza de medición.

Otros defectos del payload:

- Días sin captura **desaparecen** (no hay hueco explícito).
- `risk_score=null` cae en el cubo 0–20 → infla “bajo riesgo”.
- El donut no distingue “0 claims porque no hay artículos” de “todos Unknown”.
- No hay serie por enfermedad en el tiempo, ni `risk_mean`, ni ids para click-through.
- `Observatory.tsx` pide `/charts` incluso en la sala.

### Por qué se siente pobre / mal

1. **Son pósteres, no instrumentos.** No se puede preguntar “¿qué pasó el 3 de septiembre en gripe aviar?” y saltar a la sala.
2. **Cuatro gráficos del mismo hecho** (un conteo). No hay tendencia relativa, ni riesgo vs volumen, ni composición.
3. **El vacío se disfraza de dato.** Una barra “Sin datos = 0” es peor que un empty state.
4. **Eje temporal mentiroso:** recortar a 24 días esconde historia; los huecos no se ven.
5. **Riesgo contaminado** por nulls.
6. **Daltonismo e impresión:** rojo/verde del donut; fondo `#0b1724` ilegible en PDF/proyector.
7. **Sparklines del header mienten** (claims = 3 valores del donut).

Esto no se arregla “poniendo LineChart”. Hay que **cambiar el contrato**.

### Qué harías (no son 4 bars)

#### 3.1 Small multiples de volumen — P0

Un área pequeña **por enfermedad**, misma escala Y, mismos `from`/`to`. El ojo compara brotes, no alturas de un bar categórico.

- Payload: `by_day[]` con una clave por enfermedad.
- UI: CSS grid 2–3 columnas; `AreaChart` Recharts; eje Y solo en el primero.
- Clic en un día de un multiple → sala `?disease=&from=day&to=day`.

#### 3.2 Área apilada + comparador — P0

`AreaChart` stacked (toggle 100 % stacked). Chips para añadir/quitar enfermedades (`compare=`). Default: las 3 vigiladas.

- Muestra **cuánto del día es cada enfermedad**.
- Tooltip: `12 documentos · Gripe 7 · Gusano 4 · PPC 1` + enlace **Ver en sala**.

#### 3.3 Dual axis: volumen vs riesgo medio — P0

`ComposedChart`: barras = documentos; línea = `risk_mean` (eje derecho 0–100).

- `ReferenceLine` / `ReferenceDot`: última minería, picos con media ≥ 55, alertas HITL.
- Tooltip: `N documentos (clic) · riesgo medio 62 · 3 alertas`.

#### 3.4 Brush / zoom temporal — P0

`Brush` de Recharts en el composed. Al soltar, escribe `from`/`to` en el querystring → **sala, mapa y small multiples se recortan**. No es un zoom cosmético interno.

#### 3.5 Tooltips que son puertas — P0

Cada cubo (día, enfermedad, bin de riesgo, gajo de postura) lleva filtro listo:

```json
{
  "count": 12,
  "sample_titles": ["WOAH confirma…", "SENASICA…"],
  "filter": { "from": "2026-09-03", "to": "2026-09-03", "disease": "gripe_aviar" }
}
```

UI del tooltip:

- `12 documentos`
- 2–3 títulos cortos
- **Ver los 12 en la sala** → `navigate({ pathname: "/", search })`

El histograma y el donut **también** navegan (`?risk_min=&risk_max=` / `?stance=`).

#### 3.6 Empty real vs “0 documentos” — P0

| Situación | UI correcta |
|-----------|-------------|
| `articles=0` en toda la DB | ilustración + “Aún no hay minería. `python mine_loop.py`” |
| Filtro sin filas | “0 documentos con este filtro” + chips del filtro + **Limpiar**. Sin ejes con una barra a 0 |
| Día sin captura **dentro** de un rango con datos | hueco (`count: 0`, `missing: true`) como gap, no como categoría “Sin fecha” |
| Claims=0 pero sí hay artículos | donut sustituido por “Sin claims extraídos (NLP no encontró afirmaciones)” |
| `risk_score=null` | cubo aparte **Sin puntuación**, nunca 0–20 |

#### Extra P1 (mismas gráficas)

- Paleta **Okabe–Ito** (daltónicos): `#E69F00 #56B4E9 #009E73 #F0E442 #0072B2 #D55E00 #CC79A7`. Postura: azul = Supported, naranja = Contradicted, gris = Unknown. Añadir rayado SVG, no solo color.
- Tema **imprimible**: `@media print` fondo blanco, tinta `#111`, leyendas en texto. Botón “Exportar PNG” (`html-to-image` sobre el contenedor).
- Tabla accesible bajo cada chart (`<table>` + “Mostrar datos”) para Excel.
- Anotaciones desde `GET /charts.annotations` (ciclos de minería, reviews HITL).

### Cómo implementarlo (libs, endpoints, visual)

**No cambiar de librería en el sprint.** Recharts 3 ya tiene `ComposedChart`, `Area`, `Brush`, `ReferenceLine` y tooltip custom. Migrar a Nivo/ECharts/Observable Plot sería una semana de restyling con el mismo recorte de datos.

| Pieza | Dónde |
|-------|--------|
| Payload rico | `database/store.py` → `chart_payload`: `GROUP BY date(coalesce(published_at, collected_at))` + tags de enfermedad |
| Contrato | `GET /charts` en `api/main.py`; tipos `ChartBundle` en `frontend/src/api.ts` |
| UI | reescribir `ChartsPanel.tsx` (composed ancho + brush; small multiples; stacked; histograma; postura como **quinto** chart, no protagonista) |
| Clic | `useNavigate` + querystring canónico |
| Color | nuevo `frontend/src/chartTheme.ts` (Okabe–Ito, tokens print) |
| Export | `html-to-image` (P1) |
| Tests | pytest: suma de series = total; `empty` si count=0; null de riesgo no entra en 0–20. RTL: el tooltip tiene el link “Ver en sala” |

**Endpoint propuesto (compatible hacia atrás):**

```
GET /charts?disease=&compare=a,b&from=&to=&country=
```

```json
{
  "empty": false,
  "filter": { "from": "2026-08-01", "to": "2026-09-10", "disease": null },
  "volume_by_disease": [
    { "id": "gripe_aviar", "name": "Gripe aviar", "count": 40 }
  ],
  "by_day": [
    {
      "day": "2026-09-03",
      "count": 12,
      "missing": false,
      "risk_mean": 48.2,
      "risk_unknown": 2,
      "alerts": 1,
      "gripe_aviar": 7,
      "gusano_barrenador": 4,
      "fiebre_porcina_clasica": 1,
      "filter": { "from": "2026-09-03", "to": "2026-09-03" }
    }
  ],
  "risk_histogram": [
    { "bucket": "61-80", "count": 5, "filter": { "risk_min": 61, "risk_max": 80 } },
    { "bucket": "sin_puntuacion", "count": 3, "filter": { "risk_null": true } }
  ],
  "stance": [
    { "name": "Unknown", "value": 9, "filter": { "stance": "Unknown" } }
  ],
  "annotations": [
    { "day": "2026-09-08", "label": "ciclo RSS", "kind": "mine" }
  ]
}
```

Mantener `volume_by_day` un ciclo para no romper clientes; deprecarlo en el mismo PR.

**Diseño visual:**

1. Columna principal a ancho completo: composed (volumen + riesgo) + Brush.
2. Debajo: small multiples (una enfermedad por panel, título = nombre + n).
3. Debajo o al lado: stacked area (comparador) + histograma + postura.
4. Títulos con **pregunta** (“¿Cuántos documentos por día y qué tan riesgosos?”), no “Chart 2”.
5. Cada chart declara población: `n = 128 documentos del filtro`.
6. Cursor pointer en barras/áreas; el tooltip tiene un `<button>` o `<a>` real, no solo texto.

**P2 (después del sprint):** heatmap 90 días tipo GitHub; small multiples por **país**; dual axis alertas vs documentos; Vega-Lite si las specs crecen.

---

## 4. Grafo de narrativas

### Qué hay ahora

- `vis-network` Barnes-Hut. Nodos: fuente (`SRC-{id}`), enfermedad, narrativa (4 buckets keyword), hasta **40** artículos (`store.network_graph`).
- Clic: enfermedad → pill; fuente → `q=label` (el label es el **id**, no el nombre); artículo → ficha; narrativa → sala **sin filtro**.
- Física siempre encendida; sin búsqueda, sin freeze, sin export.
- No es un grafo de claims ni HDBSCAN: es co-ocurrencia léxica.

### Por qué se siente pobre

Una sopa de puntos. Las fuentes se llaman `SRC002`. Las narrativas “brote/vacunas/ocultamiento/artificial” aparecen aunque `claim_count=0`. 40 artículos de 400 es una muestra opaca. El analista no puede preguntar “quién conecta SENASICA con H5N1 esta semana”.

### Qué harías (3–6)

1. **P0** Etiquetas humanas (`sources.name`) y no dibujar narrativas con 0 claims.
2. **P0** Clic en narrativa → sala `?q=` o `?narrative=NAR-ocultamiento`.
3. **P1** Controles: physics on/off, filtro por grupo, tope de artículos (slider 10–80), “solo oficiales”.
4. **P1** Sidebar al seleccionar: grado, documentos, link “ver N en sala”.
5. **P1** Layout jerárquico opcional (enfermedad → fuentes → artículos) para demos.
6. **P2** Clustering real de claims; aristas con peso = co-menciones.

### Cómo implementarlo

- Seguir con **vis-network**; no migrar a Cytoscape en el sprint.
- `network_graph`: join `sources.name`; `value` = conteo; tooltip “clic filtra la sala”.
- CSS: leyenda ya existe; añadir “N nodos · M aristas · muestra de 40/128 artículos”.
- Empty: “No hay co-ocurrencias con este filtro” (grafo vacío, no 3 nodos sueltos de enfermedad).

---

## 5. CNN / Laboratorio

### Qué hay ahora

- Ruta `/cnn` (`CnnLab.tsx`): cajas de arquitectura, accuracy train/val, loss, matriz de confusión, upload, tira de PNG de test.
- Copy honesto: CNN 8 clases **académica** (a menudo sintético); encoder productivo CLIP/ResNet o heurística URL (`visual_encoder.py`).
- `POST /cnn/predict` (token si `TNB_API_TOKEN`). Softmax + pHash + OCR.
- Dataset en `models/cnn/dataset`; reentrenar a mano. Matriz recorta labels al primer token (`ANIMAL_HEALTH_CONTENT` → “ANIMAL”).

### Por qué se siente pobre

Parece un notebook de clase pegado al observatorio. Las muestras de test son dibujos. No hay puente “esta foto salió en la ficha X”. Un 98 % sintético, si se enseña mal, destruye credibilidad. Upload abierto si no hay token.

### Qué harías (3–6)

1. **P0** Banner persistente: “Este % no decide si una noticia es falsa”.
2. **P0** Galería de **fotos minadas reales** (`GET /images`) + link a ficha; no solo `models/cnn/samples/*.png`.
3. **P1** Matriz con labels ES completos; clic en celda → imágenes de ese par real/predicho.
4. **P1** Pestañas “Productivo (CLIP/ResNet)” vs “Académico (CNN 64×64)”.
5. **P1** Rechazar export de sintéticos / `demo_seed_` (ver Visión).
6. **P2** HITL de etiquetado visual hacia `cnn_samples`.

### Cómo implementarlo

- `GET /cnn/metrics` ya sirve history/CM; reutilizar `GET /images?limit=24` en el lab.
- Diseño: dos columnas (productivo | experimento). Confusion: texto pequeño, sin truncate.
- Auth: exigir token en `/cnn/predict` en LAN demo (aunque sea `tnb-local` en `.env.example`).
- **Libs:** ninguna nueva para el lab.

---

## 6. Revisión HITL

### Qué hay ahora

- Ruta `/revision` con cola `alerts?status=pending_review`. Badge en nav (`AppHeader.tsx`).
- Acciones: Validar / Descartar / Modificar (`window.prompt` para el motivo).
- API `POST /alerts/{id}/review` escribe `reviews` + `audit_logs` (SQLite y MySQL). `used_for_retraining=0` (correcto).
- Analyst hardcoded `"sala"`. No hay undo. La ficha **no** tiene botones HITL.
- Empty: “No hay alertas pendientes”.
- La auditoría decía “UI stub”; el panel ya existe, pero es una lista de títulos.

### Por qué se siente pobre

El analista no ve claim, evidencia ni `why` del risk sin abrir otra pestaña. `prompt()` es un prototipo. No hay cola histórica, ni teclado, ni conflicto si dos personas pulsan. Sin cierre humano el 24/7 no opera.

### Qué harías (3–6)

1. **P0** Card HITL con: título, riesgo, veredicto, **claim principal**, snippet de evidencia, link a ficha.
2. **P0** Modificar = textarea + motivo obligatorio, no `prompt`.
3. **P0** Los tres botones **dentro de la ficha** si hay alerta `pending_review`.
4. **P1** Filtros: riesgo ≥ 55, enfermedad, fecha. Historial `status=reviewed`.
5. **P1** Atajos `V` / `D` / `M`. Undo 5 s (reabrir `pending_review`).
6. **P2** Roles, SLA, correo.

### Cómo implementarlo

- `GET /alerts?status=pending_review&include=article,claims,evidence` (join en `store.py`).
- Extraer `HitlQueue` de `Observatory.tsx` a `HitlPanel.tsx`. Modal de modificar.
- Diseño: semáforo de veredicto + patrón; motivo visible.
- Empty distinto: “Cola a cero — última revisión hace Ns” vs “La API no trajo alertas (¿ciclo sin umbral?)”.

---

## 7. Ficha de artículo

### Qué hay ahora

- `AnalysisPage.tsx`: hero, mapa de 1 punto, timeline, “lectura del caso” (local/LLM), entidades (DISEASE/ANIMAL/COUNTRY/ORG), evidencia + claims en el mismo bloque, galería CNN/OCR, similares **sin** pintar `reasons`.
- 404 con 5 recientes. Allowlist de URL. Calidad `%` opaca.
- No HITL. Entidades no filtran la sala. Similares = tags + pHash, no embeddings.

### Por qué se siente pobre

Página larga de paneles iguales (`viz`) sin jerarquía: el veredicto se pierde entre el mapa y el softmax. Evidencia y claims mezclados. “WOAH” inyectado por gazetteer se ve como hecho. Similares parecen recomendaciones vacías. El mapa de un centroide de país no aporta.

### Qué harías (3–6)

1. **P0** Layout 2 columnas: (izq) decisión — veredicto, riesgo, claims, evidencia, HITL; (der) contexto — texto, mapa, imágenes, similares.
2. **P0** Mostrar `similar.reasons` (“misma enfermedad”, “pHash cercano”).
3. **P0** Claims y evidencia **emparejados** por `claim_id`.
4. **P1** Chips de entidad clicables → sala `?q=` / `?disease=` / `?country=`.
5. **P1** Timeline útil: publicado → capturado → claims → alerta → review (`TRACEABILITY.md`).
6. **P1** Calidad: frase humana (“sin LLM; NLI léxico; 2 claims Unknown”).

### Cómo implementarlo

- CSS `analysis-grid` ya existe; reordenar JSX, no nuevo framework.
- API detalle ya manda `claims`, `evidence`, `similar`, `timeline`, `quality`. Pegar evidencia al claim.
- Empty: “Sin evidencia oficial cacheada” ≠ “Contradicho”. No mapa si código `XX`.

---

## 8. Fuentes

### Qué hay ahora

- Cards: nombre, dominio, `type`/`access_method`, país, “Operativa” o `last_error`.
- ~109 filas del catálogo. Scrape diferido **sin error** se pinta Operativa.
- No hay conteo de artículos, ni `last_checked` visible, ni RSS vs API vs scrape, ni filtros.
- `GET /sources` sí manda `consecutive_failures`, `next_check`, `healthy`.

### Por qué se siente pobre

Un directorio plano. El 90 % scrape-never se ve tan “sano” como WHO RSS. El analista no sabe qué alimenta la sala. No hay forma de abrir “artículos de esta fuente”.

### Qué harías (3–6)

1. **P0** Tabla: método (rss/api/scrape), última captura, fallos seguidos, **N artículos**, estado (`ok` / `error` / `deferred`).
2. **P0** Clic en fila → sala `?source=SRC002`.
3. **P1** Filtros: método, país, healthy, “solo con artículos”.
4. **P1** No decir Operativa si `access_method=scrape` y nunca se ha chequeado: badge **Diferida**.
5. **P1** Ordenar por fallos / por N artículos.
6. **P2** Mini sparkline de capturas por fuente.

### Cómo implementarlo

- Tabla HTML (`<table>`), no 109 cards. `store.list_sources` + `COUNT(articles)`.
- Diseño: ícono de método + color de salud **y** texto.
- Empty: “Catálogo vacío (¿`catalog.yaml`?)”.

---

## 9. Minería / MySQL

### Qué hay ahora

- Ciclo: RSS + GDELT + `html_fetcher` para cuerpo si el summary es corto. Scrape masivo sigue **deferred**.
- `POST /cycle?max_sources=8` desde la sala (hardcode en `api.ts`). `mine_loop.py` ~30 min. Banner `mine_state.json`.
- SQLite es la fuente de lectura. MySQL dual-write (schema ya tiene `reviews` / `audit_logs`). Banner “MySQL conectado” no dice si va atrasado.
- Seed/fast por defecto ya van en `0`. Demo seed sigue existiendo por flag.
- Sin backup automatizado. Artículos **no** se paginan en servidor. `TNB_MAX_SOURCES` 12.

### Por qué se siente pobre / mal

La UI promete un observatorio 24/7; el embudo real es ~8 RSS + GDELT títulos. Dual-write que falla en silencio convierte el banner verde en teatro. Un ciclo desde el botón no es operación (PC sleep, OneDrive lock). Los charts heredan basura (fixture, corpus, GDELT sin cuerpo).

### Qué harías (3–6)

1. **P0** KPIs de **calidad de captura**: `% raw_format in (rss, api)`, `% con cuerpo > 500 chars`, `% seed/corpus`. Banner: “128 docs · 91 RSS · 12 seed · 25 sin cuerpo”.
2. **P0** Backup diario SQLite (`sqlite3 .backup` + zip) + Task Scheduler; documentar restauración.
3. **P0** Si MySQL cae: banner **ámbar** con `mysql_error` (`/health` ya lo tiene; la UI no).
4. **P1** Botón ciclo no bloqueante: `BackgroundTasks` + poll `/status` (el ciclo síncrono congela :8010).
5. **P1** `max_sources` configurable; no hardcode 8 en `api.ts`.
6. **P2** Servicio Windows / compose API+mine+web; parsers scrape de 5 oficiales. Celery fuera.

### Cómo implementarlo

- Extender `GET /kpis` con `by_format`. Pintar en `mine-banner`.
- Script `scripts/backup-tnb.ps1` + XML Task Scheduler.
- Dual-write: exponer `mysql_lag` (max `collected_at` SQLite vs MySQL).
- No migrar la lectura a MySQL en 2 semanas.
- **Libs:** `sqlite3` CLI; Docker MySQL ya está en compose.

---

## 10. NLP (claims, entidades, relevancia, narrativas)

### Qué hay ahora

- Relevancia por keywords YAML (umbral 0.15).
- NER gazetteer (enfermedades, especies, países, orgs, estados). Puede inyectar WOAH/FAO.
- Claims: regex + `claim_engine` del Generador. NLI léxico conservador (`lexical_v2_conservative`) — Unknown por defecto.
- Narrativas: 4 clusters keyword (`engine.py`); `growth_pct=100` si prev=0.
- Clasificador ML: stub (`unclassified`).
- Dashboard: 3 enfermedades.

### Por qué se siente pobre

Claims cortos de summaries GDELT. Entidades “WHO” por substring. El donut de postura se llena de Unknown y parece que el sistema no sabe. Narrativas infladas el primer ciclo. Sin tripletas estables no hay grafo ni HITL de calidad.

### Qué harías (3–6)

1. **P0** No extraer claims si `len(text) < 400` (marcar `pipeline_level` bajo; no Unknown teatral).
2. **P0** UI: contar “artículos sin claims” distinto de “claims Unknown”.
3. **P1** NER: word boundaries para orgs; no inyectar WOAH si no está en el texto.
4. **P1** `growth_pct`: `null` si `prev=0` (no 100 %).
5. **P1** Ampliar pills/diccionario (PPA, rabia) **después** de que las 3 actuales tengan cuerpo.
6. **P2** spaCy / MiniLM / HDBSCAN (auditoría semanas 3–4).

### Cómo implementarlo

- `pipeline/run.py` `analyze_article`: gate de longitud antes de `extract_claims`.
- `nli.py` ya es conservador; no tocar umbrales en el sprint salvo bugs.
- Charts: campo `articles_without_claims` en `/charts` o `/kpis`.
- Tests: fixture rumor vs ficha WOAH → no Supported por token “brote”.
- **Libs P2:** `spacy` `es_core_news_md`; `sentence-transformers`; `hdbscan` o sklearn agglomerative.

---

## 11. Visión (CNN, OCR, hash, CLIP)

### Qué hay ahora

- Productivo: CLIP si está, si no ResNet18, si no heurística URL (`visual_encoder.py`).
- Académico: CNN 64×64 8 clases, pesos a menudo sintéticos (`train_cnn.py`).
- OCR: pytesseract / Paddle / alt RSS.
- Hash: aHash 8×8, Hamming ≤ 10 = reuse (`image_hash.py`).
- Thumbs de sala: `database/thumbs.py`; placeholders si falla la descarga.

### Por qué se siente pobre

Fotos de laboratorio en la sala. “Reuso 0 %” porque no hay pHash DCT. OCR vacío en Windows. Softmax uniforme se muestra como clasificación. El lab y la ficha hablan idiomas distintos (académico vs CLIP).

### Qué harías (3–6)

1. **P0** Nunca mostrar / exportar PNG sintético o `demo_seed_` como miniatura de noticia (auditar huecos de `is_news_thumb`).
2. **P0** En ficha: etiqueta del **encoder productivo**; CNN académica en `<details>`.
3. **P1** `imagehash.phash` 16×16; umbral Hamming documentado.
4. **P1** EasyOCR como fallback en Windows.
5. **P1** No clasificar placeholders; no exportarlos a `cnn_dataset`.
6. **P2** Dataset humano 50+/clase; CLIP reuse multimodal.

### Cómo implementarlo

- Blocklist en `database/cnn_dataset.py`. Ampliar `tests/test_thumbs.py`.
- UI ficha: una línea `CLIP · PHOTOGRAPH 0.72 · OCR: …`; softmax académico colapsado.
- **Libs P1:** `ImageHash`, `easyocr`. CLIP ya está previsto en `visual_encoder.py`.

---

## Matriz P0 / P1 / P2 (todos los módulos)

| ID | Ítem | Módulo | P | Esfuerzo |
|----|------|--------|---|----------|
| F1 | Querystring + `GET /articles` filtrado/paginado en servidor | transversal | P0 | 1.5 d |
| F2 | `GET /charts` series día×enfermedad + `empty` + `filter` por cubo | gráficas | P0 | 1 d |
| G1 | Small multiples + stacked area + composed dual axis + Brush | gráficas | P0 | 2 d |
| G2 | Tooltip con conteo + “Ver en sala” | gráficas | P0 | 0.5 d |
| G3 | Empty ≠ barra 0; `risk_null` fuera de 0–20; huecos temporales | gráficas | P0 | 0.5 d |
| G4 | Okabe–Ito + print CSS + export PNG | gráficas | P1 | 0.5 d |
| S1 | Pills desde API; filtros veredicto/origen/orden | sala | P0 | 1 d |
| S2 | Empty states; KPI alertas pendientes; sparkline real | sala | P0 | 0.5 d |
| S3 | Fetch por panel (no 7 endpoints) | sala | P1 | 0.5 d |
| M1 | Clic mapa → `?country=`; XX/INT fuera del mar | mapa | P0 | 0.5 d |
| M2 | Estados MX + coropleta | mapa | P1 | 2 d |
| R1 | Labels humanas; narrativas 0 ocultas; clic → sala | grafo | P0 | 0.5 d |
| R2 | Sidebar + physics toggle | grafo | P1 | 1 d |
| H1 | HITL con claim/evidencia; sin `prompt`; botones en ficha | HITL | P0 | 1.5 d |
| H2 | Historial + undo corto | HITL | P1 | 0.5 d |
| A1 | Ficha 2 columnas; reasons; claim↔evidencia | ficha | P0 | 1 d |
| U1 | Tabla fuentes + N artículos + Diferida + clic sala | fuentes | P0 | 0.5 d |
| Q1 | Banner % RSS/cuerpo/seed; MySQL ámbar | minería | P0 | 0.5 d |
| Q2 | Backup SQLite + Task Scheduler | minería | P0 | 0.5 d |
| N1 | No claims si texto corto; Unknown ≠ sin claims | NLP | P0 | 0.5 d |
| V1 | Thumbs sintéticas fuera de sala/export | visión | P0 | 0.5 d |
| C1 | Lab: fotos reales + banner académico | CNN | P0 | 0.5 d |

**P2 (fuera del sprint):** spaCy, HDBSCAN, scrape 5 parsers, CLIP reuse, heatmap 90 días, auth roles, Celery, Mapbox, ECharts.

---

## Sprint 2 semanas (1 dev + analista a ratos)

Supuesto: no se reescribe el pipeline ni se cambia de chart library. Se entrega un observatorio **usable** con gráficas que filtran la sala.

### Semana 1 — contrato y gráficas (P0)

| Día | Entrega |
|-----|---------|
| 1 | F1 querystring + artículos paginados. Tests API. |
| 2 | F2 payload charts (series, empty, risk_null, sample filter). |
| 3–4 | G1+G2+G3 `ChartsPanel` nuevo: multiples, stacked, dual axis, brush, tooltips clicables, empty states. |
| 5 | S1+S2 sala (pills API, filtros, empties). M1 mapa → país. Cablear `from`/`to` en mapa/grafo. |

**Demo viernes 1:** elegir un pico en el dual-axis → sala filtrada ese día y enfermedad. Mapa México → misma sala. Sin barras “Sin datos”.

### Semana 2 — resto del marco (P0 restante + P1 barato)

| Día | Entrega |
|-----|---------|
| 6 | H1 cola HITL rica + botones en ficha. |
| 7 | A1 ficha 2 columnas + similares con reasons. U1 tabla fuentes. |
| 8 | R1 grafo legible. Q1 banner calidad. V1/C1 higiene visual. N1 gate de claims. |
| 9 | Q2 backup. G4 paleta + print. S3 fetch por panel. H2 historial mínimo. |
| 10 | Pulido, Playwright (sala filtro, chart→sala, HITL validar), README 10 líneas “cómo leer las gráficas”. |

**Demo viernes 2:** analista valida una alerta desde la ficha; fuentes “Diferida” vs RSS; backup zip del día; gráfica impresa en PDF blanco.

### Fuera de alcance de las 2 semanas

- Reentrenar CNN con fotos reales (etiquetado humano, no código).
- NLI neuronal, embeddings, coropleta MX completa (M2 si sobra el día 9).
- Scrape de las 100 fuentes.
- Auth de verdad (token opcional sí se documenta).

---

## Qué no hacer

- No añadir un quinto bar chart “para que se vea lleno”.
- No migrar a ECharts/Nivo/D3 “porque Recharts es pobre”: el recorte de datos es el pobre.
- No pintar `count: 0` como categoría “Sin datos”.
- No abrir la ficha al azar desde mapa/chart (salvo link explícito en el tooltip).
- No usar la CNN académica como detector de fake news.
- No dejar que Ollama escriba el veredicto.
- No reescribir Next.js ni fusionar repos.
- No git-commit de este plan junto con secrets o `tnb.db`.

---

## Apéndice — archivos a tocar primero

| Pieza | Ruta |
|-------|------|
| Filtros UI | `frontend/src/Observatory.tsx`, `frontend/src/api.ts` |
| Gráficas | `frontend/src/components/ChartsPanel.tsx`, `database/store.py` `chart_payload`, `GET /charts` |
| Mapa | `frontend/src/components/MapView.tsx`, `database/geo.py`, `GET /geo` |
| Grafo | `frontend/src/components/NetworkGraph.tsx`, `store.network_graph` |
| HITL | `HitlQueue` en `Observatory.tsx`, `GET/POST /alerts` |
| Ficha | `frontend/src/AnalysisPage.tsx` |
| Fuentes | `SourcesPanel` en `Observatory.tsx`, `GET /sources` |
| Lab | `frontend/src/CnnLab.tsx` |
| Ciclo | `pipeline/run.py`, `api.ts` `cycle()` |
| Paleta | nuevo `frontend/src/chartTheme.ts` |

Auditoría de arquitectura (ingesta 90 % scrape, NLI, 24/7 Windows): seguir [`AUDITORIA.md`](AUDITORIA.md). Este archivo no la sustituye: la traduce a trabajo de UI y de agregados para las **próximas dos semanas**.
