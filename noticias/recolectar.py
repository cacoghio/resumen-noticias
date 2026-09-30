"""Lee las fuentes (RSS/Atom, páginas de listado HTML y el changelog de Claude Code).
Una fuente caída no detiene el resto."""
import calendar
import html
import re
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import certifi
import feedparser

from .config import FEEDS, PERSONAS, URL_RELEASE, VENTANA_HORAS, Feed
from .modelos import Noticia, sin_tildes

AGENTE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
LARGO_RESUMEN = 500
LARGO_CHANGELOG = 2500
MESES = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


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


def detectar_personas(texto: str) -> list[str]:
    plano = sin_tildes(texto)
    return [
        nombre for nombre, alias in PERSONAS.items()
        if any(re.search(rf"\b{re.escape(a)}\b", plano) for a in alias)
    ]


def _personas(feed: Feed, *textos: str) -> list[str]:
    personas = [feed.persona] if feed.persona else []
    for p in detectar_personas(" ".join(textos)):
        if p not in personas:
            personas.append(p)
    return personas


# --- RSS / Atom ---

RELACIONADA = re.compile(
    r'<a href="([^"]+)"[^>]*>(.*?)</a>(?:&nbsp;|\s)*<font[^>]*>(.*?)</font>', re.S
)


def _relacionadas(resumen_html: str, feed: Feed, fecha, grupo: str) -> list[Noticia]:
    """Google News lista en cada item las notas de otros medios sobre la misma historia."""
    notas = []
    for link, titulo, medio in RELACIONADA.findall(resumen_html or ""):
        titulo = _limpiar(titulo)
        notas.append(Noticia(
            medio=_limpiar(medio), seccion=feed.seccion, titulo=titulo, resumen="",
            link=html.unescape(link), fecha=fecha, tipo=feed.item,
            personas=_personas(feed, titulo), grupo=grupo,
        ))
    return notas


def parsear(feed: Feed, contenido: bytes, ahora: datetime) -> list[Noticia]:
    datos = feedparser.parse(contenido)
    limite = ahora - timedelta(hours=VENTANA_HORAS)
    notas = []
    for e in datos.entries[: max(feed.max_items * 3, 60)]:
        titulo = _limpiar(e.get("title", ""))
        link = e.get("link", "")
        if not titulo or not link:
            continue
        fecha = _fecha(e)
        if fecha and fecha < limite:
            continue
        medio = feed.nombre
        if feed.google:
            fuente = e.get("source", {}).get("title")
            if fuente:
                medio = fuente
                sufijo = f" - {fuente}"
                if titulo.endswith(sufijo):
                    titulo = titulo[: -len(sufijo)].strip()
            relacionadas = _relacionadas(e.get("summary", ""), feed, fecha, grupo=link)
            if relacionadas:
                notas.extend(relacionadas)
                continue
            resumen = ""  # Google News solo repite el título
        else:
            resumen = _limpiar(e.get("summary", "") or e.get("media_description", ""))
        notas.append(Noticia(
            medio=medio, seccion=feed.seccion, titulo=titulo, resumen=resumen[:LARGO_RESUMEN],
            link=link, fecha=fecha, tipo=feed.item,
            personas=_personas(feed, titulo, resumen),
        ))
        if len(notas) >= feed.max_items:
            break
    return notas


# --- Páginas de listado HTML (anthropic.com/news, claude.com/blog...) ---

ANCLA = r'<a\s[^>]*href="({prefijo}[a-z0-9][a-z0-9-]*)"[^>]*>(.*?)</a>'
FECHA_HTML = re.compile(r"\b([A-Z][a-z]{2}) (\d{1,2}), (\d{4})\b")


def _titulo_de_slug(slug: str) -> str:
    texto = slug.replace("-", " ")
    return texto[:1].upper() + texto[1:]


def parsear_html(feed: Feed, contenido: str, ahora: datetime) -> list[Noticia]:
    limite = ahora - timedelta(hours=VENTANA_HORAS)
    patron = re.compile(ANCLA.format(prefijo=re.escape(feed.prefijo)), re.S)
    por_ruta: dict[str, dict] = {}
    for ruta, interior in patron.findall(contenido):
        piezas = [p.strip() for p in re.split(r"\s*<[^>]+>\s*", interior) if p.strip()]
        datos = por_ruta.setdefault(ruta, {"fecha": None, "titulo": ""})
        for pieza in piezas:
            m = FECHA_HTML.fullmatch(pieza)
            if m and m.group(1).lower() in MESES:
                datos["fecha"] = datetime(int(m.group(3)), MESES[m.group(1).lower()], int(m.group(2)),
                                          12, tzinfo=timezone.utc)
            elif pieza.lower() not in ("read more", "leer más", "learn more") and len(pieza) > len(datos["titulo"]):
                datos["titulo"] = pieza
    notas = []
    for ruta, datos in por_ruta.items():
        if datos["fecha"] and datos["fecha"] < limite:
            continue
        titulo = _limpiar(datos["titulo"]) or _titulo_de_slug(ruta.rsplit("/", 1)[-1])
        # En anthropic.com/news la categoría va antes del título; se toma la pieza más larga
        notas.append(Noticia(
            medio=feed.nombre, seccion=feed.seccion, titulo=titulo, resumen="",
            link=feed.base + ruta, fecha=datos["fecha"], tipo=feed.item,
            personas=_personas(feed, titulo),
        ))
        if len(notas) >= feed.max_items:
            break
    return notas


META_DESCRIPCION = re.compile(
    r'<meta[^>]+(?:property="og:description"|name="description")[^>]+content="([^"]*)"', re.I
)


