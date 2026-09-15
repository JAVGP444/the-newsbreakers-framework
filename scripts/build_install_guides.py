"""Build printable install guides: docs/install-es.pdf and docs/install-en.pdf."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer

INK = HexColor("#1a2332")
MUTED = HexColor("#4b5563")
LINE = HexColor("#d1d5db")
ACCENT = HexColor("#0f766e")
PANEL = HexColor("#f4f1ea")
NAVY = HexColor("#041428")

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LOGO = ROOT / "branding" / "logo.png"


def _font() -> str:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        p = Path(path)
        if p.is_file():
            pdfmetrics.registerFont(TTFont("Body", str(p)))
            bold = path.replace("Arial.ttf", "Arial Bold.ttf").replace("arial.ttf", "arialbd.ttf")
            bold = bold.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
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
    ss.add(ParagraphStyle("Bodyc", fontName=font, fontSize=10, leading=14, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6))
    ss.add(ParagraphStyle("Notec", fontName=font, fontSize=9, leading=12, textColor=MUTED, alignment=TA_LEFT, spaceAfter=8))
    ss.add(ParagraphStyle("Codec", fontName="Courier", fontSize=8, leading=11, textColor=INK, backColor=PANEL, leftIndent=4, rightIndent=4, spaceAfter=8))
    ss.add(ParagraphStyle("Bulletc", fontName=font, fontSize=10, leading=13, textColor=INK, leftIndent=12, spaceAfter=2))
    return ss


def _paint_bar(canvas, doc, right_label: str) -> None:
    canvas.saveState()
    bar_h = 16 * mm
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - bar_h, A4[0], bar_h, fill=1, stroke=0)
    text_x = 18 * mm
    if LOGO.is_file():
        canvas.drawImage(str(LOGO), 14 * mm, A4[1] - bar_h + 2.5 * mm, width=11 * mm, height=11 * mm, mask="auto")
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


def _build(path: Path, title: str, bar: str, blocks: list[tuple[str, str, str | None]]) -> None:
    font = _font()
    ss = _styles(font)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        title=title,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=24 * mm,
        bottomMargin=20 * mm,
    )
    story = []
    story.append(Paragraph(title, ss["H1c"]))
    for kind, text, extra in blocks:
        if kind == "h2":
            story.append(Paragraph(text, ss["H2c"]))
        elif kind == "p":
            story.append(Paragraph(text, ss["Bodyc"]))
        elif kind == "note":
            story.append(Paragraph(text, ss["Notec"]))
        elif kind == "code":
            story.append(Preformatted(text, ss["Codec"]))
        elif kind == "li":
            story.append(Paragraph("• " + text, ss["Bulletc"]))
        if extra:
            story.append(Spacer(1, 2 * mm))
    doc.build(story, onFirstPage=lambda c, d: _paint_bar(c, d, bar), onLaterPages=lambda c, d: _paint_bar(c, d, bar))


ES = [
    ("p", "Observatorio de salud animal (gusano barrenador, gripe aviar, peste porcina). Al abrir entra a la sala. No hay cuenta ni clave. En la cabecera hay un botón <b>ES | EN</b> para cambiar el idioma de la interfaz.", None),
    ("h2", "Qué necesitas", None),
    ("li", "<b>Windows:</b> Python 3.12 (marca PATH), Node.js LTS, Git. Inno Setup 6 es opcional para el instalador .exe.", None),
    ("li", "<b>macOS:</b> python3, node/npm (Homebrew si faltan). Para el .app: bash packaging/mac/make_dmg.sh.", None),
    ("li", "<b>Linux:</b> python3, node/npm. python packaging/build.py.", None),
    ("h2", "Windows (en el PC Windows)", None),
    ("p", "No construyas el .exe en el Mac.", None),
    ("code", "cd %USERPROFILE%\\Desktop\ngit clone https://github.com/JAVGP444/the-newsbreakers-framework.git\ncd the-newsbreakers-framework\npython -m venv .venv\n.venv\\Scripts\\activate\npython -m pip install -U pip\npython -m pip install -r requirements.txt pyinstaller pywebview\ncd frontend\nnpm install\nset VITE_API_URL=\nnpm run build\ncd ..\npython packaging/build.py", None),
    ("p", "Sale dist\\NewsBreakers\\NewsBreakers.exe. Datos en %APPDATA%\\TheNewsBreakers. Con Inno Setup: packaging\\windows\\setup.iss → NewsBreakers-Setup.exe.", None),
    ("h2", "macOS", None),
    ("code", "cd ~\ngit clone https://github.com/JAVGP444/the-newsbreakers-framework.git\ncd the-newsbreakers-framework\nbash packaging/mac/make_dmg.sh", None),
    ("p", "Arrastra NewsBreakers.app a Aplicaciones. Para desarrollo: mac/Instalar-y-abrir.command (clic derecho → Abrir la primera vez). Parar: mac/detener.command.", None),
    ("h2", "Linux y desarrollo", None),
    ("p", "Desarrollo: linux/abrir.sh o windows/abrir.bat. Parar: linux/detener.sh o windows/detener.bat. MySQL con Docker es opcional; SQLite abre el dashboard.", None),
    ("note", "Guías en el repo: README.md (español e inglés), mac/README.md, windows/README.md, linux/README.md.", None),
]

EN = [
    ("p", "Animal-health observatory (screwworm, avian flu, classical swine fever). The app opens to the watch room. There is no account or license key. Use the <b>ES | EN</b> button in the header to switch the interface language.", None),
    ("h2", "What you need", None),
    ("li", "<b>Windows:</b> Python 3.12 (tick PATH), Node.js LTS, Git. Inno Setup 6 is optional for the .exe installer.", None),
    ("li", "<b>macOS:</b> python3, node/npm (Homebrew if missing). For the .app: bash packaging/mac/make_dmg.sh.", None),
    ("li", "<b>Linux:</b> python3, node/npm. python packaging/build.py.", None),
    ("h2", "Windows (on the Windows PC)", None),
    ("p", "Do not build the .exe on a Mac.", None),
    ("code", "cd %USERPROFILE%\\Desktop\ngit clone https://github.com/JAVGP444/the-newsbreakers-framework.git\ncd the-newsbreakers-framework\npython -m venv .venv\n.venv\\Scripts\\activate\npython -m pip install -U pip\npython -m pip install -r requirements.txt pyinstaller pywebview\ncd frontend\nnpm install\nset VITE_API_URL=\nnpm run build\ncd ..\npython packaging/build.py", None),
    ("p", "Output is dist\\NewsBreakers\\NewsBreakers.exe. Data lives in %APPDATA%\\TheNewsBreakers. With Inno Setup: packaging\\windows\\setup.iss → NewsBreakers-Setup.exe.", None),
    ("h2", "macOS", None),
    ("code", "cd ~\ngit clone https://github.com/JAVGP444/the-newsbreakers-framework.git\ncd the-newsbreakers-framework\nbash packaging/mac/make_dmg.sh", None),
    ("p", "Drag NewsBreakers.app to Applications. For development: mac/Instalar-y-abrir.command (right-click → Open the first time). Stop: mac/detener.command.", None),
    ("h2", "Linux and development", None),
    ("p", "Development: linux/abrir.sh or windows/abrir.bat. Stop: linux/detener.sh or windows/detener.bat. MySQL via Docker is optional; SQLite opens the dashboard.", None),
    ("note", "Guides in the repo: README.md (Spanish and English), mac/README.md, windows/README.md, linux/README.md.", None),
]


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    es = DOCS / "install-es.pdf"
    en = DOCS / "install-en.pdf"
    _build(es, "The NewsBreakers — instalación", "instalación", ES)
    _build(en, "The NewsBreakers — installation", "installation", EN)
    print(es)
    print(en)


if __name__ == "__main__":
    main()
