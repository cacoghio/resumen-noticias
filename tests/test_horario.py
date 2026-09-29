from datetime import datetime, timezone

from noticias.horario import debe_correr, fecha_chile, actualizar_historial


def utc(h, m, dia=29, mes=9):
    return datetime(2026, mes, dia, h, m, tzinfo=timezone.utc)


def test_horario_de_verano_corre_el_cron_de_las_11_15_utc():
    # 29-sep: Chile en UTC-3 -> 11:15 UTC = 08:15
    assert debe_correr(utc(11, 15), ultimo_envio="2026-09-28")[0] is True


def test_horario_de_verano_el_segundo_cron_no_repite():
    assert debe_correr(utc(12, 15), ultimo_envio="2026-09-29")[0] is False


def test_horario_de_invierno_el_primer_cron_es_muy_temprano():
    # 15-jun: Chile en UTC-4 -> 11:15 UTC = 07:15
    assert debe_correr(utc(11, 15, dia=15, mes=6), ultimo_envio="2026-06-14")[0] is False


def test_horario_de_invierno_corre_el_cron_de_las_12_15_utc():
    assert debe_correr(utc(12, 15, dia=15, mes=6), ultimo_envio="2026-06-14")[0] is True


def test_si_el_primero_fallo_el_segundo_reintenta():
    assert debe_correr(utc(12, 15), ultimo_envio="2026-09-28")[0] is True


def test_muy_tarde_no_corre():
    assert debe_correr(utc(15, 0), ultimo_envio="2026-09-28")[0] is False


def test_fecha_chile_usa_zona_local():
    # 02:00 UTC del 30-sep es todavía 29-sep en Chile
    assert fecha_chile(utc(2, 0, dia=30)) == "2026-09-29"


def test_historial_guarda_solo_los_ultimos_dias():
    historial = [
        {"fecha": "2026-09-25", "titular": "viejo"},
        {"fecha": "2026-09-27", "titular": "reciente"},
    ]
    nuevo = actualizar_historial(historial, "2026-09-29", ["hoy"], dias=3)
    assert [h["titular"] for h in nuevo] == ["reciente", "hoy"]
