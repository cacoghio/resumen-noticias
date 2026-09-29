import pytest

from noticias.validar import (
    Analisis, Elegida, ErrorValidacion, Mirada, armar_resumen,
)
from tests.test_deduplicar import nota
from noticias.deduplicar import agrupar

TEXTO_40 = " ".join(["palabra"] * 40)


def clusters_de_prueba():
    titulos = [
        ("Chile uno alfa beta gamma", "chile"), ("Chile dos delta epsilon zeta", "chile"),
        ("Chile tres eta theta iota", "chile"), ("Mundo cuatro kappa lambda mu", "mundo"),
        ("Mundo cinco nu xi omicron", "mundo"), ("Mundo seis pi rho sigma", "mundo"),
    ]
    return agrupar([nota(t, medio=f"Medio{i}", ambito=a) for i, (t, a) in enumerate(titulos)])


def elegidas(ids, ambitos):
    return [Elegida(id=i, ambito=a, tema="tecnologia_ia") for i, a in zip(ids, ambitos)]


def analisis(i):
    return Analisis(
        id=i, titular=f"Titular {i}", bajada="Una bajada breve.",
        contexto=TEXTO_40 + " " + TEXTO_40,
        miradas=[Mirada(actor="Gobierno", postura=TEXTO_40), Mirada(actor="Oposición", postura="No está de acuerdo.")],
        que_mirar=TEXTO_40,
    )


def test_resumen_valido_usa_links_de_los_feeds():
    cl = clusters_de_prueba()
    ids = [c.id for c in cl[:5]]
    resumen = armar_resumen(
        cl, elegidas(ids, ["chile", "chile", "chile", "mundo", "mundo"]),
        [analisis(i) for i in ids], fecha="2026-09-29", modelo="x",
    )
    assert len(resumen.noticias) == 5
    links_feeds = {n.link for c in cl for n in c.noticias}
    assert all(f.link in links_feeds for item in resumen.noticias for f in item.fuentes)
    assert resumen.nota_mix == ""


def test_rechaza_menos_de_5():
    cl = clusters_de_prueba()
    ids = [c.id for c in cl[:4]]
    with pytest.raises(ErrorValidacion, match="5"):
        armar_resumen(cl, elegidas(ids, ["chile"] * 2 + ["mundo"] * 2),
                      [analisis(i) for i in ids], fecha="2026-09-29", modelo="x")


def test_rechaza_id_inventado():
    cl = clusters_de_prueba()
    ids = [c.id for c in cl[:4]] + ["c999"]
    with pytest.raises(ErrorValidacion, match="c999"):
        armar_resumen(cl, elegidas(ids, ["chile"] * 3 + ["mundo"] * 2),
                      [analisis(i) for i in ids], fecha="2026-09-29", modelo="x")


def test_rechaza_mix_4_chile_1_mundo():
    cl = clusters_de_prueba()
    ids = [c.id for c in cl[:5]]
    with pytest.raises(ErrorValidacion, match="mix"):
        armar_resumen(cl, elegidas(ids, ["chile"] * 4 + ["mundo"]),
                      [analisis(i) for i in ids], fecha="2026-09-29", modelo="x")


def test_mix_2_chile_3_mundo_se_acepta_con_nota():
    cl = clusters_de_prueba()
    ids = [c.id for c in cl[:5]]
    resumen = armar_resumen(cl, elegidas(ids, ["chile"] * 2 + ["mundo"] * 3),
                            [analisis(i) for i in ids], fecha="2026-09-29", modelo="x")
    assert "2 de Chile" in resumen.nota_mix


def test_rechaza_analisis_muy_corto():
    cl = clusters_de_prueba()
    ids = [c.id for c in cl[:5]]
    corto = [analisis(i) for i in ids]
    corto[0] = corto[0].model_copy(update={"contexto": "Muy corto.", "que_mirar": "Nada.", "miradas": []})
    with pytest.raises(ErrorValidacion, match="palabras"):
        armar_resumen(cl, elegidas(ids, ["chile"] * 3 + ["mundo"] * 2), corto,
                      fecha="2026-09-29", modelo="x")


def test_rechaza_analisis_faltante():
    cl = clusters_de_prueba()
    ids = [c.id for c in cl[:5]]
    with pytest.raises(ErrorValidacion, match="análisis"):
        armar_resumen(cl, elegidas(ids, ["chile"] * 3 + ["mundo"] * 2),
                      [analisis(i) for i in ids[:4]], fecha="2026-09-29", modelo="x")
