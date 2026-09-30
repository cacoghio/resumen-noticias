"""Gemini: 1) elige qué entra al Radar, 2) escribe el análisis. Con reintentos y modelos de respaldo."""
import json
import time

from google import genai
from google.genai import types
from pydantic import ValidationError

from .config import (
    MAX_CANDIDATOS, MAX_ITEMS, MAX_POR_SECCION, MODELO_PRINCIPAL, MODELO_RESPALDO,
    MODELOS_INTERMEDIOS, clave,
)
from .modelos import Cluster
from .validar import ErrorValidacion, Redaccion, Resumen, Seleccion, armar_resumen

PROMPT_SELECCION = """Eres el editor de "Radar IA", un resumen diario para una persona chilena que sigue de cerca la IA generativa, sobre todo Claude Code y Anthropic.

## Intereses del lector
{intereses}

## Ya enviado en los últimos días (no repetir salvo un desarrollo nuevo e importante)
{historial}

## Candidatos de las últimas 36 horas
Formato: id | pista de sección | tipo | cobertura (medios distintos que lo publican) | personas seguidas | medios | titular | resumen
{candidatos}

## Tarea
Elige entre 0 y {max_items} candidatos (máximo {max_seccion} por sección). No hay cuota: si hoy hay poco de valor, elige pocos; si no hay nada, devuelve la lista vacía.
Secciones: "claude_code" (Claude Code: releases, skills, plugins, MCP, hooks, trucos, workflows), "anthropic" (Anthropic y Claude: modelos, anuncios, ingeniería, empresa, políticas), "competencia" (OpenAI/ChatGPT, Google/Gemini, Cursor, Codex y otras herramientas de IA).
La "pista de sección" es solo una sugerencia: decide tú según el contenido.
Prioriza, de mayor a menor:
1. Releases y features de Claude Code (los de tipo "release" casi siempre entran).
2. Skills, plugins, MCP, hooks, subagentes y trucos concretos de Claude Code.
3. Lanzamientos, modelos y anuncios de Anthropic.
4. Lo que dicen o publican las personas seguidas, cuando aporta algo sobre IA (un video o post de ellos sobre el tema entra).
5. Lanzamientos importantes de la competencia.
6. Discusión de la comunidad, solo si es sustancial.
Descarta: rumores sin fuente, memes, reposts, listas tipo "10 prompts", notas de cursos o ventas, noticias que solo mencionan IA de pasada y noticias sin relación con IA generativa.
importancia: 3 = no te lo puedes perder, 2 = relevante, 1 = menor.
Responde solo con el JSON pedido."""

PROMPT_ANALISIS = """Eres analista de IA para un lector chileno con conocimiento técnico medio. Escribe en español de Chile, claro y directo; deja en inglés los nombres de productos y comandos.

Para cada historia (con los titulares y resúmenes de todas las fuentes que la cubren) escribe:
- titular: máximo 110 caracteres, informativo, sin clickbait y sin emojis.
- bajada: 1 frase (máx. 25 palabras) que explique la noticia; va en el correo.
- que_paso: qué ocurrió exactamente, con los datos concretos de las fuentes (60-130 palabras). En un release de Claude Code, resume lo más útil: features nuevas, comandos, settings y arreglos importantes.
- por_que_importa: por qué le sirve o le importa a quien usa Claude Code o sigue la IA (30-80 palabras).
- que_probar: solo para Claude Code, skills, plugins o trucos: qué puede probar hoy, con el comando o la configuración exacta si está en las fuentes (máx. 50 palabras). Déjalo vacío si no aplica.
Si la historia es de una persona (video, post, entrevista), di quién es, qué dijo o mostró y qué se lleva el lector. No inventes citas textuales.
No inventes datos: si algo no está en las fuentes{busqueda}, no lo afirmes. Usa el mismo id de cada historia.

## Intereses del lector (para el enfoque)
{intereses}

## Historias
{historias}

Responde solo con el JSON pedido."""


def _candidatos(clusters: list[Cluster]) -> str:
    lineas = []
    for c in clusters[:MAX_CANDIDATOS]:
        p = c.principal
        medios = ", ".join(sorted({n.medio for n in c.noticias}))[:100]
        pista = "/".join(sorted(c.secciones))
        tipos = "/".join(sorted(c.tipos))
        personas = ", ".join(c.personas) or "-"
        resumen = p.resumen[:160].replace("\n", " ")
        lineas.append(f"{c.id} | {pista} | {tipos} | {c.cobertura} | {personas} | {medios} | {p.titulo} | {resumen}")
    return "\n".join(lineas)


def _historias(clusters: list[Cluster]) -> str:
    bloques = []
    for c in clusters:
        notas = []
        for n in c.noticias[:8]:
            largo = 2500 if n.tipo == "release" else 500
            texto = n.resumen[:largo]
            notas.append(f"  - [{n.medio}] {n.titulo}" + (f": {texto}" if texto else ""))
        bloques.append(f"### {c.id}\n" + "\n".join(notas))
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
            max_items=MAX_ITEMS, max_seccion=MAX_POR_SECCION,
        ),
        Seleccion, buscar=False,
    )
    if not seleccion.elegidas:
        return armar_resumen(clusters, [], [], fecha=fecha, modelo=modelo)
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
# Si el principal está saturado (503) se le da tiempo antes de pasar a los otros.
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
