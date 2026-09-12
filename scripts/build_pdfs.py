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
    _paint_bar(canvas, doc, "observatorio")


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
        title="The NewsBreakers — observatorio",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=24 * mm,
        bottomMargin=20 * mm,
    )
    P, H1, H2 = ss["Bodyc"], ss["H1c"], ss["H2c"]
    story = []
    if LOGO.is_file():
        story.append(RLImage(str(LOGO), width=38 * mm, height=38 * mm))
        story.append(Spacer(1, 8))
    story.append(Paragraph("The NewsBreakers — observatorio 24/7", H1))
    story.append(Paragraph(
        "Vigilancia de desinformación en salud animal (gusano barrenador, gripe aviar, peste porcina clásica). "
        "Este PDF actualiza el briefing anterior: el dashboard vive en este repo, no en Next.js :3003.",
        P,
    ))

    story.append(Paragraph("Cómo se enciende (Mac, Windows, Linux)", H2))
    story.append(Paragraph(
        "Clona el repo. Python 3.12 y Node 18+. Docker es opcional (solo MySQL warehouse). "
        "Mac: <b>mac/Instalar-y-abrir.command</b>. Windows: <b>windows/abrir.bat</b>. "
        "Linux: <b>linux/abrir.sh</b>. UI en http://127.0.0.1:5173  ·  API en :8010.",
        P,
    ))

    story.append(Paragraph("Pipeline", H2))
    story.append(_box_row(ss, [[
        "<b>1 Watchlist</b><br/>RSS, GDELT, HTML. Solo fuentes del catálogo.",
        "<b>2 Filtro</b><br/>Relevancia por palabra completa. Titular sin sanidad animal → no entra a Sala.",
        "<b>3 NLP + visión</b><br/>Claims, NLI, OCR, CNN 8 clases, pHash.",
    ], [
        "<b>4 Evidencia</b><br/>Fuentes oficiales primero. El LLM no cierra la verdad.",
        "<b>5 Riesgo + HITL</b><br/>Alertas pending_review. Revisión humana.",
        "<b>6 Persistencia</b><br/>SQLite tnb.db. MySQL dual-write si Docker está arriba.",
    ]]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Sala, gráficas y grafo", H2))
    story.append(Paragraph(
        "Sala lista documentos recientes. Cada tarjeta abre la ficha y, si hay URL pública, "
        "«Abrir noticia». Gráficas (Recharts) recortan por enfermedad y fecha. "
        "Grafo (vis-network) une enfermedades, fuentes y notas. Clic filtra la sala.",
        P,
    ))

    story.append(Paragraph("Qué cambió respecto al PDF anterior", H2))
    for it in [
        "Filtro de Sala: guerra, cultura y pies de página de RSS ya no se cuelan. «rabia» no coincide dentro de Arabia.",
        "Traductor EN→ES por Google gtx (Ollama queda apagado salvo TNB_TRANSLATE_OLLAMA=1). El texto que ya está en español no se reescribe.",
        "Cada ciclo (POST /cycle o minar-ya) recorre la watchlist vencida y suma artículos nuevos; los duplicados se saltan.",
        "CNN: pesos en models/cnn/vision_cnn_v1.pt. Lab en /cnn. Reentrenar: python -m ai_service.vision.train_cnn.",
        "Arranque único por SO. Generador_Excel_Enfermedades es opcional.",
        "Fotos minadas no van al git. SQLite de trabajo sí (snapshot tnb.db).",
    ]:
        story.append(Paragraph("• " + it, ss["Bulletc"]))

    story.append(Paragraph("Docker y SQL", H2))
    story.append(Preformatted(
        "docker compose up -d mysql\n"
        "cp .env.example .env   # o copy en Windows\n"
        "python mine_loop.py    # dual-write SQLite + MySQL",
        ss["Codec"],
    ))
    story.append(Paragraph(
        "Sin Docker el observatorio usa SQLite. Postgres/Mongo/Redis en compose son reserva, no hace falta abrirlos para la UI.",
        P,
    ))

    story.append(Paragraph("Comprobar", H2))
    story.append(Preformatted(
        "pytest tests -q\n"
        "curl -s http://127.0.0.1:8010/health\n"
        "curl -s http://127.0.0.1:8010/stats",
        ss["Codec"],
    ))
    story.append(Paragraph(
        "El LLM no decide veredicto. NLI: Supported / Contradicted / Unknown. "
        "Unknown es el valor por defecto cuando la evidencia no alcanza.",
        P,
    ))
    doc.build(story, onFirstPage=_obs_footer, onLaterPages=_obs_footer)


def main() -> None:
    DESKTOP.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    ai_path = DESKTOP / "Senales-escritura-IA.pdf"
    obs_path = DOCS / "The-NewsBreakers-observatorio.pdf"
    build_ai_pdf(ai_path)
    build_obs_pdf(obs_path)
    print(ai_path)
    print(obs_path)


if __name__ == "__main__":
    main()
