from datetime import datetime, timezone

from noticias.config import Feed
from noticias.recolectar import parsear

AHORA = datetime(2026, 9, 29, 11, 0, tzinfo=timezone.utc)

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Prueba</title>
<item>
  <title>Noticia reciente</title>
  <link>https://ejemplo.cl/reciente</link>
  <description>&lt;p&gt;Resumen &lt;b&gt;con&lt;/b&gt; HTML&lt;/p&gt;</description>
  <pubDate>Tue, 29 Sep 2026 09:00:00 GMT</pubDate>
</item>
<item>
  <title>Noticia vieja</title>
  <link>https://ejemplo.cl/vieja</link>
  <pubDate>Sat, 26 Sep 2026 09:00:00 GMT</pubDate>
</item>
</channel></rss>"""

RSS_GOOGLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Google News</title>
<item>
  <title>Hacienda ajusta proyecci\xc3\xb3n de crecimiento - La Tercera</title>
  <link>https://news.google.com/rss/articles/abc</link>
  <pubDate>Tue, 29 Sep 2026 08:00:00 GMT</pubDate>
  <source url="https://www.latercera.com">La Tercera</source>
</item>
</channel></rss>"""


RSS_GOOGLE_RELACIONADAS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Google News</title>
<item>
  <title>Gobierno retira reforma - La Tercera</title>
  <link>https://news.google.com/rss/articles/principal</link>
  <pubDate>Tue, 29 Sep 2026 08:00:00 GMT</pubDate>
  <description>&lt;ol&gt;&lt;li&gt;&lt;a href="https://news.google.com/a1" target="_blank"&gt;Gobierno retira reforma&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;La Tercera&lt;/font&gt;&lt;/li&gt;&lt;li&gt;&lt;a href="https://news.google.com/a2" target="_blank"&gt;Derrota para el ministro&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;El Mostrador&lt;/font&gt;&lt;/li&gt;&lt;/ol&gt;</description>
  <source url="https://www.latercera.com">La Tercera</source>
</item>
</channel></rss>"""


def test_google_news_relacionadas_quedan_en_el_mismo_grupo():
    notas = parsear(Feed("Google News Chile", "mixto", "x", portada=True), RSS_GOOGLE_RELACIONADAS, AHORA)
    assert [(n.medio, n.titulo) for n in notas] == [
        ("La Tercera", "Gobierno retira reforma"),
        ("El Mostrador", "Derrota para el ministro"),
    ]
    assert {n.grupo for n in notas} == {"https://news.google.com/rss/articles/principal"}
    assert all(n.portada for n in notas)


def test_parsear_filtra_viejas_y_limpia_html():
    notas = parsear(Feed("Prueba", "chile", "x"), RSS, AHORA)
    assert [n.titulo for n in notas] == ["Noticia reciente"]
    assert notas[0].resumen == "Resumen con HTML"
    assert notas[0].link == "https://ejemplo.cl/reciente"
    assert notas[0].medio == "Prueba"


def test_parsear_google_news_usa_medio_original_y_quita_sufijo():
    notas = parsear(Feed("Google News Chile", "mixto", "x", portada=True), RSS_GOOGLE, AHORA)
    assert len(notas) == 1
    assert notas[0].titulo == "Hacienda ajusta proyección de crecimiento"
    assert notas[0].medio == "La Tercera"
    assert notas[0].portada is True
