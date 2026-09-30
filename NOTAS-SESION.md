# Notas de sesión (30-09-2026)

**Problema:** un resumen diario por correo, gratis y en la nube. Nació como noticias generales y se pivoteó a **Radar IA** (Claude Code, Anthropic, competencia y voces).

**Resultado:** funcionando en GitHub Actions. Primera corrida manual en verde: llegó el correo y abre la página de Pages.
- Repo público: github.com/cacoghio/resumen-noticias (usuario `cacoghio`).
- Página: cacoghio.github.io/resumen-noticias/
- Secrets en Actions: `GEMINI_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`. El `.env` local está ignorado y nunca se subió.

**Decisiones:**
- Solo fuentes abiertas (RSS, 3 páginas HTML y el changelog). X, Instagram, TikTok y LinkedIn quedan fuera (sin acceso gratis).
- Cantidad variable de ítems (0 a 10), no 5 fijos.
- Repo público porque GitHub Pages gratis lo exige.
- Certificados: se usa `certifi` (la verificación SSL sigue activada).

**Pendiente:** confirmar el envío automático de mañana (01-10) cerca de las 8:30 y revisar la corrida en Actions. Quizás ajustar `intereses.md` según lo que llegue.