def descripcion_pagina(url: str) -> str:
    """Las páginas de listado no traen resumen: se lee la descripción de cada post."""
    try:
        texto = _descargar(url).decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001 - sin descripción igual sirve el título
        return ""
    m = META_DESCRIPCION.search(texto)
    return _limpiar(m.group(1))[:LARGO_RESUMEN] if m else ""


# --- Changelog de Claude Code ---

def _version(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def novedades_changelog(texto: str, ultima: str | None) -> tuple[str, list[tuple[str, list[str]]]]:
    """Devuelve (versión más nueva, [(versión, viñetas)] de las versiones posteriores a `ultima`).
    Sin `ultima` (primera vez) solo trae la última versión."""
    secciones: list[tuple[str, list[str]]] = []
    for bloque in re.split(r"^## ", texto, flags=re.M)[1:]:
        cabecera, _, cuerpo = bloque.partition("\n")
        version = cabecera.strip()
        if not re.fullmatch(r"\d+(?:\.\d+)+", version):
            continue
        viñetas = [ln[2:].strip() for ln in cuerpo.splitlines() if ln.startswith("- ")]
        secciones.append((version, viñetas))
    if not secciones:
        return ultima or "", []
    secciones.sort(key=lambda s: _version(s[0]), reverse=True)
    mas_nueva = secciones[0][0]
    if ultima is None:
        return mas_nueva, secciones[:1]
    return mas_nueva, [s for s in secciones if _version(s[0]) > _version(ultima)]


def parsear_changelog(feed: Feed, contenido: str, ahora: datetime, ultima: str | None) -> list[Noticia]:
    mas_nueva, nuevas = novedades_changelog(contenido, ultima)
    if not nuevas:
        return []
    versiones = [v for v, _ in nuevas]
    rango = mas_nueva if len(versiones) == 1 else f"{versiones[-1]} a {mas_nueva}"
    lineas = []
    for version, viñetas in nuevas:
        lineas.append(f"[{version}]")
        lineas.extend(f"- {v}" for v in viñetas)
    return [Noticia(
        medio=feed.nombre, seccion=feed.seccion, titulo=f"Claude Code {rango}",
        resumen="\n".join(lineas)[:LARGO_CHANGELOG], link=URL_RELEASE.format(version=mas_nueva),
        fecha=ahora, tipo="release", version=mas_nueva,
    )]


# --- Descarga y orquestación ---

# Certificados de certifi: el almacén de Windows/Python a veces trae uno vencido y falla con sitios sanos.
# La verificación SSL sigue activada.
_SSL = ssl.create_default_context(cafile=certifi.where())


def _descargar(url: str, intentos: int = 2) -> bytes:
    pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    for i in range(intentos):
        ultimo = i + 1 == intentos
        try:
            with urllib.request.urlopen(pedido, timeout=25, context=_SSL) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or ultimo:  # 429 = demasiadas peticiones (Reddit): esperar y reintentar
                raise
            time.sleep(10)
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if ultimo:
                raise
            time.sleep(2)
    raise RuntimeError("unreachable")


def recolectar(
    ahora: datetime | None = None, feeds: list[Feed] = FEEDS, version_vista: str | None = None,
) -> tuple[list[Noticia], list[Reporte]]:
    ahora = ahora or datetime.now(timezone.utc)

    def uno(feed: Feed) -> tuple[list[Noticia], Reporte]:
        reporte = Reporte(feed.nombre)
        try:
            contenido = _descargar(feed.url)
            if feed.tipo == "changelog":
                notas = parsear_changelog(feed, contenido.decode("utf-8", "ignore"), ahora, version_vista)
                reporte.leidas = reporte.recientes = len(notas)
                return notas, reporte
            if feed.tipo == "html":
                texto = contenido.decode("utf-8", "ignore")
                notas = parsear_html(feed, texto, ahora)
                anclas = re.findall(ANCLA.format(prefijo=re.escape(feed.prefijo)), texto, re.S)
                reporte.leidas = len({ruta for ruta, _ in anclas})
                reporte.recientes = len(notas)
                if reporte.leidas == 0:
                    reporte.error = "sin posts (¿cambió la página?)"
                return notas, reporte
            reporte.leidas = len(feedparser.parse(contenido).entries)
            notas = parsear(feed, contenido, ahora)
            reporte.recientes = len(notas)
            if reporte.leidas == 0:
                reporte.error = "feed vacío"
            return notas, reporte
        except Exception as e:  # noqa: BLE001 - una fuente caída no debe botar el resumen
            reporte.error = f"{type(e).__name__}: {e}"[:120]
            return [], reporte

    # Las fuentes del mismo sitio se piden en fila y con pausa (Reddit responde 429 si van juntas)
    por_sitio: dict[str, list[Feed]] = {}
    for f in feeds:
        por_sitio.setdefault(urlparse(f.url).netloc, []).append(f)

    def grupo(fs: list[Feed]) -> list[tuple[list[Noticia], Reporte]]:
        salida = []
        for i, f in enumerate(fs):
            if i:
                time.sleep(5)
            salida.append(uno(f))
        return salida

    with ThreadPoolExecutor(max_workers=8) as pool:
        por_grupo = dict(zip(por_sitio, pool.map(grupo, por_sitio.values())))
    # Se mantiene el orden original de FEEDS
    resultados = [por_grupo[urlparse(f.url).netloc][por_sitio[urlparse(f.url).netloc].index(f)] for f in feeds]

    noticias = [n for notas, _ in resultados for n in notas]
    # Los posts de listado no traen resumen: se completa con la descripción de cada página
    sin_resumen = [n for n in noticias if n.tipo in ("blog", "articulo") and not n.resumen and n.fecha is None][:15]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for nota, desc in zip(sin_resumen, pool.map(lambda n: descripcion_pagina(n.link), sin_resumen)):
            nota.resumen = desc
    return noticias, [r for _, r in resultados]
