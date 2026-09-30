"""Genera los 3 prototipos de diseño con el mismo día real (30-09-2026).

Uso: .venv\\Scripts\\python.exe diseno\\prototipos\\generar.py
Salida: diseno/prototipos/{a-carta,b-consola,c-boletin}.html
"""
import json
import math
import re
import ssl
import urllib.request
from pathlib import Path

import certifi
from jinja2 import Environment, FileSystemLoader, select_autoescape

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos-ejemplo.json"
CACHE_CHANGELOG = AQUI / "changelog-2.1.285.txt"

NOMBRE_SECCION = {"claude_code": "Claude Code", "anthropic": "Anthropic y Claude", "competencia": "Competencia"}
CODIGO_SECCION = {"claude_code": "CC", "anthropic": "AN", "competencia": "CP"}
ORDEN = ["claude_code", "anthropic", "competencia"]
# Rumbo central de cada sector del radar (grados desde el norte, sentido horario)
RUMBO = {"claude_code": 0, "anthropic": 120, "competencia": 240}
DISTANCIA = {3: 0.30, 2: 0.56, 1: 0.80}  # más cerca del centro = más importante

# "En 30 segundos": en producción lo escribirá Gemini (campo resumen_dia)
RESUMEN_DIA = [
    {"lead": "Claude Code 2.1.285", "resto": "suma claude --desktop, un interruptor para apagar WebFetch y opciones de plugins configurables."},
    {"lead": "Anthropic avisa \"riesgo existencial\"", "resto": "en su prospecto de salida a bolsa, y Dario Amodei llevó el mismo mensaje a la Casa Blanca."},
    {"lead": "OpenAI lanza Dots y GPT-6.1 Sol", "resto": "en su DevDay, pero frena GPT-6.1 Astra por problemas de seguridad."},
]


def changelog_2_1_285() -> list[str]:
    if not CACHE_CHANGELOG.exists():
        ctx = ssl.create_default_context(cafile=certifi.where())
        url = "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"
        texto = urllib.request.urlopen(url, context=ctx, timeout=30).read().decode()
        bloque = texto.split("## 2.1.285", 1)[1].split("\n## ", 1)[0]
        CACHE_CHANGELOG.write_text(bloque, encoding="utf-8")
    bloque = CACHE_CHANGELOG.read_text(encoding="utf-8")
    return [ln[2:].strip() for ln in bloque.splitlines() if ln.startswith("- ")]


TIPOS_CAMBIO = [("Added", "nuevo", "Nuevo"), ("Improved", "mejora", "Mejorado"),
                ("Changed", "cambio", "Cambiado"), ("Fixed", "arreglo", "Arreglado")]


def clasificar(vinetas: list[str]) -> dict:
    conteo = {clave: 0 for _, clave, _ in TIPOS_CAMBIO}
    nuevos = []
    for v in vinetas:
        limpio = re.sub(r"^(\[[^\]]+\]\s*|Windows:\s*|WSL:\s*|macOS:\s*)", "", v)
        for prefijo, clave, _ in TIPOS_CAMBIO:
            if limpio.startswith(prefijo):
                conteo[clave] += 1
                if clave == "nuevo" and not v.startswith("["):
                    nuevos.append(limpio[len(prefijo):].strip())
                break
    total = len(vinetas)
    barras = [{"clave": c, "nombre": n, "n": conteo[c], "pct": round(100 * conteo[c] / total, 1)}
              for _, c, n in TIPOS_CAMBIO if conteo[c]]
    return {"total": total, "barras": barras, "destacados": nuevos[:6]}


def codigo_html(texto: str) -> str:
    """`algo` -> <code>algo</code> (el texto ya viene escapado por Jinja en la plantilla)."""
    from markupsafe import escape, Markup
    partes = re.split(r"`([^`]+)`", str(texto))
    salida = [escape(p) if i % 2 == 0 else Markup(f"<code>{escape(p)}</code>") for i, p in enumerate(partes)]
    return Markup("").join(salida)


