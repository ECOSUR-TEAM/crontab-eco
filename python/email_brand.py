#!/usr/bin/env python3
"""Constantes compartidas por la plantilla y el envío del correo."""

# El HTML referencia el logo con CID; Resend adjunta el PNG con este content_id.
LOGO_CID = "logo-ecosur"
LOGO_FILENAME = "logoEcosur-email.png"
LOGO_CONTENT_TYPE = "image/png"

# Familia Sans es la tipografía corporativa. El resto de la pila cubre clientes
# que no tienen la fuente instalada (Gmail, Outlook, Apple Mail, móviles).
FONT_STACK = "'Family Sans','Segoe UI',Arial,Helvetica,sans-serif"

HOME_URL_DEFAULT = "https://www.ecosur.mx/"
