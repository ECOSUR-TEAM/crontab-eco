#!/usr/bin/env python3
import argparse
import shlex
import sys
from pathlib import Path


def parse_env(path: Path) -> dict:
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True)
    parser.add_argument("--format", choices=("shell", "value"), default="shell")
    parser.add_argument("--keys", nargs="*", default=[])
    parser.add_argument("--required", action="store_true")
    args = parser.parse_args()

    path = Path(args.env)
    if not path.is_file():
        print("No existe el archivo de configuración privada.", file=sys.stderr)
        return 1

    values = parse_env(path)
    missing = [key for key in args.keys if not values.get(key)]
    if missing:
        print("Faltan variables obligatorias: " + ", ".join(missing), file=sys.stderr)
        return 1

    if args.format == "value":
        if len(args.keys) != 1:
            print("--format value requiere una sola clave.", file=sys.stderr)
            return 1
        print(values[args.keys[0]])
        return 0

    for key in args.keys:
        if key in values:
            print("export {}={}".format(key, shlex.quote(values[key])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
