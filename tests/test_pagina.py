from noticias import pagina
from noticias.correo import asunto, texto_plano
from noticias.validar import Fuente, Item, Mirada, Resumen


def resumen_de_prueba():
    items = [
        Item(id=f"c00{i}", ambito="chile" if i <= 3 else "mundo", tema="Tecnología e IA",
             titular=f"Titular <{i}>", bajada="Bajada.", contexto="Contexto.",
             miradas=[Mirada(actor="Gobierno", postura="Postura.")], que_mirar="Hitos.",
             fuentes=[Fuente(medio="La Tercera", titulo="t", link=f"https://ejemplo.cl/{i}")], cobertura=3)
        for i in range(1, 6)
    ]
    return Resumen(fecha="2026-09-29", modelo="gemini-x", noticias=items)


def test_fecha_larga_en_espanol():
    assert pagina.fecha_larga("2026-09-29") == "Martes 29 de septiembre de 2026"


def test_genera_pagina_del_dia_indice_y_json(tmp_path, monkeypatch):
    monkeypatch.setattr(pagina, "DOCS", tmp_path)
    pagina.generar_pagina(resumen_de_prueba())
    html = (tmp_path / "2026-09-29.html").read_text(encoding="utf-8")
    assert html == (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Titular &lt;1&gt;" in html  # se escapa el HTML
    assert html.count("<article") == 5
    assert (tmp_path / "datos" / "2026-09-29.json").exists()
    assert "2026-09-29.html" in (tmp_path / "archivo.html").read_text(encoding="utf-8")


def test_correo_tiene_5_titulares_y_link_a_la_pagina(monkeypatch):
    monkeypatch.setattr(pagina, "URL_PAGINAS", "https://juan.github.io/resumen-noticias")
    r = resumen_de_prueba()
    html = pagina.html_correo(r)
    assert html.count("https://ejemplo.cl/") == 5
    assert "https://juan.github.io/resumen-noticias/2026-09-29.html" in html
    assert asunto(r) == "Resumen 29-09: Titular <1>"
    assert "https://juan.github.io/resumen-noticias/2026-09-29.html" in texto_plano(r)
