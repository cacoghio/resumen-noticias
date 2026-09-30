"""Genera la página del día, el índice y el archivo de días anteriores en docs/."""
import json
from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import DOCS, PLANTILLAS, URL_PAGINAS
from .validar import Resumen

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

entorno = Environment(loader=FileSystemLoader(PLANTILLAS), autoescape=select_autoescape(["html", "j2"]))


def fecha_larga(fecha: str) -> str:
    d = date.fromisoformat(fecha)
    return f"{DIAS[d.weekday()].capitalize()} {d.day} de {MESES[d.month - 1]} de {d.year}"


def url_del_dia(fecha: str) -> str:
    base = URL_PAGINAS or DOCS.as_uri()
    return f"{base}/{fecha}.html"


def contexto(resumen: Resumen) -> dict:
    return {
        "fecha_larga": fecha_larga(resumen.fecha),
        "noticias": resumen.noticias,
        "secciones": resumen.secciones(),
        "aviso": resumen.aviso,
        "modelo": resumen.modelo,
        "url_pagina": url_del_dia(resumen.fecha),
        "url_archivo": "archivo.html",
    }


def _archivo() -> str:
    dias = sorted((p.stem for p in DOCS.glob("????-??-??.html")), reverse=True)
    items = "\n".join(f'<li><a href="{d}.html">{fecha_larga(d)}</a></li>' for d in dias)
    return (
        '<!doctype html><html lang="es-CL"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Archivo</title>'
        '<style>body{font-family:Georgia,serif;background:#f4efe6;color:#1c1a17;max-width:640px;'
        'margin:0 auto;padding:32px 16px;line-height:1.8}a{color:#c2361b}'
        '@media (prefers-color-scheme:dark){body{background:#16140f;color:#efe8da}a{color:#ff7a5c}}</style>'
        f'</head><body><h1>Días anteriores</h1><ul>{items}</ul></body></html>'
    )


def generar_pagina(resumen: Resumen) -> str:
    """Escribe docs/AAAA-MM-DD.html, docs/index.html, docs/archivo.html y el JSON. Devuelve la URL del día."""
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "datos").mkdir(exist_ok=True)
    (DOCS / ".nojekyll").touch()
    html = entorno.get_template("pagina.html.j2").render(**contexto(resumen))
    (DOCS / f"{resumen.fecha}.html").write_text(html, encoding="utf-8")
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    (DOCS / "archivo.html").write_text(_archivo(), encoding="utf-8")
    (DOCS / "datos" / f"{resumen.fecha}.json").write_text(
        json.dumps(resumen.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return url_del_dia(resumen.fecha)


def html_correo(resumen: Resumen) -> str:
    return entorno.get_template("correo.html.j2").render(**contexto(resumen))
