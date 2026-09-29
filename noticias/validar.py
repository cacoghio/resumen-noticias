"""Esquemas de la respuesta de Gemini y validación del resumen final.

Los links NUNCA vienen de Gemini: se toman de los clusters (feeds reales).
"""
from typing import Literal

from pydantic import BaseModel, Field

from .modelos import Cluster

TEMAS = Literal[
    "tecnologia_ia", "internacional", "economia", "politica_chile",
    "inmobiliario", "musica_cultura", "ciencia_medioambiente", "deportes", "otro",
]
NOMBRE_TEMA = {
    "tecnologia_ia": "Tecnología e IA", "internacional": "Internacional",
    "economia": "Economía", "politica_chile": "Política",
    "inmobiliario": "Inmobiliario", "musica_cultura": "Música y cultura",
    "ciencia_medioambiente": "Ciencia", "deportes": "Deportes", "otro": "Otro",
}
PALABRAS_MIN, PALABRAS_MAX = 120, 340
MAX_FUENTES = 5


class ErrorValidacion(Exception):
    pass


# --- Lo que devuelve Gemini ---
class Elegida(BaseModel):
    id: str = Field(description="id del cluster candidato, ej. c007")
    ambito: Literal["chile", "mundo"]
    tema: TEMAS


class Seleccion(BaseModel):
    elegidas: list[Elegida]


class Mirada(BaseModel):
    actor: str = Field(description="quién opina: gobierno, oposición, expertos, empresa, otro país...")
    postura: str


class Analisis(BaseModel):
    id: str
    titular: str
    bajada: str
    contexto: str
    miradas: list[Mirada]
    que_mirar: str


class Redaccion(BaseModel):
    noticias: list[Analisis]


# --- Resumen final (lo que usan la página y el correo) ---
class Fuente(BaseModel):
    medio: str
    titulo: str
    link: str


class Item(BaseModel):
    id: str
    ambito: Literal["chile", "mundo"]
    tema: str
    titular: str
    bajada: str
    contexto: str
    miradas: list[Mirada]
    que_mirar: str
    fuentes: list[Fuente]
    cobertura: int


class Resumen(BaseModel):
    fecha: str
    modelo: str
    noticias: list[Item]
    nota_mix: str = ""


def _palabras(a: Analisis) -> int:
    texto = " ".join([a.contexto, a.que_mirar, *(m.postura for m in a.miradas)])
    return len(texto.split())


def _fuentes(cluster: Cluster) -> list[Fuente]:
    vistas, fuentes = set(), []
    for n in sorted(cluster.noticias, key=lambda n: n.portada):  # medios directos primero
        if n.medio in vistas:
            continue
        vistas.add(n.medio)
        fuentes.append(Fuente(medio=n.medio, titulo=n.titulo, link=n.link))
    return fuentes[:MAX_FUENTES]


def armar_resumen(
    clusters: list[Cluster], elegidas: list[Elegida], analisis: list[Analisis],
    fecha: str, modelo: str,
) -> Resumen:
    por_id = {c.id: c for c in clusters}
    errores = []

    if len(elegidas) != 5 or len({e.id for e in elegidas}) != 5:
        errores.append(f"se esperaban 5 noticias distintas y llegaron {len(elegidas)}")
    for e in elegidas:
        if e.id not in por_id:
            errores.append(f"id inexistente: {e.id}")

    chile = sum(e.ambito == "chile" for e in elegidas)
    nota_mix = ""
    if chile == 2 and len(elegidas) == 5:
        nota_mix = "Hoy van 2 de Chile y 3 del mundo: no hubo una tercera noticia chilena a la altura."
    elif chile != 3 and len(elegidas) == 5:
        errores.append(f"mix inválido: {chile} Chile / {5 - chile} mundo (se espera 3/2 o 2/3)")

    textos = {a.id: a for a in analisis}
    items = []
    for e in elegidas:
        a = textos.get(e.id)
        if a is None:
            errores.append(f"falta el análisis de {e.id}")
            continue
        vacios = [k for k in ("titular", "bajada", "contexto", "que_mirar") if not getattr(a, k).strip()]
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
                id=e.id, ambito=e.ambito, tema=NOMBRE_TEMA.get(e.tema, e.tema),
                titular=a.titular.strip(), bajada=a.bajada.strip(), contexto=a.contexto.strip(),
                miradas=a.miradas, que_mirar=a.que_mirar.strip(),
                fuentes=_fuentes(c), cobertura=c.cobertura,
            ))

    if errores:
        raise ErrorValidacion("; ".join(errores))

    # Se mantiene el orden de Gemini: de mayor a menor prioridad
    return Resumen(fecha=fecha, modelo=modelo, noticias=items, nota_mix=nota_mix)
