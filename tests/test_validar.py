import pytest

from noticias.deduplicar import agrupar
from noticias.validar import Analisis, Elegida, ErrorValidacion, armar_resumen
from tests.test_deduplicar import nota

TEXTO_30 = " ".join(["palabra"] * 30)


def clusters_de_prueba(n=12):
    titulos = [
        "alfa uno beta gamma", "delta dos epsilon zeta", "eta tres theta iota", "kappa cuatro lambda mu",
        "nu cinco xi omicron", "pi seis rho sigma", "tau siete upsilon phi", "chi ocho psi omega",
        "arbol nueve roble pino", "mesa diez silla sofa", "rio once lago mar", "sol doce luna estrella",
    ]
    return agrupar([nota(t, medio=f"Medio{i}") for i, t in enumerate(titulos[:n])])


def elegida(i, seccion="anthropic", importancia=2):
    return Elegida(id=i, seccion=seccion, importancia=importancia)


def analisis(i, que_paso=TEXTO_30, por_que="Importa porque cambia el flujo de trabajo de todos los días.", probar=""):
    return Analisis(id=i, titular=f"Titular {i}", bajada="Una bajada breve.", que_paso=que_paso,
                    por_que_importa=por_que, que_probar=probar)


def armar(cl, elegidas, textos=None):
    textos = textos if textos is not None else [analisis(e.id) for e in elegidas]
    return armar_resumen(cl, elegidas, textos, fecha="2026-09-30", modelo="x")


def test_resumen_valido_usa_links_de_los_fuentes():
    cl = clusters_de_prueba()
    elegidas = [elegida(cl[0].id, "claude_code"), elegida(cl[1].id), elegida(cl[2].id, "competencia")]
    resumen = armar(cl, elegidas)
    assert len(resumen.noticias) == 3
    links = {n.link for c in cl for n in c.noticias}
    assert all(f.link in links for item in resumen.noticias for f in item.fuentes)
    assert resumen.aviso == ""


def test_items_salen_ordenados_por_seccion_y_luego_importancia():
    cl = clusters_de_prueba()
    elegidas = [
        elegida(cl[0].id, "competencia", 3), elegida(cl[1].id, "claude_code", 1),
        elegida(cl[2].id, "claude_code", 3), elegida(cl[3].id, "anthropic", 2),
    ]
    resumen = armar(cl, elegidas)
    assert [(i.seccion, i.importancia) for i in resumen.noticias] == [
        ("claude_code", 3), ("claude_code", 1), ("anthropic", 2), ("competencia", 3),
    ]
    assert [nombre for nombre, _ in resumen.secciones()] == ["Claude Code", "Anthropic y Claude", "Competencia"]


def test_dia_sin_noticias_es_valido_y_deja_aviso():
    resumen = armar(clusters_de_prueba(), [], textos=[])
    assert resumen.noticias == []
    assert "tranquilo" in resumen.aviso.lower()


def test_rechaza_mas_de_10():
    cl = clusters_de_prueba()
    elegidas = [elegida(c.id, s) for c, s in zip(cl[:11], ["claude_code", "anthropic", "competencia"] * 4)]
    with pytest.raises(ErrorValidacion, match="10"):
        armar(cl, elegidas)


def test_rechaza_mas_de_5_en_una_seccion():
    cl = clusters_de_prueba()
    with pytest.raises(ErrorValidacion, match="sección"):
        armar(cl, [elegida(c.id, "claude_code") for c in cl[:6]])


def test_rechaza_id_inventado_y_repetido():
    cl = clusters_de_prueba()
    with pytest.raises(ErrorValidacion, match="c999"):
        armar(cl, [elegida(cl[0].id), elegida("c999")])
    with pytest.raises(ErrorValidacion, match="repetid"):
        armar(cl, [elegida(cl[0].id), elegida(cl[0].id)])


def test_rechaza_analisis_muy_corto():
    cl = clusters_de_prueba()
    corto = analisis(cl[0].id, que_paso="Corto.", por_que="Nada.")
    with pytest.raises(ErrorValidacion, match="palabras"):
        armar(cl, [elegida(cl[0].id)], textos=[corto])


def test_rechaza_analisis_faltante():
    cl = clusters_de_prueba()
    with pytest.raises(ErrorValidacion, match="análisis"):
        armar(cl, [elegida(cl[0].id), elegida(cl[1].id)], textos=[analisis(cl[0].id)])


def test_etiquetas_de_release_video_y_persona():
    cl = agrupar([
        nota("Claude Code 2.1.286", medio="GitHub", tipo="release", seccion="claude_code"),
        nota("Boris Cherny habla de hooks", medio="YouTube", tipo="video", personas=["Boris Cherny"]),
    ])
    resumen = armar(cl, [elegida(c.id, "claude_code") for c in cl])
    etiquetas = {e for i in resumen.noticias for e in i.etiquetas}
    assert etiquetas == {"📦 Release", "▶ Video", "🎙 Boris Cherny"}
