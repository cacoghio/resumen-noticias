# Radar IA

Correo diario (~8:30, hora de Chile) con las novedades de IA generativa: **Claude Code**, **Anthropic y Claude**, y la **competencia**, más lo que dicen las personas que sigues. Incluye un link a una página con el análisis completo. Todo gratis: GitHub Actions + GitHub Pages + Gemini (plan gratis) + Gmail.

- Repo: https://github.com/cacoghio/resumen-noticias
- Página: https://cacoghio.github.io/resumen-noticias/
- Días anteriores: https://cacoghio.github.io/resumen-noticias/archivo.html

## Cómo funciona
1. Dos horarios (11:15 y 12:15 UTC) cubren el cambio de hora de Chile. El script solo envía entre las 08:00 y las 11:00 hora de Chile y una vez por día.
2. Lee ~18 fuentes: changelog de Claude Code, blogs de Anthropic, YouTube (Anthropic y Benjamín Cordero), Reddit, Hacker News, Simon Willison, OpenAI, Google y búsquedas de Google News por tema y por persona.
3. Agrupa lo repetido y saca lo que ya enviaste (memoria de 14 días en `docs/vistos.json`).
4. Gemini elige entre 0 y 10 noticias (máximo 5 por sección) y escribe el análisis. Si un modelo está saturado, prueba con otros.
5. Se genera la página en `docs/` y se envía el correo. El workflow guarda los cambios en el repo.

## Cambiar mis intereses
Edita [`intereses.md`](intereses.md) (desde GitHub: abre el archivo → ícono del lápiz → **Commit changes**). Vale desde el día siguiente. Ahí cambias secciones, personas, qué descartar y el estilo.

Para sumar una fuente o una persona nueva hay que editar `noticias/config.py` (`FEEDS` y `PERSONAS`).

## Lanzarlo a mano
1. Entra a https://github.com/cacoghio/resumen-noticias/actions/workflows/resumen-diario.yml.
2. Toca **Run workflow**, deja marcada la casilla y toca el botón verde **Run workflow**.
3. En 3 a 8 minutos llega el correo. Si dejas la casilla sin marcar, respeta el horario y el "ya se envió hoy".

En tu PC (carpeta del proyecto, con el `.env` completo):
```bash
.venv\Scripts\python.exe resumen.py --sin-correo --forzar
```
Genera la página sin enviar correo. Con `--solo-recoleccion` solo revisa las fuentes.

## Si un día no llega el correo
1. Revisa Spam y la pestaña Promociones de Gmail.
2. Entra a la pestaña **Actions** del repo y mira la última corrida:
   - **Verde y sin correo:** puede que se haya saltado el horario (solo envía entre 08:00 y 11:00 hora de Chile) o que ya se hubiera enviado ese día.
   - **Roja:** abre la corrida y revisa el paso "Generar y enviar el Radar IA". Causas comunes: Gemini saturado durante toda la corrida (vuelve a lanzarla a mano más tarde), la clave de aplicación de Gmail revocada (crea otra y actualiza el secret `GMAIL_APP_PASSWORD`) o la clave de Gemini caducada o mal copiada (actualiza `GEMINI_API_KEY`).
   - **No aparece ninguna corrida:** GitHub apaga los horarios si el repo pasa 60 días sin actividad. Como el workflow guarda la página diaria en el repo, normalmente no pasa. Si ocurre, entra a Actions y toca **Enable workflow**.
3. Para actualizar un secret: Settings → Secrets and variables → Actions → clic en el nombre → **Update secret**.

## Límites conocidos
- **X/Twitter, Instagram, TikTok y LinkedIn no se leen** (no hay acceso gratis). Lo que digan ahí llega solo si un medio lo cita.
- **Reddit** a veces bloquea a GitHub (error 429). Si falla, el correo sale igual sin esa fuente.
- Las páginas de Anthropic no traen fecha: el primer día se marcan como vistas y desde el siguiente se detecta lo nuevo.
- Gemini puede cometer errores; cada noticia lleva sus fuentes para revisar.
- El repo es público: el código, `intereses.md` y las páginas de análisis son visibles. Las claves no (van como Secrets).

## Archivos
| Archivo | Para qué |
|---|---|
| `resumen.py` | Punto de entrada |
| `noticias/config.py` | Fuentes, personas, modelos y límites |
| `noticias/recolectar.py`, `deduplicar.py` | Leer fuentes y agrupar repetidos |
| `noticias/analizar.py` | Prompts y llamadas a Gemini |
| `noticias/validar.py` | Reglas que debe cumplir el resumen |
| `noticias/pagina.py`, `correo.py`, `plantillas/` | Página HTML y correo |
| `noticias/horario.py` | Horario, "ya enviado" y memoria |
| `docs/` | Lo que publica GitHub Pages (más `estado.json`, `historial.json`, `vistos.json`) |
| `SPEC.md` | Diseño y criterios de aceptación |
