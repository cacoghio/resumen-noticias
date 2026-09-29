from datetime import datetime, timedelta, timezone

from noticias.modelos import Noticia
from noticias.deduplicar import agrupar, normalizar, similitud

AHORA = datetime(2026, 9, 29, 11, 0, tzinfo=timezone.utc)


def nota(titulo, medio="La Tercera", portada=False, horas=1, ambito="chile"):
    return Noticia(
        medio=medio,
        ambito=ambito,
        titulo=titulo,
        resumen="",
        link=f"https://ejemplo.cl/{abs(hash((titulo, medio)))}",
        fecha=AHORA - timedelta(hours=horas),
        portada=portada,
    )


def test_normalizar_quita_tildes_puntuacion_y_palabras_vacias():
    assert normalizar("El Banco Central sube la tasa: ¿qué significa?") == {
        "banco", "central", "sube", "tasa", "significa",
    }


def test_similitud_alta_para_misma_historia_con_otras_palabras():
    a = "Banco Central sube la tasa de interés a 5%"
    b = "Banco Central de Chile sube tasa de interés al 5%"
    assert similitud(a, b) >= 0.5


def test_similitud_baja_para_historias_distintas():
    assert similitud("Apple presenta nuevo iPhone", "Banco Central sube la tasa") < 0.2


def test_agrupa_misma_historia_de_dos_medios():
    clusters = agrupar([
        nota("Banco Central sube la tasa de interés a 5%", medio="La Tercera"),
        nota("Banco Central de Chile sube tasa de interés al 5%", medio="DF"),
        nota("Apple presenta nuevo iPhone con IA", medio="Xataka", ambito="mundo"),
    ])
    assert len(clusters) == 2
    grande = clusters[0]
    assert grande.cobertura == 2
    assert {n.medio for n in grande.noticias} == {"La Tercera", "DF"}


def test_cobertura_cuenta_medios_distintos_no_notas():
    clusters = agrupar([
        nota("Senado aprueba reforma de pensiones en general", medio="La Tercera", horas=1),
        nota("Senado aprueba en general la reforma de pensiones", medio="La Tercera", horas=2),
    ])
    assert len(clusters) == 1
    assert clusters[0].cobertura == 1


def test_alias_de_un_mismo_medio_cuentan_una_vez():
    clusters = agrupar([
        nota("Huracán toca tierra en México con lluvias intensas", medio="BBC"),
        nota("Huracán toca tierra en México con lluvias intensas", medio="BBC Mundo"),
        nota("Huracán toca tierra en México con lluvias intensas", medio="EL PAÍS"),
        nota("Huracán toca tierra en México con lluvias intensas", medio="El País América"),
    ])
    assert clusters[0].cobertura == 2


def test_portada_se_propaga_al_cluster():
    clusters = agrupar([
        nota("Temblor sacude el norte de Chile sin daños", medio="Cooperativa"),
        nota("Temblor sacude el norte de Chile: no hay daños", medio="Google News", portada=True),
    ])
    assert clusters[0].portada is True


def test_orden_por_cobertura_luego_portada():
    clusters = agrupar([
        nota("OpenAI lanza nuevo modelo de razonamiento", medio="Xataka", ambito="mundo"),
        nota("Codelco reporta alza en producción de cobre", medio="DF"),
        nota("Codelco reporta alza en la producción de cobre", medio="La Tercera"),
        nota("Gobierno anuncia plan de vivienda", medio="Cooperativa", portada=True),
    ])
    assert clusters[0].cobertura == 2
    assert clusters[1].portada is True


def test_notas_del_mismo_grupo_van_juntas_aunque_el_titulo_difiera():
    a = nota("Gobierno retira reforma de seguridad", medio="La Tercera")
    b = nota("Derrota para el ministro Arrau", medio="El Mostrador")
    a.grupo = b.grupo = "g1"
    clusters = agrupar([a, b])
    assert len(clusters) == 1
    assert clusters[0].cobertura == 2


def test_nota_suelta_se_une_a_grupo_de_google_por_titulo():
    a = nota("Gobierno retira reforma de seguridad", medio="La Tercera")
    b = nota("Derrota para el ministro Arrau", medio="El Mostrador")
    a.grupo = b.grupo = "g1"
    c = nota("Gobierno retira la reforma de seguridad", medio="Cooperativa")
    clusters = agrupar([a, b, c])
    assert len(clusters) == 1
    assert clusters[0].cobertura == 3


def test_ids_de_cluster_son_unicos_y_estables():
    clusters = agrupar([nota("Uno dos tres cuatro"), nota("Cinco seis siete ocho")])
    assert [c.id for c in clusters] == ["c001", "c002"]
