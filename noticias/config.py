import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
PLANTILLAS = RAIZ / "plantillas"
INTERESES = RAIZ / "intereses.md"

load_dotenv(RAIZ / ".env")

ZONA = "America/Santiago"
VENTANA_HORAS = 36
DIAS_HISTORIAL = 3
DIAS_VISTOS = 14
MAX_CANDIDATOS = 120

# Si hay falta de novedades se envía igual un correo corto
MAX_ITEMS = 10
MAX_POR_SECCION = 5

MODELO_PRINCIPAL = "gemini-3.8-flash"
# Si el principal está saturado: estos también son gratis y aceptan búsqueda de Google
MODELOS_INTERMEDIOS = ["gemini-3.7-flash", "gemini-3.5-flash"]
MODELO_RESPALDO = "gemini-3.5-flash-lite"

# URL pública de GitHub Pages, ej: https://usuario.github.io/resumen-noticias
URL_PAGINAS = os.environ.get("URL_PAGINAS", "").rstrip("/")

# Personas a seguir: nombre que se muestra -> cómo pueden aparecer escritas (sin tildes, minúsculas)
PERSONAS = {
    "Benjamín Cordero": ["benjamin cordero", "bencord"],
    "Dario Amodei": ["dario amodei"],
    "Boris Cherny": ["boris cherny"],
    "Sam Altman": ["sam altman"],
    "Simon Willison": ["simon willison"],
}


@dataclass(frozen=True)
class Feed:
    nombre: str
    seccion: str  # pista para Gemini: claude_code | anthropic | competencia | voces
    url: str
    tipo: str = "rss"  # rss | html | changelog
    google: bool = False  # Google News: cada item trae la lista de medios que cubren la historia
    item: str = "articulo"  # articulo | video | comunidad | blog
    persona: str = ""  # si todo lo de esta fuente es de una persona
    prefijo: str = ""  # html: prefijo de ruta de los posts, ej. /news/
    base: str = ""  # html: dominio, ej. https://www.anthropic.com
    max_items: int = 40


URL_CHANGELOG = "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"
URL_RELEASE = "https://github.com/anthropics/claude-code/releases/tag/v{version}"

_GN = "https://news.google.com/rss/search"
_EN = "hl=en-US&gl=US&ceid=US:en"
_ES = "hl=es-419&gl=CL&ceid=CL:es-419"
_YT = "https://www.youtube.com/feeds/videos.xml?channel_id="

FEEDS = [
    # --- Claude Code ---
    Feed("Claude Code", "claude_code", URL_CHANGELOG, tipo="changelog"),
    Feed("r/ClaudeCode", "claude_code", "https://www.reddit.com/r/ClaudeCode/top/.rss?t=day", item="comunidad", max_items=15),
    # --- Anthropic y Claude ---
    Feed("Anthropic News", "anthropic", "https://www.anthropic.com/news", tipo="html", prefijo="/news/", base="https://www.anthropic.com", max_items=10),
    Feed("Anthropic Engineering", "anthropic", "https://www.anthropic.com/engineering", tipo="html", prefijo="/engineering/", base="https://www.anthropic.com", item="blog", max_items=8),
    Feed("Claude Blog", "anthropic", "https://claude.com/blog", tipo="html", prefijo="/blog/", base="https://claude.com", item="blog", max_items=8),
    Feed("YouTube Anthropic", "anthropic", _YT + "UCrDwWp7EBBv4NwvScIpBDOA", item="video"),
    Feed("r/ClaudeAI", "anthropic", "https://www.reddit.com/r/ClaudeAI/top/.rss?t=day", item="comunidad", max_items=15),
    Feed("Hacker News", "anthropic", "https://hnrss.org/newest?q=Claude+OR+Anthropic+OR+%22Claude+Code%22&points=50", item="comunidad", max_items=15),
    Feed("Google News Anthropic", "anthropic", f"{_GN}?q=Anthropic+OR+%22Claude+Code%22+OR+%22Claude+AI%22+when:1d&{_EN}", google=True, max_items=25),
    Feed("Google News Claude (es)", "anthropic", f"{_GN}?q=Claude+Anthropic+IA+when:1d&{_ES}", google=True, max_items=15),
    # --- Voces ---
    Feed("YouTube Benjamín Cordero", "voces", _YT + "UCpq8lHHliCS3oBt-gfL0bKQ", item="video", persona="Benjamín Cordero"),
    Feed("Simon Willison", "voces", "https://simonwillison.net/atom/everything/", item="blog", persona="Simon Willison", max_items=15),
    Feed("Google News Voces", "voces", f"{_GN}?q=%22Dario+Amodei%22+OR+%22Boris+Cherny%22+OR+%22Sam+Altman%22+when:2d&{_EN}", google=True, max_items=25),
    # --- Competencia ---
    Feed("OpenAI", "competencia", "https://openai.com/news/rss.xml", max_items=15),
    Feed("Google AI", "competencia", "https://blog.google/technology/ai/rss/", max_items=10),
    Feed("Google DeepMind", "competencia", "https://deepmind.google/blog/rss.xml", max_items=10),
    Feed("Google News Competencia", "competencia", f"{_GN}?q=ChatGPT+OR+OpenAI+OR+Gemini+OR+Cursor+OR+Codex+when:1d&{_EN}", google=True, max_items=25),
    Feed("Xataka IA", "competencia", "https://www.xataka.com/tag/inteligencia-artificial/rss2.xml", max_items=10),
]


def clave(nombre: str) -> str:
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise SystemExit(f"Falta {nombre} en .env (local) o en los Secrets (GitHub).")
    return valor
