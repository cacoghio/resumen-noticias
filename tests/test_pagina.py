from noticias import pagina
from noticias.correo import asunto, texto_plano
from noticias.validar import Fuente, Item, Resumen


def item(i, seccion, **extra):
    datos = dict(
        id=f"c00{i}", seccion=seccion, titular=f"Titular <{i}>", bajada="Bajada.", que_paso="Qué pasó.",
        por_que_importa="Por qué importa.", que_probar="", fuentes=[Fuente(medio="Anthropic", titulo="t", link=f"https://ejemplo.com/{i}")],
        cobertura=2, personas=[], etiquetas=[], importancia=2,
    )
    datos.update(extra)
    return Item(**datos)


def resumen_de_prueba():
    return Resumen(fecha="2026-09-30", modelo="gemini-x", noticias=[
        item(1, "claude_code", etiquetas=["📦 Release"], que_probar="Prueba `claude doctor --json`."),
        item(2, "anthropic", etiquetas=["🎙 Dario Amodei"], personas=["Dario Amodei"]),
        item(3, "competencia"),
    ])


def test_fecha_larga_en_espanol():
    assert pagina.fecha_larga("2026-09-30") == "Miércoles 30 de septiembre de 2026"


def test_genera_pagina_del_dia_indice_y_json(tmp_path, monkeypatch):
    monkeypatch.setattr(pagina, "DOCS", tmp_path)
    pagina.generar_pagina(resumen_de_prueba())
    html = (tmp_path / "2026-09-30.html").read_text(encoding="utf-8")
    assert html == (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Titular &lt;1&gt;" in html  # se escapa el HTML
    assert html.count("<article") == 3
    assert "Qué probar" in html and "claude doctor" in html
    assert html.index('id="c001"') < html.index('id="c002"') < html.index('id="c003"')
    assert '<h2 class="seccion">Anthropic y Claude</h2>' in html
    assert "🎙 Dario Amodei" in html
    assert (tmp_path / "datos" / "2026-09-30.json").exists()
    assert "2026-09-30.html" in (tmp_path / "archivo.html").read_text(encoding="utf-8")


def test_pagina_de_dia_tranquilo(tmp_path, monkeypatch):
    monkeypatch.setattr(pagina, "DOCS", tmp_path)
    pagina.generar_pagina(Resumen(fecha="2026-09-30", modelo="x", noticias=[], aviso="Día tranquilo: sin novedades."))
    assert "Día tranquilo" in (tmp_path / "2026-09-30.html").read_text(encoding="utf-8")


def test_correo_agrupa_por_seccion_y_linkea_la_pagina(monkeypatch):
    monkeypatch.setattr(pagina, "URL_PAGINAS", "https://juan.github.io/resumen-noticias")
    r = resumen_de_prueba()
    html = pagina.html_correo(r)
    assert html.count("https://ejemplo.com/") == 3
    assert "https://juan.github.io/resumen-noticias/2026-09-30.html" in html
    assert html.index("Titular &lt;1&gt;") < html.index("Titular &lt;2&gt;") < html.index("Titular &lt;3&gt;")
    assert asunto(r) == "Radar IA 30-09: Titular <1>"
    assert "https://juan.github.io/resumen-noticias/2026-09-30.html" in texto_plano(r)


def test_asunto_de_dia_tranquilo():
    r = Resumen(fecha="2026-09-30", modelo="x", noticias=[], aviso="Día tranquilo.")
    assert asunto(r) == "Radar IA 30-09: día tranquilo"
