"""Prototipo D ("Hoy"): Boletín minimalista con tarjetas que se abren, imágenes y extras.

Uso: .venv\\Scripts\\python.exe diseno\\prototipos\\generar_hoy.py
Salida: docs/prototipo/index.html (se ve en GitHub Pages: /resumen-noticias/prototipo/)
"""
import hashlib
import math
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

import generar  # mismo directorio: reutiliza datos, changelog y utilidades

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI.parent.parent / "docs" / "prototipo" / "index.html"

CATEGORIAS = [
    {"clave": "claude_code", "nombre": "Claude Code", "color": "cc"},
    {"clave": "modelos", "nombre": "Modelos", "color": "mod"},
    {"clave": "agentes", "nombre": "Agentes y apps", "color": "age"},
    {"clave": "industria", "nombre": "Industria", "color": "ind"},
    {"clave": "seguridad", "nombre": "Seguridad y reglas", "color": "seg"},
]

# En producción esto lo deciden Gemini (categoría) y el recolector (imagen desde feeds directos)
EXTRA = {
    "c001": {"categoria": "claude_code", "empresa": "Anthropic", "imagen": {"tipo": "poster"}},
    "c004": {"categoria": "agentes", "empresa": "OpenAI", "imagen": {
        "tipo": "foto", "url": "https://media.wired.com/photos/6abbcee9422fade848ea964d/master/pass/Dots%20Hero%20Image.png",
        "credito": "Wired"},
        "fuente_directa": {"medio": "Wired", "titulo": "OpenAI's Dots Are Always-On AI Agents", "link": "https://www.wired.com/story/openai-dots-always-on-ai-agents-that-proactively-help/"}},
    "c008": {"categoria": "modelos", "empresa": "OpenAI", "imagen": {
        "tipo": "foto", "url": "https://cdn.arstechnica.net/wp-content/uploads/2026/09/GettyImages-1822585391-1152x648.jpg",
        "credito": "Ars Technica / Getty"},
        "fuente_directa": {"medio": "Ars Technica", "titulo": "OpenAI says planned GPT-6.1 is too insecure to release", "link": "https://arstechnica.com/ai/2026/09/openai-says-planned-gpt-6-1-is-too-insecure-to-release/"}},
    "c003": {"categoria": "industria", "empresa": "Anthropic", "imagen": {
        "tipo": "foto", "url": "https://cdn.arstechnica.net/wp-content/uploads/2026/09/claudebyanthropic-1024x648.jpg",
        "credito": "Ars Technica"},
        "fuente_directa": {"medio": "Ars Technica", "titulo": "Anthropic's IPO pitch includes a warning about human extinction", "link": "https://arstechnica.com/ai/2026/09/anthropics-ipo-pitch-includes-a-warning-about-human-extinction/"}},
    "c009": {"categoria": "seguridad", "empresa": "Anthropic", "imagen": {"tipo": "retrato", "iniciales": "DA", "nombre": "Dario Amodei"}},
    "c013": {"categoria": "seguridad", "empresa": "Anthropic", "imagen": {"tipo": "arte", "palabra": "Red team"}},
    "c104": {"categoria": "agentes", "empresa": "OpenAI", "imagen": {
        "tipo": "foto", "url": "https://i.ytimg.com/vi/2v-_ustjm6k/maxresdefault.jpg", "credito": "YouTube · Benjamín Cordero"}},
}

COMPARATIVA = {
    "fuentes": [("anthropic.com", "https://www.anthropic.com/"), ("Ars Technica", "https://arstechnica.com/ai/2026/09/openai-says-planned-gpt-6-1-is-too-insecure-to-release/")],
    "filas": [
        {"modelo": "Claude Sonnet 5.5", "lab": "Anthropic", "fecha": "28 sep", "promesa": "30% más rápido y hasta 30% más barato que Sonnet 5", "estado": "Disponible", "ok": True},
        {"modelo": "Claude Opus 5.5", "lab": "Anthropic", "fecha": "22 sep", "promesa": "Rinde como Fable 5.1 en la mayoría del trabajo y cuesta 40% menos que Opus 5", "estado": "Disponible", "ok": True},
        {"modelo": "GPT-6.1 Sol", "lab": "OpenAI", "fecha": "29 sep", "promesa": "Inteligencia cercana a Astra a un quinto del precio", "estado": "Disponible", "ok": True},
        {"modelo": "GPT-6.1 Astra", "lab": "OpenAI", "fecha": "—", "promesa": "El modelo más potente de OpenAI", "estado": "En pausa por seguridad", "ok": False},
    ],
}

