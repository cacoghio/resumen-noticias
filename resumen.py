"""Radar IA: resumen diario sobre IA generativa, Claude Code y Anthropic.

Uso:
  python resumen.py --solo-recoleccion   recolecta y deduplica, no llama a Gemini
  python resumen.py --sin-correo         todo menos el correo
  python resumen.py --forzar             se salta el chequeo de horario / ya enviado
"""
import argparse
import sys
from datetime import datetime, timezone

from noticias import horario
from noticias.config import INTERESES
from noticias.deduplicar import agrupar
from noticias.recolectar import recolectar


def mostrar_recoleccion(reportes, noticias, clusters, cuantos=25):
    print("== Fuentes ==")
    for r in reportes:
        estado = f"ERROR {r.error}" if r.error else "ok"
        print(f"  {r.medio:<26} leídas={r.leidas:<4} recientes={r.recientes:<4} {estado}")
    print(f"\nNotas: {len(noticias)}  ->  historias únicas: {len(clusters)}")
    print(f"\n== Top {cuantos} (releases y voces primero) ==")
    for c in clusters[:cuantos]:
        tipos = "/".join(sorted(c.tipos))
        personas = f" 🎙{', '.join(c.personas)}" if c.personas else ""
        print(f"  {c.id} x{c.cobertura} [{'/'.join(sorted(c.secciones))}|{tipos}]{personas}  {c.principal.titulo[:85]}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Radar IA")
    p.add_argument("--solo-recoleccion", action="store_true")
    p.add_argument("--sin-correo", action="store_true")
    p.add_argument("--forzar", action="store_true")
    args = p.parse_args(argv)

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ahora = datetime.now(timezone.utc)
    if not (args.forzar or args.solo_recoleccion):
        corre, motivo = horario.debe_correr(ahora, horario.ultimo_envio())
        print(motivo)
        if not corre:
            return 0

    vistos = horario.leer_vistos()
    noticias, reportes = recolectar(ahora, version_vista=vistos["changelog"] or None)
    noticias = horario.filtrar_vistos(noticias, vistos)
    clusters = agrupar(noticias)
    caidos = [f"{r.medio} ({r.error})" for r in reportes if r.error]
    print(f"Recolección: {len(noticias)} notas nuevas, {len(clusters)} historias. Fuentes con error: {caidos or 'ninguna'}")

    if args.solo_recoleccion:
        mostrar_recoleccion(reportes, noticias, clusters)
        return 0
    if len(reportes) - len(caidos) < 3:
        raise SystemExit("Casi todas las fuentes fallaron; no se envía nada.")

    from noticias.analizar import generar_resumen
    from noticias.pagina import generar_pagina

    fecha = horario.fecha_chile(ahora)
    historial = [h["titular"] for h in horario.leer_historial() if h["fecha"] != fecha]
    resumen = generar_resumen(clusters, INTERESES.read_text(encoding="utf-8"), historial, fecha)
    url = generar_pagina(resumen)
    print(f"Página: {url}")
    for i, n in enumerate(resumen.noticias, 1):
        print(f"  {i}. [{n.seccion}] {n.titular}")
    if resumen.aviso:
        print(f"  {resumen.aviso}")

    if args.sin_correo:
        return 0

    from noticias.correo import enviar
    destino = enviar(resumen)
    print(f"Correo enviado a {destino}")

    elegidos = {n.id for n in resumen.noticias}
    links = [l for c in clusters if c.id in elegidos for l in c.links]
    links += [n.link for n in noticias if n.fecha is None and n.tipo != "release"]
    version = max((n.version for n in noticias if n.version), default="", key=lambda v: tuple(map(int, v.split("."))))
    horario.guardar_vistos(fecha, links, version)
    horario.marcar_enviado(fecha, url)
    horario.guardar_historial(fecha, [n.titular for n in resumen.noticias])
    return 0


if __name__ == "__main__":
    sys.exit(main())
