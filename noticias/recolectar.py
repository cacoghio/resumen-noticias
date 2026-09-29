"""Lee los feeds RSS. Un feed caído no detiene el resto."""
import calendar
import html
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import feedparser

from .config import FEEDS, VENTANA_HORAS, Feed
from .modelos import Noticia

AGENTE = "Mozilla/5.0 (resumen-noticias; +https://github.com)"
LARGO_RESUMEN = 400


@dataclass
class Reporte:
    medio: str
    leidas: int = 0
    recientes: int = 0
    error: str = ""


def _limpiar(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    texto = html.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


def _fecha(entrada) -> datetime | None:
    t = entrada.get("published_parsed") or entrada.get("updated_parsed")
    return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc) if t else None


RELACIONADA = re.compile(
    r'<a href="([^"]+)"[^>]*>(.*?)</a>(?:&nbsp;|\s)*<font[^>]*>(.*?)</font>', re.S
)


def _relacionadas(resumen_html: str, feed: Feed, fecha, grupo: str) -> list[Noticia]:
    """Google News lista en cada item las notas de otros medios sobre la misma historia."""
    notas = []
    for link, titulo, medio in RELACIONADA.findall(resumen_html or ""):
        notas.append(Noticia(
            medio=_limpiar(medio),
            ambito=feed.ambito,
            titulo=_limpiar(titulo),
            resumen="",
            link=html.unescape(link),
            fecha=fecha,
            portada=True,
            grupo=grupo,
        ))
    return notas


def parsear(feed: Feed, contenido: bytes, ahora: datetime) -> list[Noticia]:
    datos = feedparser.parse(contenido)
    limite = ahora - timedelta(hours=VENTANA_HORAS)
    notas = []
    for e in datos.entries:
        titulo = _limpiar(e.get("title", ""))
        link = e.get("link", "")
        if not titulo or not link:
            continue
        fecha = _fecha(e)
        if fecha and fecha < limite:
            continue
        medio = feed.nombre
        fuente = e.get("source", {}).get("title") if feed.portada else None
        if fuente:
            medio = fuente
            sufijo = f" - {fuente}"
            if titulo.endswith(sufijo):
                titulo = titulo[: -len(sufijo)].strip()
        if feed.portada:
            relacionadas = _relacionadas(e.get("summary", ""), feed, fecha, grupo=link)
            if relacionadas:
                notas.extend(relacionadas)
                continue
            resumen = ""  # Google News solo repite el título
        else:
            resumen = _limpiar(e.get("summary", ""))
        notas.append(Noticia(
            medio=medio,
            ambito=feed.ambito,
            titulo=titulo,
            resumen=resumen[:LARGO_RESUMEN],
            link=link,
            fecha=fecha,
            portada=feed.portada,
        ))
    return notas


def _descargar(feed: Feed) -> bytes:
    pedido = urllib.request.Request(feed.url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(pedido, timeout=25) as r:
        return r.read()


def recolectar(ahora: datetime | None = None, feeds: list[Feed] = FEEDS) -> tuple[list[Noticia], list[Reporte]]:
    ahora = ahora or datetime.now(timezone.utc)

    def uno(feed: Feed) -> tuple[list[Noticia], Reporte]:
        reporte = Reporte(feed.nombre)
        try:
            contenido = _descargar(feed)
            reporte.leidas = len(feedparser.parse(contenido).entries)
            notas = parsear(feed, contenido, ahora)
            reporte.recientes = len(notas)
            if reporte.leidas == 0:
                reporte.error = "feed vacío"
            return notas, reporte
        except Exception as e:  # noqa: BLE001 - un feed caído no debe botar el resumen
            reporte.error = f"{type(e).__name__}: {e}"[:120]
            return [], reporte

    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(uno, feeds))

    noticias = [n for notas, _ in resultados for n in notas]
    reportes = [r for _, r in resultados]
    return noticias, reportes