AGENDA = [
    {"dia": "28", "mes": "OCT", "hasta": "29 oct", "nombre": "GitHub Universe", "lugar": "San Francisco + online gratis", "tema": "Agentes, open source y herramientas para developers",
     "link": "https://github.blog/news-insights/company-news/your-guide-to-github-universe-2026-is-here-the-schedule-just-launched/"},
    {"dia": "17", "mes": "NOV", "hasta": "20 nov", "nombre": "Microsoft Ignite", "lugar": "San Francisco + digital", "tema": "Copilot, Azure AI y agentes empresariales",
     "link": "https://moscone.com/events/microsoft-ignite-2026"},
    {"dia": "30", "mes": "NOV", "hasta": "4 dic", "nombre": "AWS re:Invent", "lugar": "Las Vegas + stream gratis", "tema": "IA agéntica, modelos y nube", "link": ""},
]

FRASE = {
    "texto": "Very real risks.", "traduccion": "«Riesgos muy reales».",
    "persona": "Dario Amodei", "rol": "CEO de Anthropic, tras su reunión en la Casa Blanca",
    "fuente": "Firstpost", "id": "c009",
}


def _semilla(texto: str) -> int:
    return int(hashlib.sha1(texto.encode()).hexdigest()[:8], 16)


def arte(id_: str, color: str) -> dict:
    """Parámetros deterministas para la ilustración de respaldo (manchas de color + anillos de radar)."""
    s = _semilla(id_)
    manchas = []
    for k in range(3):
        v = (s >> (k * 7)) & 0x7F
        manchas.append({"x": 20 + (v % 60), "y": 15 + ((v * 3) % 70), "r": 38 + (v % 30), "o": [0.95, 0.7, 0.5][k]})
    ang = (s % 360)
    return {"manchas": manchas, "color": color, "barrido": ang,
            "bx": round(50 + 46 * math.sin(math.radians(ang)), 1), "by": round(50 - 46 * math.cos(math.radians(ang)), 1)}


def contexto_hoy() -> dict:
    base = generar.contexto()
    colores = {c["clave"]: c["color"] for c in CATEGORIAS}
    nombres = {c["clave"]: c["nombre"] for c in CATEGORIAS}
    items = []
    for it in base["items"]:
        extra = EXTRA[it["id"]]
        it = dict(it)
        it["categoria"] = extra["categoria"]
        it["categoria_nombre"] = nombres[extra["categoria"]]
        it["color"] = colores[extra["categoria"]]
        it["empresa"] = extra["empresa"]
        it["imagen"] = extra["imagen"]
        it["arte"] = arte(it["id"], colores[extra["categoria"]])
        if "fuente_directa" in extra:
            it["fuentes"] = [extra["fuente_directa"]] + it["fuentes"]
            it["cobertura"] += 1
        it["lectura"] = max(1, round(it["palabras"] / 200))
        items.append(it)
    orden = [c["clave"] for c in CATEGORIAS]
    items.sort(key=lambda i: (orden.index(i["categoria"]), -i["importancia"]))
    # Portada: la más importante con foto real
    portada = sorted(items, key=lambda i: (-i["importancia"], i["imagen"]["tipo"] != "foto"))[0]
    release = next(i for i in items if i["es_release"])
    categorias = [dict(c, n=sum(1 for i in items if i["categoria"] == c["clave"])) for c in CATEGORIAS]
    return {
        **base, "items": items, "portada": portada, "release": release, "categorias": categorias,
        "comparativa": COMPARATIVA, "agenda": AGENDA, "frase": FRASE,
        "numero": {"valor": release["cambios"]["total"], "texto": f"cambios en Claude Code {release['version']}"},
    }


def main():
    env = Environment(loader=FileSystemLoader(AQUI / "plantillas"), autoescape=select_autoescape(["html", "j2"]))
    env.filters["codigo"] = generar.codigo_html
    html = env.get_template("d-hoy.html.j2").render(**contexto_hoy())
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(html, encoding="utf-8")
    print(f"{SALIDA}  {len(html.encode()) // 1024} KB")


if __name__ == "__main__":
    main()
