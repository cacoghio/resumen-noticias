"""Envía el resumen por Gmail (SMTP SSL + clave de aplicación)."""
import os
import smtplib
from email.message import EmailMessage

from .config import clave
from .pagina import html_correo, url_del_dia
from .validar import Resumen


def texto_plano(resumen: Resumen) -> str:
    lineas = [f"Radar IA ({resumen.fecha})", ""]
    if resumen.aviso:
        lineas += [resumen.aviso, ""]
    for nombre, items in resumen.secciones():
        lineas.append(nombre.upper())
        for n in items:
            lineas += [f"- {n.titular}", f"  {n.bajada}", f"  {n.fuentes[0].medio}: {n.fuentes[0].link}"]
        lineas.append("")
    lineas.append(f"Análisis completo: {url_del_dia(resumen.fecha)}")
    return "\n".join(lineas)


def asunto(resumen: Resumen) -> str:
    dd, mm = resumen.fecha[8:10], resumen.fecha[5:7]
    principal = resumen.noticias[0].titular if resumen.noticias else "día tranquilo"
    return f"Radar IA {dd}-{mm}: {principal}"


def enviar(resumen: Resumen) -> str:
    usuario = clave("GMAIL_USER")
    destino = os.environ.get("DESTINATARIO", "").strip() or usuario
    msg = EmailMessage()
    msg["Subject"] = asunto(resumen)
    msg["From"] = f"Resumen de noticias <{usuario}>"
    msg["To"] = destino
    msg.set_content(texto_plano(resumen))
    msg.add_alternative(html_correo(resumen), subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(usuario, clave("GMAIL_APP_PASSWORD"))
        smtp.send_message(msg)
    return destino