def radar(items: list[dict], tam: int = 320) -> dict:
    c = tam / 2
    r_max = tam / 2 - 18
    puntos = []
    for seccion in ORDEN:
        grupo = [i for i in items if i["seccion"] == seccion]
        for k, it in enumerate(grupo):
            ancho = 100  # grados útiles del sector de 120
            ang = RUMBO[seccion] - ancho / 2 + ancho * (k + 1) / (len(grupo) + 1)
            dist = DISTANCIA[it["importancia"]] + (0.07 if k % 2 else 0)
            rad = math.radians(ang)
            puntos.append({
                "id": it["id"], "n": it["n"], "seccion": seccion,
                "x": round(c + r_max * dist * math.sin(rad), 1),
                "y": round(c - r_max * dist * math.cos(rad), 1),
                # La importancia manda en el tamaño; la cobertura suma poco
                "r": round(3.5 + it["importancia"] * 2 + min(it["cobertura"], 10) * 0.2, 1),
                "rumbo": round(ang % 360), "imp": it["importancia"],
                "titular": it["titular"],
            })
    anillos = [round(r_max * d, 1) for d in (0.30, 0.56, 0.80, 1.0)]
    ticks = []
    for g in range(0, 360, 10):
        rad = math.radians(g)
        largo = 10 if g % 30 == 0 else 5
        ticks.append({
            "x1": round(c + r_max * math.sin(rad), 1), "y1": round(c - r_max * math.cos(rad), 1),
            "x2": round(c + (r_max - largo) * math.sin(rad), 1), "y2": round(c - (r_max - largo) * math.cos(rad), 1),
            "g": g, "tx": round(c + (r_max + 11) * math.sin(rad), 1), "ty": round(c - (r_max + 11) * math.cos(rad) + 3, 1),
        })
    divisiones = []
    for g in (60, 180, 300):
        rad = math.radians(g)
        divisiones.append({"x": round(c + r_max * math.sin(rad), 1), "y": round(c - r_max * math.cos(rad), 1)})
    etiquetas = []
    for s in ORDEN:
        rad = math.radians(RUMBO[s])
        etiquetas.append({"seccion": s, "codigo": CODIGO_SECCION[s], "nombre": NOMBRE_SECCION[s],
                          "x": round(c + r_max * 0.9 * math.sin(rad), 1), "y": round(c - r_max * 0.9 * math.cos(rad) + 3, 1)})
    gajos = []
    for s in ORDEN:
        a0, a1 = math.radians(RUMBO[s] - 60), math.radians(RUMBO[s] + 60)
        gajos.append({"seccion": s, "d": (
            f"M{c} {c} L{c + r_max * math.sin(a0):.1f} {c - r_max * math.cos(a0):.1f} "
            f"A{r_max} {r_max} 0 0 1 {c + r_max * math.sin(a1):.1f} {c - r_max * math.cos(a1):.1f} Z")})
    return {"tam": tam, "c": c, "r": r_max, "anillos": anillos, "puntos": puntos, "ticks": ticks,
            "divisiones": divisiones, "etiquetas": etiquetas, "gajos": gajos}


def contexto() -> dict:
    d = json.loads(DATOS.read_text(encoding="utf-8-sig"))
    items = d["noticias"]
    for n, it in enumerate(items, start=1):
        it["n"] = n
        it["titular"] = it["titular"].replace("🎙 ", "").strip()
        it["codigo"] = f"{CODIGO_SECCION[it['seccion']]}-{n:02d}"
        it["es_release"] = "📦 Release" in it["etiquetas"]
        it["es_video"] = "▶ Video" in it["etiquetas"]
        it["palabras"] = len(" ".join([it["que_paso"], it["por_que_importa"], it["que_probar"]]).split())
        if it["es_release"]:
            it["fuentes"].sort(key=lambda f: f["medio"] != "Claude Code")
            it["version"] = "2.1.285"
            it["cambios"] = clasificar(changelog_2_1_285())
        # Separar comando(s) copiables de "qué probar"
        it["comandos"] = re.findall(r"(export [A-Z_]+=\S+|claude --[a-z-]+)", it["que_probar"])
    total_palabras = sum(it["palabras"] + len(it["titular"].split()) + len(it["bajada"].split()) for it in items)
    secciones = [{"clave": s, "nombre": NOMBRE_SECCION[s], "codigo": CODIGO_SECCION[s],
                  "notas": [i for i in items if i["seccion"] == s]} for s in ORDEN]
    return {
        "fecha": d["fecha"], "fecha_larga": "Miércoles 30 de septiembre de 2026", "fecha_corta": "30 SEP 2026",
        "hora": "08:21", "hora_utc": "11:21", "edicion": 1, "modelo": d["modelo"],
        "items": items, "secciones": [s for s in secciones if s["notas"]],
        "total": len(items), "minutos": max(1, round(total_palabras / 220)),
        "resumen_dia": RESUMEN_DIA, "radar": radar(items),
        "fuentes_revisadas": 18, "fuentes_caidas": ["r/ClaudeAI"],
        "personas": sorted({p for i in items for p in i["personas"]}),
    }


def main():
    env = Environment(loader=FileSystemLoader(AQUI / "plantillas"), autoescape=select_autoescape(["html", "j2"]))
    env.filters["codigo"] = codigo_html
    ctx = contexto()
    for nombre in ("a-carta", "b-consola", "c-boletin"):
        plantilla = AQUI / "plantillas" / f"{nombre}.html.j2"
        if not plantilla.exists():
            continue
        html = env.get_template(f"{nombre}.html.j2").render(**ctx)
        (AQUI / f"{nombre}.html").write_text(html, encoding="utf-8")
        # Copia para revisar en local: el Artifact agrega esta cabecera al publicar
        vista = AQUI / "vista"
        vista.mkdir(exist_ok=True)
        (vista / f"{nombre}.html").write_text(
            '<!doctype html><html lang="es-CL"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            f'</head><body style="margin:0">{html}</body></html>', encoding="utf-8")
        print(f"{nombre}.html  {len(html.encode()) // 1024} KB")


if __name__ == "__main__":
    main()
