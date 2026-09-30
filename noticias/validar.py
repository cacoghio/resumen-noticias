"""Esquemas de la respuesta de Gemini y validación del resumen final.

Los links NUNCA vienen de Gemini: se toman de los clusters (fuentes reales).
"""
from typing import Literal

from pydantic import BaseModel, Field

from .config import MAX_ITEMS, MAX_POR_SECCION
from .modelos import Cluster

Seccion = Literal["claude_code", "anthropic", "competencia"]
ORDEN_SECCIONES = ["claude_code", "anthropic", "competencia"]
NOMBRE_SECCION = {
    "claude_code": "Claude Code",
    "anthropic": "Anthropic y Claude",
    "competencia": "Competencia",
}
ETIQUETA_TIPO = {"release": "📦 Release", "video": "▶ Video"}
PALABRAS_MIN, PALABRAS_MAX = 40, 400
AVISO_DIA_TRANQUILO = "Día tranquilo: hoy no hubo novedades importantes en tus temas."


class ErrorValidacion(Exception):
    pass


# --- Lo que devuelve Gemini ---
class Elegida(BaseModel):
    id: str = Field(description="id del cluster candidato, ej. c007")
    seccion: Seccion
    importancia: int = Field(ge=1, le=3, description="3 = no te lo puedes perder, 1 = menor")


class Seleccion(BaseModel):
    elegidas: list[Elegida]


class Analisis(BaseModel):
    id: str
    titular: str
    bajada: str
    que_paso: str
    por_que_importa: str
    que_probar: str = ""


class Redaccion(BaseModel):
    noticias: list[Analisis]


# --- Resumen final (lo que usan la página y el correo) ---
class Fuente(BaseModel):
    medio: str
    titulo: str
    link: str


class Item(BaseModel):
    id: str
    seccion: Seccion
    titular: str
    bajada: str
    que_paso: str
    por_que_importa: str
    que_probar: str = ""
    fuentes: list[Fuente]
    cobertura: int
    personas: list[str] = []
    etiquetas: list[str] = []
    importancia: int = 2


class Resumen(BaseModel):
    fecha: str
    modelo: str
    noticias: list[Item]
    aviso: str = ""

    def secciones(self) -> list[tuple[str, list[Item]]]:
        """[(nombre de sección, items)] solo de las secciones que tienen algo."""
        return [
            (NOMBRE_SECCION[s], [i for i in self.noticias if i.seccion == s])
            for s in ORDEN_SECCIONES
            if any(i.seccion == s for i in self.noticias)
        ]


def _palabras(a: Analisis) -> int:
    return len(" ".join([a.que_paso, a.por_que_importa, a.que_probar]).split())


def _fuentes(cluster: Cluster, maximo: int = 5) -> list[Fuente]:
    vistas, fuentes = set(), []
    for n in cluster.noticias:
        if n.medio in vistas:
            continue
        vistas.add(n.medio)
        fuentes.append(Fuente(medio=n.medio, titulo=n.titulo, link=n.link))
    return fuentes[:maximo]


def _etiquetas(cluster: Cluster) -> list[str]:
    etiquetas = [ETIQUETA_TIPO[t] for t in ("release", "video") if t in cluster.tipos]
    etiquetas += [f"🎙 {p}" for p in cluster.personas]
    return etiquetas


def armar_resumen(
    clusters: list[Cluster], elegidas: list[Elegida], analisis: list[Analisis],
    fecha: str, modelo: str,
) -> Resumen:
    por_id = {c.id: c for c in clusters}
    errores = []

    ids = [e.id for e in elegidas]
    if len(elegidas) > MAX_ITEMS:
        errores.append(f"se eligieron {len(elegidas)} noticias y el máximo es {MAX_ITEMS}")
    if len(set(ids)) != len(ids):
        errores.append("hay ids repetidos")
    for i in ids:
        if i not in por_id:
            errores.append(f"id inexistente: {i}")
    for seccion in ORDEN_SECCIONES:
        n = sum(e.seccion == seccion for e in elegidas)
        if n > MAX_POR_SECCION:
            errores.append(f"la sección {seccion} tiene {n} noticias (máximo {MAX_POR_SECCION})")

    textos = {a.id: a for a in analisis}
    items = []
    for e in elegidas:
        a = textos.get(e.id)
        if a is None:
            errores.append(f"falta el análisis de {e.id}")
            continue
        vacios = [k for k in ("titular", "bajada", "que_paso", "por_que_importa") if not getattr(a, k).strip()]
        if vacios:
            errores.append(f"{e.id}: campos vacíos {vacios}")
        n = _palabras(a)
        if not PALABRAS_MIN <= n <= PALABRAS_MAX:
            errores.append(f"{e.id}: {n} palabras (se esperan {PALABRAS_MIN}-{PALABRAS_MAX})")
        if len(a.titular) > 140:
            errores.append(f"{e.id}: titular de {len(a.titular)} caracteres")
        if e.id in por_id:
            c = por_id[e.id]
            items.append(Item(
                id=e.id, seccion=e.seccion, titular=a.titular.strip(), bajada=a.bajada.strip(),
                que_paso=a.que_paso.strip(), por_que_importa=a.por_que_importa.strip(),
                que_probar=a.que_probar.strip(), fuentes=_fuentes(c), cobertura=c.cobertura,
                personas=c.personas, etiquetas=_etiquetas(c), importancia=e.importancia,
            ))

    if errores:
        raise ErrorValidacion("; ".join(errores))

    items.sort(key=lambda i: (ORDEN_SECCIONES.index(i.seccion), -i.importancia))
    aviso = "" if items else AVISO_DIA_TRANQUILO
    return Resumen(fecha=fecha, modelo=modelo, noticias=items, aviso=aviso)
