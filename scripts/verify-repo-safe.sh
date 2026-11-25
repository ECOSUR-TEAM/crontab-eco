#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE"

fail() {
  printf 'NO LISTO: %s\n' "$1" >&2
  exit 1
}

[ -f .env ] || fail 'falta el .env local (plantilla: .env.example)'
[ -f .gitignore ] || fail 'falta .gitignore'
grep -q '^\.env$' .gitignore || fail '.gitignore no excluye .env'
grep -q '^state/$' .gitignore || fail '.gitignore no excluye state/'

for file in run-weekly-report.sh scripts/configure-env.sh scripts/verify-repo-safe.sh; do
  [ -x "$file" ] || fail "$file no es ejecutable"
done

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    fail '.env está rastreado por Git; quítalo del índice antes de subir'
  fi
  git check-ignore -q .env || fail 'Git no ignora .env'
fi

python3 - <<'PY' || exit 1
import re
from pathlib import Path

pattern = re.compile(r"re_[A-Za-z0-9_-]{16,}")
offenders = []
for path in Path(".").rglob("*"):
    if not path.is_file() or path.name == ".env" or "__pycache__" in path.parts:
        continue
    if any(part in {"logs", "out", "state"} for part in path.parts):
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    if pattern.search(text):
        offenders.append(str(path))
if offenders:
    print("NO LISTO: posible API key en: " + ", ".join(offenders), file=__import__("sys").stderr)
    raise SystemExit(1)
PY

printf 'REPO_SAFE_OK\n'
