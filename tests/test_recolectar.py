from datetime import datetime, timezone

from noticias.config import Feed
from noticias.recolectar import (
    detectar_personas, novedades_changelog, parsear, parsear_changelog, parsear_html,
)

AHORA = datetime(2026, 9, 30, 11, 0, tzinfo=timezone.utc)

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Prueba</title>
<item>
  <title>Noticia reciente</title>
  <link>https://ejemplo.com/reciente</link>
  <description>&lt;p&gt;Resumen &lt;b&gt;con&lt;/b&gt; HTML&lt;/p&gt;</description>
  <pubDate>Wed, 30 Sep 2026 09:00:00 GMT</pubDate>
</item>
<item>
  <title>Noticia vieja</title>
  <link>https://ejemplo.com/vieja</link>
  <pubDate>Sat, 26 Sep 2026 09:00:00 GMT</pubDate>
</item>
</channel></rss>"""

YOUTUBE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
 <entry>
  <title>Anthropic lanza Claude Sonnet 5.5</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=abc"/>
  <author><name>Benjam\xc3\xadn Cordero</name></author>
  <published>2026-09-30T08:00:00+00:00</published>
  <media:group>
   <media:title>Anthropic lanza Claude Sonnet 5.5</media:title>
   <media:description>Probamos el modelo nuevo en Claude Code.</media:description>
  </media:group>
 </entry>
</feed>"""

GOOGLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Google News</title>
<item>
  <title>Anthropic launches Claude - TechCrunch</title>
  <link>https://news.google.com/rss/articles/principal</link>
  <pubDate>Wed, 30 Sep 2026 08:00:00 GMT</pubDate>
  <description>&lt;ol&gt;&lt;li&gt;&lt;a href="https://news.google.com/a1" target="_blank"&gt;Anthropic launches Claude&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;TechCrunch&lt;/font&gt;&lt;/li&gt;&lt;li&gt;&lt;a href="https://news.google.com/a2" target="_blank"&gt;Claude gets an upgrade&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;The Verge&lt;/font&gt;&lt;/li&gt;&lt;/ol&gt;</description>
  <source url="https://techcrunch.com">TechCrunch</source>
</item>
</channel></rss>"""

HTML_NEWS = """
<a href="/news/accenture-embedded-evaluation" class="x"><div class="m"><time class="d">Sep 29, 2026</time><span class="s">Announcements</span></div><span class="t"> Partnering with Accenture on embedded evaluation</span></a>
<a href="/news/old-post" class="x"><div class="m"><time class="d">Sep 10, 2026</time><span class="s">Science</span></div><span class="t"> An old post</span></a>
<a href="/news">Todas las noticias</a>
"""

HTML_BLOG = """
<a href="/blog/claude-in-chrome-generally-available"><img src="x.png"></a>
<a href="/blog/claude-in-chrome-generally-available">Read more</a>
<a href="/blog/cowork-is-now-claude">Read more</a>
"""

CHANGELOG = """# Changelog

## 2.1.286

- Added `claude doctor --json`
- Fixed a crash on resume

## 2.1.285

- Added `CLAUDE_CODE_DISABLE_WEB_FETCH` environment variable

## 2.1.284

- Fixed hooks not firing on Windows
"""


def test_parsear_filtra_viejas_y_limpia_html():
    notas = parsear(Feed("Prueba", "anthropic", "x"), RSS, AHORA)
    assert [n.titulo for n in notas] == ["Noticia reciente"]
    assert notas[0].resumen == "Resumen con HTML"
    assert notas[0].medio == "Prueba"
    assert notas[0].seccion == "anthropic"


def test_youtube_marca_persona_video_y_usa_descripcion():
    feed = Feed("YouTube Benjamín Cordero", "voces", "x", item="video", persona="Benjamín Cordero")
    notas = parsear(feed, YOUTUBE, AHORA)
    assert len(notas) == 1
    assert notas[0].tipo == "video"
    assert notas[0].personas == ["Benjamín Cordero"]
    assert "Claude Code" in notas[0].resumen


def test_google_news_relacionadas_quedan_en_el_mismo_grupo():
    notas = parsear(Feed("GN", "anthropic", "x", google=True), GOOGLE, AHORA)
    assert [(n.medio, n.titulo) for n in notas] == [
        ("TechCrunch", "Anthropic launches Claude"),
        ("The Verge", "Claude gets an upgrade"),
    ]
    assert len({n.grupo for n in notas}) == 1


def test_detectar_personas_con_tildes_alias_y_mayusculas():
    assert detectar_personas("Dario Amodei habló con Boris Cherny") == ["Dario Amodei", "Boris Cherny"]
    assert detectar_personas("nuevo video de BENJAMIN CORDERO") == ["Benjamín Cordero"]
    assert detectar_personas("Daniela Amodei y otros") == []


def test_html_listado_extrae_titulo_fecha_y_descarta_viejos():
    feed = Feed("Anthropic News", "anthropic", "x", tipo="html", prefijo="/news/", base="https://www.anthropic.com")
    notas = parsear_html(feed, HTML_NEWS, AHORA)
    assert [n.titulo for n in notas] == ["Partnering with Accenture on embedded evaluation"]
    assert notas[0].link == "https://www.anthropic.com/news/accenture-embedded-evaluation"
    assert notas[0].fecha.day == 29


def test_html_listado_sin_fecha_usa_el_slug_como_titulo_y_une_anclas_repetidas():
    feed = Feed("Claude Blog", "anthropic", "x", tipo="html", prefijo="/blog/", base="https://claude.com", item="blog")
    notas = parsear_html(feed, HTML_BLOG, AHORA)
    assert [n.titulo for n in notas] == ["Claude in chrome generally available", "Cowork is now claude"]
    assert all(n.fecha is None for n in notas)


def test_novedades_changelog_solo_versiones_nuevas():
    version, bullets = novedades_changelog(CHANGELOG, ultima="2.1.284")
    assert version == "2.1.286"
    assert [v for v, _ in bullets] == ["2.1.286", "2.1.285"]
    assert "Added `claude doctor --json`" in bullets[0][1][0]


def test_novedades_changelog_primera_vez_trae_solo_la_ultima():
    version, bullets = novedades_changelog(CHANGELOG, ultima=None)
    assert version == "2.1.286"
    assert [v for v, _ in bullets] == ["2.1.286"]


def test_novedades_changelog_sin_novedades():
    assert novedades_changelog(CHANGELOG, ultima="2.1.286") == ("2.1.286", [])


def test_parsear_changelog_arma_un_item_release_con_link_por_version():
    feed = Feed("Claude Code", "claude_code", "x", tipo="changelog")
    notas = parsear_changelog(feed, CHANGELOG, AHORA, ultima="2.1.284")
    assert len(notas) == 1
    n = notas[0]
    assert n.tipo == "release" and n.version == "2.1.286"
    assert n.titulo == "Claude Code 2.1.285 a 2.1.286"
    assert n.link == "https://github.com/anthropics/claude-code/releases/tag/v2.1.286"
    assert "claude doctor --json" in n.resumen and "WEB_FETCH" in n.resumen
    assert "hooks not firing" not in n.resumen
