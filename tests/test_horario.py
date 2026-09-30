from datetime import datetime, timezone

from noticias.horario import (
    actualizar_historial, actualizar_vistos, debe_correr, fecha_chile, filtrar_vistos,
)
from tests.test_deduplicar import nota


def utc(h, m, dia=30, mes=9):
    return datetime(2026, mes, dia, h, m, tzinfo=timezone.utc)


def test_horario_de_verano_corre_el_cron_de_las_11_15_utc():
    # 30-sep: Chile en UTC-3 -> 11:15 UTC = 08:15
    assert debe_correr(utc(11, 15), ultimo_envio="2026-09-29")[0] is True


def test_horario_de_verano_el_segundo_cron_no_repite():
    assert debe_correr(utc(12, 15), ultimo_envio="2026-09-30")[0] is False


def test_horario_de_invierno_el_primer_cron_es_muy_temprano():
    # 15-jun: Chile en UTC-4 -> 11:15 UTC = 07:15
    assert debe_correr(utc(11, 15, dia=15, mes=6), ultimo_envio="2026-06-14")[0] is False


def test_horario_de_invierno_corre_el_cron_de_las_12_15_utc():
    assert debe_correr(utc(12, 15, dia=15, mes=6), ultimo_envio="2026-06-14")[0] is True


def test_si_el_primero_fallo_el_segundo_reintenta():
    assert debe_correr(utc(12, 15), ultimo_envio="2026-09-29")[0] is True


def test_muy_tarde_no_corre():
    assert debe_correr(utc(15, 0), ultimo_envio="2026-09-29")[0] is False


def test_fecha_chile_usa_zona_local():
    # 02:00 UTC del 1-oct es todavía 30-sep en Chile
    assert fecha_chile(utc(2, 0, dia=1, mes=10)) == "2026-09-30"


def test_historial_guarda_solo_los_ultimos_dias():
    historial = [
        {"fecha": "2026-09-25", "titular": "viejo"},
        {"fecha": "2026-09-29", "titular": "reciente"},
    ]
    nuevo = actualizar_historial(historial, "2026-09-30", ["hoy"], dias=3)
    assert [h["titular"] for h in nuevo] == ["reciente", "hoy"]


def test_filtrar_vistos_saca_links_ya_enviados():
    a, b = nota("Uno dos tres cuatro"), nota("Cinco seis siete ocho")
    vistos = {"links": {a.link: "2026-09-29"}, "changelog": ""}
    assert filtrar_vistos([a, b], vistos) == [b]


def test_filtrar_vistos_primera_vez_descarta_lo_que_no_tiene_fecha():
    con_fecha, sin_fecha = nota("Uno dos tres cuatro"), nota("Cinco seis siete ocho")
    sin_fecha.fecha = None
    release = nota("Claude Code 2.1.286", tipo="release")
    release.fecha = None
    assert filtrar_vistos([con_fecha, sin_fecha, release], {"links": {}, "changelog": ""}) == [con_fecha, release]


def test_actualizar_vistos_guarda_14_dias_y_la_version_del_changelog():
    vistos = {"links": {"https://viejo": "2026-09-01", "https://reciente": "2026-09-25"}, "changelog": "2.1.280"}
    nuevo = actualizar_vistos(vistos, "2026-09-30", ["https://hoy"], "2.1.286")
    assert set(nuevo["links"]) == {"https://reciente", "https://hoy"}
    assert nuevo["changelog"] == "2.1.286"


def test_actualizar_vistos_conserva_la_version_si_no_hay_nueva():
    nuevo = actualizar_vistos({"links": {}, "changelog": "2.1.280"}, "2026-09-30", [], "")
    assert nuevo["changelog"] == "2.1.280"
