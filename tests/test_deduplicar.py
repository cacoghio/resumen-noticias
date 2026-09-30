from datetime import datetime, timedelta, timezone

from noticias.modelos import Noticia
from noticias.deduplicar import agrupar, normalizar, similitud

AHORA = datetime(2026, 9, 30, 11, 0, tzinfo=timezone.utc)


def nota(titulo, medio="TechCrunch", horas=1, seccion="anthropic", tipo="articulo", personas=None, grupo=None):
    return Noticia(
        medio=medio,
        seccion=seccion,
        titulo=titulo,
        resumen="",
        link=f"https://ejemplo.com/{abs(hash((titulo, medio)))}",
        fecha=AHORA - timedelta(hours=horas),
        tipo=tipo,
        personas=personas or [],
        grupo=grupo,
    )


def test_normalizar_quita_tildes_puntuacion_y_palabras_vacias():
    assert normalizar("El Banco Central sube la tasa: ¿qué significa?") == {
        "banco", "central", "sube", "tasa", "significa",
    }


def test_similitud_alta_para_misma_historia_con_otras_palabras():
    a = "Anthropic launches Claude Sonnet 5.5 with lower prices"
    b = "Anthropic launches new Claude Sonnet 5.5 model, cuts prices"
    assert similitud(a, b) >= 0.45


def test_similitud_baja_para_historias_distintas():
    assert similitud("OpenAI launches GPT-6.1", "Cursor raises new funding round") < 0.2


def test_agrupa_misma_historia_de_dos_medios():
    clusters = agrupar([
        nota("Anthropic launches Claude Sonnet 5.5 with lower prices", medio="TechCrunch"),
        nota("Anthropic launches new Claude Sonnet 5.5 model, cuts prices", medio="The Verge"),
        nota("Cursor raises new funding round", medio="Xataka"),
    ])
    assert len(clusters) == 2
    assert clusters[0].cobertura == 2


def test_cobertura_cuenta_medios_distintos_no_notas():
    clusters = agrupar([
        nota("Claude Code adds plugin marketplace for teams", medio="Reddit", horas=1),
        nota("Claude Code adds a plugin marketplace for teams", medio="Reddit", horas=2),
    ])
    assert len(clusters) == 1
    assert clusters[0].cobertura == 1


def test_alias_de_un_mismo_medio_cuentan_una_vez():
    clusters = agrupar([
        nota("OpenAI presenta nuevo modelo con agentes", medio="BBC"),
        nota("OpenAI presenta nuevo modelo con agentes", medio="BBC Mundo"),
        nota("OpenAI presenta nuevo modelo con agentes", medio="EL PAÍS"),
        nota("OpenAI presenta nuevo modelo con agentes", medio="El País América"),
    ])
    assert clusters[0].cobertura == 2


def test_release_va_primero_aunque_tenga_menos_cobertura():
    clusters = agrupar([
        nota("OpenAI releases another model update", medio="A"),
        nota("OpenAI releases another model update now", medio="B"),
        nota("Claude Code 2.1.286", medio="Changelog", tipo="release", seccion="claude_code"),
    ])
    assert clusters[0].tipos == {"release"}


def test_personas_y_tipos_se_propagan_al_cluster():
    clusters = agrupar([
        nota("Boris Cherny explains Claude Code hooks in a talk", personas=["Boris Cherny"]),
        nota("Boris Cherny explains Claude Code hooks in a new talk", medio="YouTube", tipo="video"),
    ])
    assert clusters[0].personas == ["Boris Cherny"]
    assert clusters[0].tipos == {"articulo", "video"}


def test_notas_del_mismo_grupo_van_juntas_aunque_el_titulo_difiera():
    a = nota("Anthropic launches new model", medio="TechCrunch", grupo="g1")
    b = nota("Claude gets a big upgrade today", medio="The Verge", grupo="g1")
    clusters = agrupar([a, b])
    assert len(clusters) == 1
    assert clusters[0].cobertura == 2


def test_nota_suelta_se_une_a_grupo_de_google_por_titulo():
    a = nota("Anthropic launches new Claude model", medio="TechCrunch", grupo="g1")
    b = nota("Claude gets a big upgrade today", medio="The Verge", grupo="g1")
    c = nota("Anthropic launches the new Claude model", medio="Xataka")
    clusters = agrupar([a, b, c])
    assert len(clusters) == 1
    assert clusters[0].cobertura == 3


def test_ids_de_cluster_son_unicos_y_estables():
    clusters = agrupar([nota("Uno dos tres cuatro"), nota("Cinco seis siete ocho")])
    assert sorted(c.id for c in clusters) == ["c001", "c002"]
