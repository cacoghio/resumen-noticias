# SPEC: Radar IA (repo `resumen-noticias`)

Correo diario cerca de las 8:30 (hora de Chile) con las novedades de IA generativa, enfocado en Claude Code, Anthropic/Claude y la competencia, más lo que dicen personas seguidas. Incluye un link a una página con el análisis. Costo $0: GitHub Actions + GitHub Pages + Gemini API (plan gratis) + Gmail SMTP.

## Flujo
1. **Horario** (`noticias/horario.py`): el workflow corre a las 11:15 y 12:15 UTC. El script solo sigue si en Chile (`America/Santiago`) son entre las 08:00 y las 11:00 y hoy aún no se envió (`docs/estado.json`). Con eso se cubre el cambio UTC-3/UTC-4. `--forzar` se salta el chequeo.
2. **Recolección** (`noticias/recolectar.py`): RSS/Atom, páginas de listado HTML (anthropic.com/news, /engineering, claude.com/blog) y el `CHANGELOG.md` de Claude Code. Una fuente caída no detiene nada. Ventana de 36 horas. Las fuentes del mismo sitio se piden en fila con pausa (Reddit responde 429 si van juntas).
3. **Vistos** (`docs/vistos.json`): links ya enviados (14 días) y última versión de Claude Code enviada. La primera vez se descartan los posts sin fecha.
4. **Deduplicación** (`noticias/deduplicar.py`): agrupa títulos parecidos y respeta los grupos de Google News. Orden de los candidatos: release > fuente de Claude/Anthropic/voces > resto; luego por cobertura (medios distintos) y fecha.
5. **Selección con Gemini** (`noticias/analizar.py`): recibe `intereses.md`, candidatos y lo enviado en los últimos 3 días. Elige entre 0 y 10 (máx. 5 por sección: `claude_code`, `anthropic`, `competencia`) con importancia 1-3.
6. **Análisis con Gemini**: titular, bajada, qué pasó, por qué importa y (opcional) qué probar. Con búsqueda de Google cuando el modelo la acepta.
7. **Validación** (`noticias/validar.py`): ids existentes y sin repetir, máximo por sección, análisis presente, 40-400 palabras, y los links salen de las fuentes (nunca los inventa Gemini). Si falla: reintentos → otros modelos → error (el workflow queda en rojo).
8. **Página** (`noticias/pagina.py`): `docs/AAAA-MM-DD.html`, `docs/index.html`, `docs/archivo.html`, `docs/datos/AAAA-MM-DD.json`.
9. **Correo** (`noticias/correo.py`): Gmail SMTP SSL (465) con clave de aplicación, HTML + texto plano. Asunto `Radar IA DD-MM: <titular principal>`. Día sin novedades: correo corto.
10. **Estado**: se actualizan `estado.json`, `historial.json` y `vistos.json`; el workflow hace commit de `docs/`.

## Modelos (verificado el 30-09-2026)
Cadena: `gemini-3.8-flash` (con búsqueda, dos intentos) → `gemini-3.7-flash` → `gemini-3.5-flash` → sin búsqueda → `gemini-3.5-flash-lite`. SDK: `google-genai`. El modelo principal suele responder 503 por alta demanda.

## Fuentes (verificadas el 30-09-2026)
- **Claude Code:** changelog en `raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md` (un ítem "Claude Code X.Y.Z" con las versiones nuevas) y r/ClaudeCode.
- **Anthropic y Claude:** anthropic.com/news, anthropic.com/engineering, claude.com/blog (HTML), YouTube Anthropic, r/ClaudeAI, Hacker News, Google News (en inglés y español).
- **Voces:** YouTube Benjamín Cordero (@bencord), Simon Willison, Google News por Dario Amodei / Boris Cherny / Sam Altman.
- **Competencia:** OpenAI, Google AI, DeepMind, Google News (ChatGPT/OpenAI/Gemini/Cursor/Codex), Xataka IA.
- **Sin acceso gratis:** X, Instagram, TikTok, LinkedIn.

## Criterios de aceptación
1. El correo llega a diario cerca de las 8:30 (hora de Chile).
2. Trae de 0 a 10 ítems agrupados en Claude Code / Anthropic / Competencia; los días tranquilos llega un correo corto.
3. Todo release nuevo de Claude Code aparece el mismo día, resumido.
4. Los videos nuevos de @bencord y del canal de Anthropic pueden aparecer cuando son del tema.
5. Nada repetido en 14 días (salvo una novedad real).
6. Todos los links salen de las fuentes.
7. Si cae una fuente, el correo sale igual; si cae Gemini, se usan los respaldos; si fallan todos, el workflow queda en rojo.
8. Costo $0 y `.env` nunca en el repo.
9. Se puede lanzar a mano desde Actions.

## Comandos locales
- `python resumen.py --solo-recoleccion`: recolecta y deduplica; no llama a Gemini.
- `python resumen.py --sin-correo --forzar`: todo menos el correo; genera `docs/`.
- `python resumen.py --forzar`: todo, incluido el correo.
