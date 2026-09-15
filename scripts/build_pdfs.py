"""Build the two project PDFs (AI-writing field guide + observatory brief)."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = HexColor("#1a2332")
MUTED = HexColor("#4b5563")
LINE = HexColor("#d1d5db")
ACCENT = HexColor("#0f766e")
PANEL = HexColor("#f4f1ea")
NAVY = HexColor("#041428")

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = Path.home() / "Desktop"
DOCS = ROOT / "docs"
LOGO = ROOT / "branding" / "logo.png"


def _font() -> str:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        p = Path(path)
        if p.is_file():
            pdfmetrics.registerFont(TTFont("Body", str(p)))
            bold = path.replace("Arial.ttf", "Arial Bold.ttf").replace("arial.ttf", "arialbd.ttf")
            bold = bold.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
            bold = bold.replace("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf")
            if Path(bold).is_file():
                pdfmetrics.registerFont(TTFont("BodyBold", bold))
            else:
                pdfmetrics.registerFont(TTFont("BodyBold", str(p)))
            return "Body"
    return "Helvetica"


def _styles(font: str):
    bold = "BodyBold" if font == "Body" else "Helvetica-Bold"
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("H1c", fontName=bold, fontSize=18, leading=22, textColor=INK, spaceAfter=8))
    ss.add(ParagraphStyle("H2c", fontName=bold, fontSize=13, leading=17, textColor=ACCENT, spaceBefore=12, spaceAfter=6))
    ss.add(ParagraphStyle("H3c", fontName=bold, fontSize=11, leading=14, textColor=INK, spaceBefore=8, spaceAfter=4))
    ss.add(ParagraphStyle("Th", fontName=bold, fontSize=9, leading=12, textColor=white, spaceAfter=0))
    ss.add(ParagraphStyle("Bodyc", fontName=font, fontSize=10, leading=14, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6))
    ss.add(ParagraphStyle("Notec", fontName=font, fontSize=9, leading=12, textColor=MUTED, alignment=TA_LEFT, spaceAfter=8))
    ss.add(ParagraphStyle("Codec", fontName="Courier", fontSize=8, leading=11, textColor=INK, backColor=PANEL, leftIndent=4, rightIndent=4))
    ss.add(ParagraphStyle("Bulletc", fontName=font, fontSize=10, leading=13, textColor=INK, leftIndent=12, spaceAfter=2))
    return ss, bold


def _paint_bar(canvas, doc, right_label: str) -> None:
    canvas.saveState()
    bar_h = 16 * mm
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - bar_h, A4[0], bar_h, fill=1, stroke=0)
    text_x = 18 * mm
    if LOGO.is_file():
        canvas.drawImage(
            str(LOGO),
            14 * mm,
            A4[1] - bar_h + 2.5 * mm,
            width=11 * mm,
            height=11 * mm,
            mask="auto",
        )
        text_x = 28 * mm
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(text_x, A4[1] - 10 * mm, "The NewsBreakers")
    canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 10 * mm, right_label)
    canvas.setFillColor(LINE)
    canvas.rect(0, 12 * mm, A4[0], 0.4, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18 * mm, 6 * mm, doc.title)
    canvas.drawRightString(A4[0] - 18 * mm, 6 * mm, str(canvas.getPageNumber()))
    canvas.restoreState()


def _header_footer(canvas, doc):
    _paint_bar(canvas, doc, "Señales de escritura IA")


def _obs_footer(canvas, doc):
    _paint_bar(canvas, doc, "informe técnico v. 2.2")


def build_ai_pdf(path: Path) -> None:
    font = _font()
    ss, _bold = _styles(font)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        title="Señales de escritura generada por IA",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=24 * mm,
        bottomMargin=20 * mm,
    )
    P, H1, H2, H3, N = ss["Bodyc"], ss["H1c"], ss["H2c"], ss["H3c"], ss["Notec"]
    story = []
    story.append(Paragraph("Señales de escritura generada por IA", H1))
    story.append(Paragraph(
        "Lista de campo tomada de <b>Wikipedia:Signs of AI writing</b> "
        "(WikiProject AI Cleanup). Es descriptiva, no una política. "
        "Un rasgo solo no prueba nada: los modelos se entrenaron con prosa humana, "
        "y la prosa humana ya copia tics de chatbot. Varios rasgos juntos sí merecen revisión.",
        P,
    ))
    story.append(Paragraph(
        "La misma página avisa: herramientas tipo GPTZero se equivocan. "
        "Un estudio de 2025 dejó a personas cerca del azar al distinguir textos. "
        "Este PDF no es un «pasa el detector»; es un catálogo de hábitos que hay que no copiar "
        "en el código y los documentos de The NewsBreakers.",
        N,
    ))

    story.append(Paragraph("1. Contenido", H2))
    items = [
        "<b>Importancia inflada.</b> stands as, testament, pivotal role, underscores, evolving landscape, indelible mark, deeply rooted. Convierte un dato menor en «legado».",
        "<b>Notabilidad de plantilla.</b> independent coverage, profiled in, active social media presence. Lista de medios en vez de un hecho.",
        "<b>Análisis superficial.</b> Gerundio final: highlighting, ensuring, reflecting, fostering, encompassing. Añade opinión sin fuente.",
        "<b>Atribución vaga.</b> «experts say», «observers note», «it is widely regarded». Nadie concreto.",
        "<b>Cierre de deberes.</b> Sección Challenges / Future prospects que podría pegarse a cualquier tema.",
        "<b>Títulos tratados como nombre propio.</b> El modelo convierte un lema de Wikipedia en entidad.",
    ]
    for it in items:
        story.append(Paragraph("• " + it, ss["Bulletc"]))

    story.append(Paragraph("2. Léxico que se acumula", H2))
    story.append(Paragraph(
        "2023–2024: Additionally, boasts, delve, intricate, tapestry, testament, vibrant, meticulous, pivotal, underscore. "
        "2024–2025: align with, fostering, showcasing, highlighting, enhance, enduring. "
        "Una palabra suelta no cuenta. Un párrafo con cuatro de estas, sí.",
        P,
    ))
    story.append(Paragraph("3. Gramática y ritmo", H2))
    for it in [
        "Evita el verbo ser/estar («is/are») y da rodeos («serves as a means of»).",
        "Paralelismos negativos: «It’s not just X, it’s Y».",
        "Regla de tres automática: tres sustantivos, tres adjetivos, tres gerundios.",
        "Variación elegante: el mismo objeto cambia de nombre cada frase para no repetir.",
        "Title Case En Cada Encabezado Corto.",
    ]:
        story.append(Paragraph("• " + it, ss["Bulletc"]))

    story.append(Paragraph("4. Formato", H2))
    for it in [
        "Negritas a granel, listas verticales con encabezado en cada viñeta.",
        "Rayas em dash (—) en cada inciso.",
        "Tablas donde bastaba una frase.",
        "Comillas curvas “ ” y apóstrofos ’ pegados por el modelo.",
        "Saltar niveles de título (H1 → H3).",
        "Líneas temáticas (---) antes de un heading.",
        "Markdown crudo (*, #, ```) donde el destino no es Markdown.",
        "Placeholders: TODO, [Insert citation], lorem, turn0search0, oaicite, grok_card.",
        "Emojis como formato (✅ ❌ 🚀) en texto técnico.",
        "Cortes abruptos o «As an AI language model…».",
    ]:
        story.append(Paragraph("• " + it, ss["Bulletc"]))

    story.append(Paragraph("5. En código (mismo origen, otro síntoma)", H2))
    for it in [
        "Comentario que repite la línea: `# Increment counter` encima de `n += 1`.",
        "Nombres Manager/Helper/Util sin comportamiento.",
        "README con journey, seamless, leverage, robust pipeline.",
        "Commits «Improve overall architecture and enhance user experience».",
        "Tests llamados test_it_works con un assert True.",
        "Bloques try/except que tragan el error y siguen.",
    ]:
        story.append(Paragraph("• " + it, ss["Bulletc"]))

    story.append(Paragraph("6. Cómo escribir en este repo (reglas)", H2))
    story.append(Paragraph(
        "Estas reglas están también en <b>.cursor/rules/escritura-humana.mdc</b>.",
        P,
    ))
    for it in [
        "Di el hecho: archivo, puerto, umbral, comando.",
        "Una idea, una frase. Si cabe un punto, no uses la raya.",
        "Prohibido el léxico de la sección 2 en comentarios, README y commits.",
        "No cierres con «en resumen» ni con un párrafo de legado.",
        "Comentarios solo para el porqué. El qué va en el identificador.",
        "Español de consola: Abrir, Parar, Minar. Sin eslogan.",
        "Si dudas, borra el adjetivo.",
    ]:
        story.append(Paragraph("• " + it, ss["Bulletc"]))

    story.append(Paragraph(
        "Consulta: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing",
        N,
    ))
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)


def _table(ss, rows, widths):
    data = []
    for i, row in enumerate(rows):
        cells = []
        for c in row:
            style = ss["Th"] if i == 0 else ss["Bulletc"]
            cells.append(Paragraph(str(c), style))
        data.append(cells)
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 1), (-1, -1), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _box_row(ss, rows):
    data = [[Paragraph(c, ss["Bulletc"]) for c in row] for row in rows]
    t = Table(data, colWidths=[55 * mm, 55 * mm, 55 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build_obs_pdf(path: Path) -> None:
    font = _font()
    ss, _ = _styles(font)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        title="The NewsBreakers: observatorio de desinformación zoosanitaria (v. 2.2)",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=24 * mm,
        bottomMargin=20 * mm,
    )
    P, H1, H2, H3, N = ss["Bodyc"], ss["H1c"], ss["H2c"], ss["H3c"], ss["Notec"]
    B = ss["Bulletc"]
    story = []
    if LOGO.is_file():
        story.append(RLImage(str(LOGO), width=32 * mm, height=32 * mm))
        story.append(Spacer(1, 6))
    story.append(Paragraph("The NewsBreakers", H1))
    story.append(Paragraph(
        "Observatorio de desinformación zoosanitaria. Informe técnico del framework, "
        "v. 2.2. México, 12 de septiembre de 2026. Sustituye al v. 2.1.",
        N,
    ))
    story.append(Paragraph(
        "Vigilancia de tres enfermedades pecuarias: gusano barrenador del ganado "
        "(<i>Cochliomyia hominivorax</i>), influenza aviar de alta patogenicidad y peste porcina clásica. "
        "El operador trabaja en una sala: ve notas, riesgo, alertas, mapa, gráficas, grafo y visión. "
        "El sistema no decide la verdad. Extrae afirmaciones, cruza fichas oficiales, calcula un riesgo "
        "y deja la última palabra al analista (Validar, Descartar, Modificar).",
        P,
    ))
    story.append(Paragraph(
        "Cómo leer este documento. Las secciones van en el orden de uso: abrir la app, leer la sala, "
        "abrir una ficha, revisar, minar, y luego mapa, gráficas y grafo. "
        "No se etiquetan noticias como fake o real.",
        P,
    ))

    story.append(Paragraph("1. Qué es y qué no es", H2))
    story.append(_table(ss, [
        ["Paso", "Lo que sí", "Lo que no"],
        ["Fetch", "RSS, GDELT y API del catálogo. Título, fecha, enlace, cuerpo si viene.",
         "No entra al HTML de redacciones que exigen rastreador a medida (scrape diferido)."],
        ["Deduplicado", "Evita contar dos veces la misma URL o huella de texto.",
         "No fusiona versiones periodísticas distintas."],
        ["Relevancia", "Tira lo que no nombra las tres enfermedades.",
         "No es un fact-checker general."],
        ["Afirmaciones", "Parte el texto y lo cruza con fichas WOAH, USDA, FAO, SENASICA.",
         "No atribuye intención ni autoría legal."],
        ["Riesgo", "Suma seis señales (motor weighted_v3). Ordena la cola.",
         "No es un % de que la nota sea falsa."],
        ["CNN", "Sugiere el tipo de imagen (acta, meme, foto…).",
         "No certifica si una foto está manipulada."],
        ["HITL", "Validar, Descartar o Modificar en la ficha y en Revisión.",
         "No sustituye el dictamen sanitario oficial."],
    ], [32 * mm, 68 * mm, 65 * mm]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Cómo se abre hoy", H2))
    story.append(Paragraph(
        "El producto es una app de escritorio. No se trabaja en una pestaña de Chrome. "
        "La sala, la ficha, el mapa, las gráficas y el grafo son los mismos en cualquier PC. "
        "Cambia el archivo de instalación: el de macOS, el de Windows o el de Linux, según la máquina. "
        "Doble clic. El API local queda en 127.0.0.1:8010 y sirve la UI. "
        "Los datos viven en la carpeta de la aplicación del usuario; no se van con el instalador. "
        "Los enlaces externos salen al navegador del sistema. "
        "Tras un cambio de interfaz hay que cerrar la app del todo y volver a abrir. "
        "Código: https://github.com/JAVGP444/the-newsbreakers-framework",
        P,
    ))
    story.append(_table(ss, [
        ["Uso", "Cómo", "Puertos"],
        ["App instalada", "Instalador o binario del sistema en uso. Doble clic.", "API :8010; la UI la sirve el API"],
        ["Desarrollo", "Clone del repo y script de arranque.", "UI :5173 · API :8010"],
    ], [42 * mm, 78 * mm, 45 * mm]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "SQLite (<b>data/processed/tnb.db</b>) abre la sala. MySQL en Docker es almacén opcional. "
        "Sin Docker el observatorio funciona. Postgres, Mongo y Redis del compose no hacen falta para la UI.",
        P,
    ))

    story.append(Paragraph("3. Por qué esas tres enfermedades", H2))
    story.append(_table(ss, [
        ["Enfermedad", "Por qué entra", "Qué se vigila en medios"],
        ["Gusano barrenador (C. hominivorax)",
         "Reemergencia México–Centroamérica; pánico en caza y traspatio.",
         "Avisos a cazadores, heridas, rumores de mosca estéril."],
        ["Influenza aviar (HPAI)",
         "Circulación global; el lenguaje técnico se deforma en redes.",
         "Granjas, sacrificio, «gripe del pollo» como pánico alimentario."],
        ["Peste porcina clásica",
         "Declaración obligatoria; se confunde con africana en titulares.",
         "Cierres de granja, contrabando, vacunas «ocultas»."],
    ], [48 * mm, 58 * mm, 59 * mm]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Hay vocabulario estable en español e inglés, daño mediático concreto y fuentes abiertas. "
        "COVID humano, dengue o vacunas infantiles no entran: diluirían el filtro y la cola humana.",
        P,
    ))

    story.append(Paragraph("4. Países e idiomas", H2))
    story.append(Paragraph(
        "El centro operativo es México: sala en español, autoridad pecuaria nacional, corredor del barrenador. "
        "El mapa no es un GIS oficial: sitúa dónde el texto dice que ocurre algo. "
        "El inglés entra por GDELT, ciencia y cables. El conmutador «Traducir al español» es capa de lectura: "
        "el artículo se guarda como llegó; la traducción se cachea. El texto que ya está en español no se reescribe. "
        "Por defecto la traducción usa Google gtx; Ollama solo si TNB_TRANSLATE_OLLAMA=1.",
        P,
    ))

    story.append(Paragraph("5. Medios y catálogo", H2))
    story.append(_table(ss, [
        ["Tipo", "Acceso", "Papel"],
        ["GDELT DOC 2.0", "API", "Radar. Mucho volumen, poco cuerpo. El lede de GDELT (fecha compacta + sopa de palabras) no se muestra en sala ni en ficha."],
        ["Prensa pecuaria y científica", "RSS", "Vocabulario técnico; a veces el rumor nace de un titular correcto mal leído."],
        ["Prensa general", "RSS", "Encuadre nacional."],
        ["Organismos (WOAH, FAO, OMS, USDA, SENASICA)", "RSS / ficha", "Ancla de evidencia. Un 404 se registra y el ciclo sigue."],
        ["YouTube / redes", "Catálogo; ingestión desigual", "Donde circula la imagen recortada."],
        ["HTML scrape", "Diferido", "No infla el contador. Mantener selectores CSS es otro producto."],
    ], [48 * mm, 32 * mm, 85 * mm]))

    story.append(PageBreak())
    story.append(Paragraph("6. Cómo está armado el framework", H2))
    story.append(Paragraph(
        "Monorepo local. La sala no habla con SQLite: pasa por FastAPI en 127.0.0.1:8010. "
        "Si se apaga el API, la ventana puede pintar el cascarón y decir que no hay servidor. Los datos no se borran al cerrar.",
        P,
    ))
    story.append(_box_row(ss, [[
        "<b>Ventana</b><br/>Nativa. Misma UI compilada (frontend/dist) en cualquier PC.",
        "<b>API</b><br/>/articles /stats /cycle /alerts /geo /graph /charts /translate /cnn",
        "<b>Pipeline</b><br/>pipeline/run.py: catálogo vencido, fetch, dedup, relevancia, claims, NLI, riesgo, imagen.",
    ], [
        "<b>Modelos</b><br/>vision_cnn_v1.pt · NLI léxico vs fichas oficiales · riesgo weighted_v3.",
        "<b>Datos</b><br/>tnb.db · imágenes en storage/ · caché de traducción.",
        "<b>Empaque</b><br/>packaging/build.py arma el paquete nativo de la máquina donde se corre.",
    ]]))
    story.append(Spacer(1, 8))
    story.append(_table(ss, [
        ["Ruta", "Función"],
        ["ingestion/", "Fetch RSS/API/GDELT, normalización, desduplicado."],
        ["pipeline/run.py", "Orquesta un ciclo."],
        ["api/", "Contrato HTTP, HITL, estáticos de la UI."],
        ["frontend/", "Tablero Vite 5. Sala, ficha, mapa, gráficas, grafo, CNN."],
        ["ai-service/", "Riesgo, NLI, OCR, CNN, LLM opcional."],
        ["database/", "Store SQLite, filtros, thumbs."],
        ["config/", "Rutas de datos, umbrales, intervalo de minería."],
        ["desktop/", "Arranque: API local + ventana."],
        ["packaging/", "Paquete nativo según el sistema (build.py)."],
        ["models/cnn/", "Pesos .pt y dataset visual."],
    ], [42 * mm, 123 * mm]))

    story.append(Paragraph("7. El ciclo de minería", H2))
    story.append(Paragraph(
        "Orden real: catálogo → fuentes vencidas rss/api → fetch → dedup URL+texto → relevancia zoosanitaria "
        "→ afirmaciones y entidades → NLI contra fichas oficiales → riesgo y alerta → imagen y CNN. "
        "El scrape no está en esa fila: se marca diferido.",
        P,
    ))
    story.append(Paragraph(
        "Pulsar «Ejecutar ciclo» no dispara todo el catálogo. Solo las fuentes debidas. "
        "Un 404 de un feed no tumba el ciclo. Cero artículos nuevos con 57 ítems traídos es diseño: "
        "duplicados y fuera de las tres enfermedades. Para crecer el corpus: «Ejecutar ciclo» en la app "
        "o el script de minería del repo.",
        P,
    ))

    story.append(Paragraph("8. Riesgo (weighted_v3) y veredictos", H2))
    story.append(Paragraph(
        "No hay un único «score de fake». El recuadro 0–100 es la suma ponderada de seis señales. "
        "Un 20 no afirma que el hecho sea falso: afirma poco peso de alarma. Un 62 pide ojos humanos.",
        P,
    ))
    story.append(_table(ss, [
        ["Señal", "Peso", "Qué mide"],
        ["Discrepancia con evidencia", "0.28", "NLI vs fichas oficiales. Unknown con poco overlap no es respaldado."],
        ["Fiabilidad de la fuente", "0.22", "Autoridad A (WOAH/SENASICA) a E (redes). GDELT/prensa = C."],
        ["Imagen reusada", "0.18", "pHash de la foto en otras notas."],
        ["Gravedad de la afirmación", "0.18", "Brote, cifra, «oculta»; un título solo pesa poco."],
        ["Narrativa en crecimiento", "0.08", "Pico del mismo relato en el periodo."],
        ["Anomalía visual", "0.06", "Clase CNN o falta de imagen."],
    ], [48 * mm, 22 * mm, 95 * mm]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Veredictos de tarjeta: Respaldado, Insuficiente, Posiblemente engañoso, Contradicho, Revisión humana. "
        "Insuficiente: no hay base aún para un juicio fuerte. "
        "NLI de una afirmación: Respaldado / Contradicho / Sin verificar (Unknown). "
        "Unknown es el valor por defecto cuando el cruce léxico no alcanza (hace falta overlap mínimo con la ficha).",
        P,
    ))

    story.append(Paragraph("9. Sala", H2))
    story.append(Paragraph(
        "Las tarjetas ya no apilan estados ni el cuerpo basura de GDELT. Cada una muestra: miniatura, "
        "tipo de fuente, veredicto, riesgo, título en dos líneas, pie con host · fecha de publicación · Original. "
        "La fecha es la de la nota (published_at), no la de minado. Las fechas compactas GDELT (20260912T014500Z) "
        "se leen como 12 sep 2026. Si no hay publicación: «Sin fecha de publicación». "
        "Orden de la lista: publicación primero, para que una nota vieja recién minada no salte al tope.",
        P,
    ))
    story.append(Paragraph(
        "La tira Respaldado / Insuficiente / … está en Sala, no dentro de cada ficha. "
        "«Qué es cada uno» se abre ahí. Sin «Leer más» ni extracto de keywords H5N1/SENASICA/WOAH pegadas al título. "
        "Navegación: Sala · Revisión · Mapa · Gráficas · Grafo · CNN · Fuentes. "
        "Los filtros de la sala (enfermedad, país, fechas, origen) se arrastran a mapa, gráficas y grafo por la misma querystring.",
        P,
    ))

    story.append(Paragraph("10. Ficha (clic en una tarjeta)", H2))
    story.append(Paragraph(
        "Layout de nota + veredicto, no una planilla de fórmulas.",
        P,
    ))
    story.append(_table(ss, [
        ["Columna", "Qué se ve"],
        ["Izquierda: la nota",
         "Foto, fuente, fecha, cuerpo limpio (o «esta nota no trajo cuerpo»), enlace a la original, "
         "El caso (enfermedad, animal, país) y línea de tiempo si hay fechas."],
        ["Derecha: la lectura",
         "Tipo, veredicto, riesgo N/100, una frase (p. ej. «Relevante, pero sin evidencia suficiente»), "
         "Validar / Descartar / Modificar, afirmaciones con postura, chips WOAH / USDA / FAO."],
        ["Plegado",
         "«Cómo se calculó el riesgo» (seis barras y motivos). «Cruce con fichas oficiales» al abrir una afirmación. "
         "La CNN de la imagen, en galería, bajo «Tipo de imagen»."],
    ], [42 * mm, 123 * mm]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Los enlaces «Abrir noticia original» y las fichas oficiales salen al navegador del sistema.",
        P,
    ))

    story.append(Paragraph("11. Revisión humana", H2))
    story.append(Paragraph(
        "Pestaña Revisión: cola pending_review. En la ficha, los mismos tres botones. "
        "Validar, Descartar o Modificar (motivo obligatorio). El veredicto queda en el artículo. "
        "La revisión no pide token de API aparte: POST /articles/{id}/review.",
        P,
    ))

    story.append(Paragraph("12. Mapa de menciones", H2))
    story.append(Paragraph(
        "Pestaña <b>Mapa</b> (/mapa). GET /geo. Leaflet: un círculo por país. El radio crece con el recuento, "
        "no con la gravedad. Clic en un círculo o en la lista del costado abre la sala filtrada por ese país. "
        "Si el texto no trae país, va a la línea «Sin ubicar». "
        "No es el mapa de focos de SENASICA ni de WOAH: sitúa dónde el artículo dice que ocurre algo. "
        "En la ficha hay un mapa chico si hay coordenadas. Los filtros de la sala se aplican aquí.",
        P,
    ))

    story.append(Paragraph("13. Gráficas", H2))
    story.append(Paragraph(
        "Pestaña <b>Gráficas</b> (/graficas). GET /charts. Recharts. Tres recuadros; cada uno trae «Cómo leerlo». "
        "Clic en una barra o en un color abre esas notas en la sala. Vacío: aún no hay minería, o el filtro no deja nada.",
        P,
    ))
    story.append(_table(ss, [
        ["Gráfico", "Qué cuenta"],
        ["¿De qué enfermedades hablan?",
         "Barras horizontales. Una nota puede nombrar más de una. Número y % sobre el recorte."],
        ["¿De dónde sale el contenido?",
         "Barras: oficial (SENASICA, OMSA, CDC…), científico, redes/YouTube, prensa."],
        ["¿Qué concluyó el análisis?",
         "Pastel: respaldado, contradicho, insuficiente, revisión humana."],
    ], [52 * mm, 113 * mm]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Si casi todo cae en una semana y esa semana coincide con un ciclo de minado, el recuadro avisa: "
        "suele ser el día en que se guardó, no siempre el de publicación.",
        P,
    ))

    story.append(Paragraph("14. Grafo de narrativas", H2))
    story.append(Paragraph(
        "Pestaña <b>Grafo</b> (/grafo). GET /graph. vis-network. Nodos: fuente (azul), enfermedad (verde), "
        "narrativa (amarillo), artículo. El tamaño sigue el recuento. Clic en fuente o enfermedad filtra la sala. "
        "Clic en un artículo abre la ficha. Leyenda al pie; si hay recorte: «n de N artículos». "
        "Vacío: «No hay co-ocurrencias con este filtro.» Tope de muestra 10–80 (por defecto 40). "
        "Sirve para ver si varias notas empujan el mismo relato; no es un grafo de contactos epidemiológicos.",
        P,
    ))

    story.append(Paragraph("15. CNN y fuentes", H2))
    story.append(Paragraph(
        "<b>CNN</b> (/cnn). Lab visual. Ocho clases: documento oficial, captura de noticia, red social, meme, "
        "infografía, contenido pecuario, fotografía, posible manipulación. Propone el tipo de imagen; no cierra el expediente.",
        P,
    ))
    story.append(Paragraph(
        "<b>Fuentes</b> (/fuentes). Salud del catálogo: método de captura, última visita, fallos, estado. "
        "Un feed 404 se ve aquí; no se interpreta como «cero desinformación».",
        P,
    ))

    story.append(Paragraph("16. Visión", H2))
    story.append(Paragraph(
        "La CNN no lee el artículo. Mira la imagen y propone un género visual. "
        "El mismo rumor cambia de peso si viaja como acta, pantallazo, meme o foto de un animal. "
        "Entrenar es local: python -m ai_service.vision.train_cnn. No hay «la IA se actualiza sola». "
        "Un dataset sesgado (p. ej. solo membretes) no autoriza a citar accuracy. "
        "POTENTIALLY_MANIPULATED es señal débil, no peritaje.",
        P,
    ))

    story.append(Paragraph("17. Parámetros de operación", H2))
    story.append(_table(ss, [
        ["Parámetro", "Criterio"],
        ["Alerta", "Umbral de laboratorio ~55/100. Por debajo existe el ítem; no entra a la cola roja."],
        ["Fuentes por ciclo", "Solo vencidas rss/api. El tope (p. ej. 40) no son 118 descargas."],
        ["Scrape HTML", "Anotado, no descargado."],
        ["Intervalo", "Por defecto 30 min (TNB_MINE_INTERVAL_MINUTES)."],
        ["Sala", "Paginada. Orden por fecha de publicación."],
        ["Grafo", "Muestra 10–80 artículos (por defecto 40)."],
    ], [48 * mm, 117 * mm]))

    story.append(Paragraph("18. Por qué se hizo así", H2))
    for it in [
        "<b>Local primero.</b> El índice no depende de un SaaS para abrir la sala. SQLite en el portátil; MySQL si hay Docker.",
        "<b>App, no pestaña.</b> Un mismo escritorio en cualquier PC. Enlaces oficiales sí salen al navegador.",
        "<b>RSS/API antes que scrape.</b> Cincuenta extractores CSS son un medio, no un observatorio.",
        "<b>Relevancia estricta.</b> Mejor pocas notas de las tres enfermedades que cientos de «salud» genérica.",
        "<b>Humano al final.</b> Seis señales y una cola. Ni un modelo pequeño ni una CNN de pocas fotos cierran el caso.",
        "<b>Traducción como capa.</b> No se pisa el original.",
        "<b>Vista, no GIS.</b> Mapa, barras y grafo llevan a la sala. No sustituyen el mapa oficial de focos.",
    ]:
        story.append(Paragraph("• " + it, B))

    story.append(Paragraph("19. Límites", H2))
    for it in [
        "El catálogo no es N descargas por clic. Solo las vencidas rss/api.",
        "Feeds 404 son error de fuente, no «cero desinformación».",
        "GDELT a menudo no trae cuerpo: la ficha lo dice y manda al original.",
        "El overlap NLI es léxico. Cuatro palabras compartidas con WOAH no respaldan.",
        "Sin API local no hay sala.",
        "El mapa no es incidencia epidemiológica. El grafo no es red de contactos.",
        "La CNN subalimentada no es detector de deepfakes.",
        "Los recuentos de un ciclo de laboratorio no se citan como incidencia epidemiológica.",
    ]:
        story.append(Paragraph("• " + it, B))

    story.append(Paragraph("20. Instalar y construir", H2))
    story.append(Paragraph(
        "Se baja el instalador del sistema que se usa. Python 3.12, Node LTS y Git bastan para armarla en esa máquina.",
        P,
    ))
    story.append(Preformatted(
        "git clone https://github.com/JAVGP444/the-newsbreakers-framework.git\n"
        "cd the-newsbreakers-framework\n"
        "python -m venv .venv\n"
        "python -m pip install -U pip\n"
        "python -m pip install -r requirements.txt\n"
        "cd frontend && npm install && npm run build && cd ..\n"
        "python packaging/build.py",
        ss["Codec"],
    ))
    story.append(Paragraph(
        "Ese comando deja el paquete nativo en dist/. El script de arranque del repo sirve para desarrollo "
        "(UI :5173 · API :8010) sin pasar por el instalador.",
        P,
    ))

    story.append(Paragraph("21. Comprobar", H2))
    story.append(Preformatted(
        "pytest tests -q\n"
        "curl -s http://127.0.0.1:8010/health\n"
        "curl -s http://127.0.0.1:8010/stats",
        ss["Codec"],
    ))

    story.append(Paragraph("22. Cierre", H2))
    story.append(Paragraph(
        "The NewsBreakers es un marco para no perder tres enfermedades pecuarias en el ruido de los feeds. "
        "Se abre, se lee como nota (sala y ficha), se mira en mapa, gráficas y grafo, se contrasta con fichas oficiales "
        "y se cierra con un humano. "
        "La prevención, aquí, no es un modelo que apaga rumores. Es llegar a la nota con el original intacto.",
        P,
    ))
    story.append(Paragraph(
        "Cómo citar: The NewsBreakers. (2026). Observatorio de desinformación zoosanitaria: arquitectura, método y uso "
        "(Informe técnico, v. 2.2) [Documento de trabajo]. México.",
        N,
    ))

    story.append(Paragraph("Referencias (selección)", H2))
    refs = [
        "American Psychological Association. (2020). <i>Publication manual of the American Psychological Association</i> (7.a ed.).",
        "Leetaru, K. y Schrodt, P. A. (2013). GDELT: Global data on events, location and tone [Conjunto de datos]. https://www.gdeltproject.org",
        "Organización Mundial de Sanidad Animal. (s. f.). WOAH. https://www.woah.org",
        "Paszke, A. et al. (2019). PyTorch: An imperative style, high-performance deep learning library.",
        "Ramírez, S. (s. f.). FastAPI. https://fastapi.tiangolo.com",
        "SQLite Development Team. (s. f.). SQLite. https://www.sqlite.org",
        "The GDELT Project. (2017, 30 de agosto). GDELT DOC 2.0 API debuts.",
        "You, E. (s. f.). Vite. https://vitejs.dev",
    ]
    for r in refs:
        story.append(Paragraph("• " + r, B))

    doc.build(story, onFirstPage=_obs_footer, onLaterPages=_obs_footer)


def main() -> None:
    DESKTOP.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    downloads = Path.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    obs_name = "The-NewsBreakers-observatorio.pdf"
    targets = [
        DOCS / obs_name,
        downloads / obs_name,
        DESKTOP / obs_name,
    ]
    for dest in targets:
        dest.parent.mkdir(parents=True, exist_ok=True)
        build_obs_pdf(dest)
        print(dest)


if __name__ == "__main__":
    main()
