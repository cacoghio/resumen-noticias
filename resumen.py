"""Resumen diario de noticias.

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


def mostrar_recoleccion(reportes, noticias, clusters, cuantos=15):
    print("== Feeds ==")
    for r in reportes:
        estado = f"ERROR {r.error}" if r.error else "ok"
        print(f"  {r.medio:<20} leídas={r.leidas:<4} últimas 30h={r.recientes:<4} {estado}")
    print(f"\nNotas: {len(noticias)}  ->  clusters (historias únicas): {len(clusters)}")
    print(f"\n== Top {cuantos} por cobertura ==")
    for c in clusters[:cuantos]:
        marca = " [portada]" if c.portada else ""
        medios = ", ".join(sorted({n.medio for n in c.noticias}))
        print(f"  {c.id} x{c.cobertura}{marca}  {c.principal.titulo[:90]}")
        print(f"         {medios}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Resumen diario de noticias")
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

    noticias, reportes = recolectar(ahora)
    clusters = agrupar(noticias)
    caidos = [r.medio for r in reportes if r.error]
    print(f"Recolección: {len(noticias)} notas, {len(clusters)} historias. Feeds con error: {caidos or 'ninguno'}")

    if args.solo_recoleccion:
        mostrar_recoleccion(reportes, noticias, clusters)
        return 0
    if len(clusters) < 10:
        raise SystemExit("Muy pocas noticias recolectadas; algo anda mal con los feeds.")

    from noticias.analizar import generar_resumen
    from noticias.pagina import generar_pagina

    fecha = horario.fecha_chile(ahora)
    historial = [h["titular"] for h in horario.leer_historial() if h["fecha"] != fecha]
    resumen = generar_resumen(clusters, INTERESES.read_text(encoding="utf-8"), historial, fecha)
    url = generar_pagina(resumen)
    print(f"Página: {url}")
    for i, n in enumerate(resumen.noticias, 1):
        print(f"  {i}. [{n.ambito}/{n.tema}] {n.titular}")

    if args.sin_correo:
        return 0

    from noticias.correo import enviar
    destino = enviar(resumen)
    print(f"Correo enviado a {destino}")
    horario.marcar_enviado(fecha, url)
    horario.guardar_historial(fecha, [n.titular for n in resumen.noticias])
    return 0


if __name__ == "__main__":
    sys.exit(main())
