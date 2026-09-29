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
VENTANA_HORAS = 30
DIAS_HISTORIAL = 3
MAX_CANDIDATOS = 150

MODELO_PRINCIPAL = "gemini-3.8-flash"
# Si el principal está saturado: estos también son gratis y aceptan búsqueda de Google
MODELOS_INTERMEDIOS = ["gemini-3.7-flash", "gemini-3.5-flash"]
MODELO_RESPALDO = "gemini-3.5-flash-lite"

# URL pública de GitHub Pages, ej: https://usuario.github.io/resumen-noticias
URL_PAGINAS = os.environ.get("URL_PAGINAS", "").rstrip("/")


@dataclass(frozen=True)
class Feed:
    nombre: str
    ambito: str  # chile | mundo | mixto
    url: str
    portada: bool = False


_GN = "https://news.google.com/rss/headlines/section/topic"
_GN_CL = "hl=es-419&gl=CL&ceid=CL:es-419"

FEEDS = [
    Feed("La Tercera", "chile", "https://www.latercera.com/arc/outboundfeeds/rss/?outputType=xml"),
    # Diario Financiero queda fuera: su certificado SSL está vencido (29-09-2026).
    # Reactivar cuando lo renueven: https://www.df.cl/noticias/site/list/port/rss.xml
    Feed("Cooperativa", "chile", "https://www.cooperativa.cl/noticias/site/tax/port/all/rss____1.xml"),
    Feed("CIPER", "chile", "https://www.ciperchile.cl/feed/"),
    Feed("Google News Chile", "mixto", "https://news.google.com/rss?hl=es-419&gl=CL&ceid=CL:es-419", portada=True),
    Feed("Google News Negocios", "mixto", f"{_GN}/BUSINESS?{_GN_CL}", portada=True),
    Feed("Google News Mundo", "mundo", f"{_GN}/WORLD?{_GN_CL}", portada=True),
    Feed("Google News Tecnología", "mundo", f"{_GN}/TECHNOLOGY?{_GN_CL}", portada=True),
    Feed("BBC Mundo", "mundo", "https://feeds.bbci.co.uk/mundo/rss.xml"),
    Feed("El País América", "mundo", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/america/portada"),
    Feed("Xataka", "mundo", "https://www.xataka.com/feedburner.xml"),
]


def clave(nombre: str) -> str:
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise SystemExit(f"Falta {nombre} en .env (local) o en los Secrets (GitHub).")
    return valor
