"""Decide si toca enviar (hora de Chile + no enviado hoy) y guarda estado e historial."""
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import DIAS_HISTORIAL, DIAS_VISTOS, DOCS, ZONA

DESDE, HASTA = time(8, 0), time(11, 0)
ESTADO = DOCS / "estado.json"
HISTORIAL = DOCS / "historial.json"


def fecha_chile(ahora: datetime) -> str:
    return ahora.astimezone(ZoneInfo(ZONA)).date().isoformat()


def debe_correr(ahora: datetime, ultimo_envio: str | None) -> tuple[bool, str]:
    local = ahora.astimezone(ZoneInfo(ZONA))
    hoy = local.date().isoformat()
    if ultimo_envio == hoy:
        return False, f"ya se envió hoy ({hoy})"
    if not DESDE <= local.time() < HASTA:
        return False, f"fuera de horario: en Chile son las {local:%H:%M}"
    return True, f"toca enviar: en Chile son las {local:%H:%M}"


def _leer(ruta: Path, defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return defecto


def _escribir(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def ultimo_envio() -> str | None:
    return _leer(ESTADO, {}).get("ultimo_envio")


def marcar_enviado(fecha: str, url: str) -> None:
    _escribir(ESTADO, {"ultimo_envio": fecha, "pagina": url})


VISTOS = DOCS / "vistos.json"


def leer_vistos() -> dict:
    vistos = _leer(VISTOS, {})
    return {"links": vistos.get("links", {}), "changelog": vistos.get("changelog", "")}


def filtrar_vistos(noticias: list, vistos: dict) -> list:
    """Saca lo ya enviado. La primera vez (sin historial) también descarta los posts sin fecha,
    porque no se sabe si son de hoy; quedan marcados como vistos para mañana."""
    primera_vez = not vistos["links"]
    return [
        n for n in noticias
        if n.link not in vistos["links"] and not (primera_vez and n.fecha is None and n.tipo != "release")
    ]


def actualizar_vistos(vistos: dict, fecha: str, links: list[str], version: str, dias: int = DIAS_VISTOS) -> dict:
    limite = (date.fromisoformat(fecha) - timedelta(days=dias)).isoformat()
    links_nuevos = {l: f for l, f in vistos["links"].items() if f >= limite}
    links_nuevos.update({l: fecha for l in links})
    return {"links": links_nuevos, "changelog": version or vistos["changelog"]}


def guardar_vistos(fecha: str, links: list[str], version: str) -> None:
    _escribir(VISTOS, actualizar_vistos(leer_vistos(), fecha, links, version))


def leer_historial() -> list[dict]:
    return _leer(HISTORIAL, [])


def actualizar_historial(historial: list[dict], fecha: str, titulares: list[str], dias: int = DIAS_HISTORIAL) -> list[dict]:
    limite = (date.fromisoformat(fecha) - timedelta(days=dias - 1)).isoformat()
    previo = [h for h in historial if limite <= h["fecha"] < fecha]
    return previo + [{"fecha": fecha, "titular": t} for t in titulares]


def guardar_historial(fecha: str, titulares: list[str]) -> None:
    _escribir(HISTORIAL, actualizar_historial(leer_historial(), fecha, titulares))
