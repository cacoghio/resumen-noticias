# SPEC: resumen-noticias

Resumen diario de noticias: un correo cerca de las 8:30 (hora de Chile), todos los días, con 5 titulares y un link a una página HTML con análisis. Costo $0: GitHub Actions + GitHub Pages + Gemini API (free tier) + Gmail SMTP.

## Flujo
1. **Horario** (`noticias/horario.py`): el workflow corre a las 11:15 y 12:15 UTC. El script solo sigue si en Chile (`America/Santiago`) son entre 07:30 y 11:00 **y** hoy aún no se envió (`docs/estado.json`). Con eso se cubre el cambio UTC-3/UTC-4. `--forzar` se salta el chequeo.
2. **Recolección** (`noticias/recolectar.py`): lee los feeds RSS de `config.py`. Un feed caído no detiene nada; queda registrado. Solo se consideran noticias de las últimas 30 horas.
3. **Deduplicación** (`noticias/deduplicar.py`): agrupa en clusters las noticias con títulos parecidos (Jaccard de palabras normalizadas). El tamaño del cluster (cuántos medios la cubren) es la señal de "tendencia". Los items de la portada de Google News suman peso.
4. **Selección con Gemini** (`noticias/analizar.py`, llamada 1): recibe `intereses.md`, los candidatos (id, medio, título, resumen, cobertura) y los titulares enviados en los últimos 3 días. Devuelve los ids de los 5 clusters elegidos + ámbito (chile/mundo) + tema.
5. **Análisis con Gemini** (llamada 2): recibe los 5 clusters con todos sus titulares y resúmenes (distintos medios = distintas miradas). Devuelve JSON con titular, bajada, contexto, miradas y qué mirar. Si el modelo soporta Google Search grounding junto con JSON, se usa para dar contexto.
6. **Validación** (`noticias/validar.py`): 5 items, ámbito/tema válidos, links que existan en los feeds, largos razonables. Si falla: 1 reintento → modelo de respaldo → error (el workflow queda en rojo).
7. **Página** (`noticias/pagina.py`): `docs/AAAA-MM-DD.html` + `docs/index.html` (copia del día) + `docs/datos/AAAA-MM-DD.json`.
8. **Correo** (`noticias/correo.py`): Gmail SMTP SSL (465) con App Password. HTML + texto plano. Asunto: `Resumen DD-MM: <titular 1>`.
9. **Estado**: se actualizan `docs/estado.json` (último envío) y `docs/historial.json` (titulares de los últimos 3 días). El workflow hace commit de `docs/`.

## Modelos (verificado el 29-09-2026)
- Principal: `gemini-3.8-flash` (free tier, grounding con 5.000 búsquedas gratis al mes).
- Respaldo: `gemini-3.5-flash-lite` (free tier, sin grounding).
- SDK: `google-genai`.

## Feeds (verificados el 29-09-2026)
| Medio | Ámbito | URL |
|---|---|---|
| La Tercera | chile | https://www.latercera.com/arc/outboundfeeds/rss/?outputType=xml |
| Diario Financiero | chile | https://www.df.cl/noticias/site/list/port/rss.xml |
| Cooperativa | chile | https://www.cooperativa.cl/noticias/site/tax/port/all/rss____1.xml |
| CIPER | chile | https://www.ciperchile.cl/feed/ |
| Google News Chile (portada) | mixto | https://news.google.com/rss?hl=es-419&gl=CL&ceid=CL:es-419 |
| BBC Mundo | mundo | https://feeds.bbci.co.uk/mundo/rss.xml |
| El País América | mundo | https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/america/portada |
| Xataka | mundo (tech) | https://www.xataka.com/feedburner.xml |

Descartados por estar caídos o vacíos: BioBio, El Mostrador, Emol, T13, 24horas.

## Prompts
**Selección (llamada 1):** "Eres editor de un resumen diario para un lector chileno. Estos son sus intereses: {intereses.md}. Estos son los candidatos de las últimas 30 horas; `cobertura` es cuántos medios distintos publican la misma historia y `portada` indica si está en la portada de Google News. Ya se enviaron estos titulares en los últimos 3 días: {historial}; no los repitas salvo que haya un desarrollo nuevo e importante. Elige exactamente 5: 3 de ámbito chile y 2 de ámbito mundo (si no alcanza, 2 y 3). Descarta todo lo de la lista 'Excluir siempre'. Prioriza por orden de interés, tendencia (cobertura/portada) e impacto. Devuelve JSON."

**Análisis (llamada 2):** "Para cada una de estas 5 noticias (con los titulares y resúmenes de todos los medios que la cubren), escribe en español de Chile, neutral y directo: `titular` (máx. 110 caracteres, sin clickbait), `bajada` (1 frase para el correo), `contexto` (qué pasó y por qué importa hoy), `miradas` (2–3 posturas de actores distintos, sin inventar citas), `que_mirar` (próximos hitos o señales). Total ~200 palabras por noticia. No inventes datos: si no está en las fuentes ni en la búsqueda, no lo digas. Devuelve JSON."

## Criterios de aceptación
1. El correo llega todos los días entre ~8:15 y 8:45 hora Chile.
2. Trae exactamente 5 titulares con medio y link original, más el link a la página del día.
3. 3 Chile + 2 mundo (si ese día no alcanza, se permite 2+3 con una nota).
4. Cero noticias de temas excluidos.
5. Sin duplicados entre medios y sin repetir noticias de los últimos 3 días salvo desarrollo nuevo.
6. La página tiene ~200 palabras por noticia (contexto/por qué importa, miradas, qué mirar), se lee bien en el celular y está pública en Pages.
7. Todo link sale de los feeds (ninguno inventado por Gemini).
8. Si cae un feed, sale igual; si cae Gemini, reintenta y usa el respaldo; si falla todo, el workflow queda en rojo (GitHub avisa por correo).
9. Costo $0; el .env nunca está en el repo; las claves solo como Secrets.
10. Se puede lanzar a mano desde Actions.

## Comandos locales
- `python resumen.py --solo-recoleccion`: recolecta y deduplica; muestra el resultado y no llama a Gemini.
- `python resumen.py --sin-correo --forzar`: todo menos el correo; genera `docs/`.
- `python resumen.py --forzar`: todo, incluido el correo.
