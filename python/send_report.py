#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://api.resend.com/emails"


def redact(text: str, secret: str) -> str:
    if secret:
        return text.replace(secret, "***")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", required=True)
    parser.add_argument("--subject", required=True)
    args = parser.parse_args()

    api_key = os.environ.get("RESEND_API_KEY", "")
    report_from = os.environ.get("REPORT_FROM", "")
    report_to = os.environ.get("REPORT_TO", "")
    if not api_key or not report_from or not report_to:
        print("Falta configuración privada de Resend.", file=sys.stderr)
        return 1

    try:
        with open(args.html, "r", encoding="utf-8") as handle:
            html_body = handle.read()
    except OSError:
        print("No se pudo leer el HTML generado.", file=sys.stderr)
        return 1

    payload = json.dumps(
        {
            "from": report_from,
            "to": [report_to],
            "subject": args.subject,
            "html": html_body,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "User-Agent": "eco-weekly-report/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        detail = redact(detail, api_key)
        print(
            "Resend rechazó el envío (HTTP {code}): {detail}".format(
                code=exc.code, detail=detail.replace("\n", " ")
            ),
            file=sys.stderr,
        )
        return 1
    except urllib.error.URLError:
        print("No se pudo conectar con la API de Resend.", file=sys.stderr)
        return 1

    if status < 200 or status >= 300:
        print("Resend devolvió un estado inesperado: {code}".format(code=status), file=sys.stderr)
        return 1

    print("Correo enviado mediante Resend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
