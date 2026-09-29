"""Gemini: 1) elige 5 historias, 2) escribe el análisis. Con reintento y modelo de respaldo."""
import json
import time

from google import genai
from google.genai import types
from pydantic import ValidationError

from .config import MAX_CANDIDATOS, MODELO_PRINCIPAL, MODELO_RESPALDO, MODELOS_INTERMEDIOS, clave
from .modelos import Cluster
from .validar import ErrorValidacion, Redaccion, Resumen, Seleccion, armar_resumen

PROMPT_SELECCION = """Eres editor de un resumen diario de noticias para un lector chileno.

## Intereses del lector
{intereses}

## Titulares ya enviados en los últimos días (no repetir salvo desarrollo nuevo e importante)
{historial}

## Candidatos de las últimas 30 horas
Formato: id | cobertura (cuántos medios distintos la publican) | portada (sale en Google News) | medios | titular | resumen
{candidatos}

## Tarea
Elige exactamente 5 candidatos: 3 de ámbito "chile" y 2 de ámbito "mundo" (solo si no alcanza, 2 y 3).
- Descarta todo lo de la sección "Excluir siempre".
- Prioriza según el orden de intereses, la tendencia (cobertura alta y portada) y el impacto real.
- Una historia internacional con impacto directo en Chile puede ser "chile".
- Ordena las 5 de mayor a menor prioridad.
- tema: tecnologia_ia, internacional, economia, politica_chile, inmobiliario, musica_cultura, ciencia_medioambiente, deportes u otro.
Responde solo con el JSON pedido."""

PROMPT_ANALISIS = """Eres analista de noticias para un lector chileno. Escribe en español de Chile, neutral, claro y directo.

Para cada una de estas 5 historias (con los titulares y resúmenes de los medios que la cubren) escribe:
- titular: máximo 110 caracteres, informativo, sin clickbait.
- bajada: 1 frase (máx. 25 palabras) que explique la noticia; va en el correo.
- contexto: qué pasó y por qué importa hoy (100-120 palabras, 2 párrafos cortos).
- miradas: 2 o 3 posturas de actores distintos (gobierno, oposición, expertos, empresas, otros países), 20-30 palabras cada una. Describe posturas, no inventes citas textuales.
- que_mirar: próximos hitos, fechas o señales a seguir (35-50 palabras).
En total, unas 200 palabras por historia (contexto + miradas + que_mirar).
No inventes datos: si algo no está en las fuentes{busqueda}, no lo afirmes.
Usa el mismo id de cada historia.

## Intereses del lector (para el enfoque)
{intereses}

## Historias
{historias}

Responde solo con el JSON pedido."""


def _candidatos(clusters: list[Cluster]) -> str:
    lineas = []
    for c in clusters[:MAX_CANDIDATOS]:
        p = c.principal
        medios = ", ".join(sorted({n.medio for n in c.noticias}))[:120]
        resumen = p.resumen[:180]
        lineas.append(
            f"{c.id} | {c.cobertura} | {'sí' if c.portada else 'no'} | {medios} | {p.titulo} | {resumen}"
        )
    return "\n".join(lineas)


def _historias(clusters: list[Cluster]) -> str:
    bloques = []
    for c in clusters:
        notas = "\n".join(
            f"  - [{n.medio}] {n.titulo}" + (f": {n.resumen[:300]}" if n.resumen else "")
            for n in c.noticias[:8]
        )
        bloques.append(f"### {c.id}\n{notas}")
    return "\n\n".join(bloques)


def _generar(cliente, modelo: str, prompt: str, esquema, buscar: bool):
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=esquema,
        temperature=0.4,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    if buscar:
        config.tools = [types.Tool(google_search=types.GoogleSearch())]
    r = cliente.models.generate_content(model=modelo, contents=prompt, config=config)
    if r.parsed is not None:
        return r.parsed
    return esquema.model_validate(json.loads(r.text))


def _intento(cliente, modelo, clusters, intereses, historial, fecha, buscar) -> Resumen:
    seleccion = _generar(
        cliente, modelo,
        PROMPT_SELECCION.format(
            intereses=intereses,
            historial="\n".join(f"- {t}" for t in historial) or "(ninguno)",
            candidatos=_candidatos(clusters),
        ),
        Seleccion, buscar=False,
    )
    por_id = {c.id: c for c in clusters}
    elegidos = [por_id[e.id] for e in seleccion.elegidas if e.id in por_id]
    redaccion = _generar(
        cliente, modelo,
        PROMPT_ANALISIS.format(
            intereses=intereses,
            historias=_historias(elegidos),
            busqueda=" ni en la búsqueda de Google" if buscar else "",
        ),
        Redaccion, buscar=buscar,
    )
    return armar_resumen(clusters, seleccion.elegidas, redaccion.noticias, fecha=fecha, modelo=modelo)


# (modelo, usar búsqueda de Google, espera previa en segundos).
# Si el principal está saturado (503) se le da tiempo antes de pasar al respaldo.
INTENTOS = [
    (MODELO_PRINCIPAL, True, 0),
    (MODELO_PRINCIPAL, True, 30),
    *[(m, True, 5) for m in MODELOS_INTERMEDIOS],
    (MODELO_PRINCIPAL, False, 60),
    *[(m, False, 5) for m in MODELOS_INTERMEDIOS],
    (MODELO_RESPALDO, False, 5),
    (MODELO_RESPALDO, False, 60),
]


def generar_resumen(clusters, intereses: str, historial: list[str], fecha: str, log=print) -> Resumen:
    cliente = genai.Client(api_key=clave("GEMINI_API_KEY"))
    errores = []
    for i, (modelo, buscar, espera) in enumerate(INTENTOS):
        etiqueta = f"{modelo}{' + búsqueda' if buscar else ''}"
        if espera:
            log(f"  esperando {espera}s...")
            time.sleep(espera)
        try:
            log(f"Gemini: intento {i + 1} con {etiqueta}")
            resumen = _intento(cliente, modelo, clusters, intereses, historial, fecha, buscar)
            log(f"Gemini: OK con {etiqueta}")
            return resumen
        except (ErrorValidacion, ValidationError, json.JSONDecodeError) as e:
            errores.append(f"{etiqueta}: no pasó la validación ({str(e)[:300]})")
        except Exception as e:  # noqa: BLE001 - errores de API: cuota, modelo no disponible, etc.
            errores.append(f"{etiqueta}: {type(e).__name__}: {str(e)[:300]}")
        log(f"  falló -> {errores[-1]}")
    raise RuntimeError("Gemini falló en todos los intentos:\n" + "\n".join(errores))
