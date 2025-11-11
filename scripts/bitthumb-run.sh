#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="${PROJECT_ROOT}/.venv-bitthumb"

find_python() {
  local candidates=(python3.12 python3.11 python3 python)
  for candidate in "${candidates[@]}"; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
        printf "%s" "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON_BIN="$(find_python)" || {
  printf "Python 3.11 이상이 필요합니다. brew install python@3.12 또는 https://www.python.org/downloads/ 참고 후 다시 시도하세요.\n" >&2
  exit 1
}

VENV_PYTHON="${VENV_PATH}/bin/python"

if [ -d "${VENV_PATH}" ]; then
  if ! "${VENV_PYTHON}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    rm -rf "${VENV_PATH}"
  fi
fi

if [ ! -d "${VENV_PATH}" ]; then
  "$PYTHON_BIN" -m venv "${VENV_PATH}"
fi

source "${VENV_PATH}/bin/activate"

pip install --upgrade --disable-pip-version-check pip setuptools wheel >/dev/null
pip install --disable-pip-version-check "${PROJECT_ROOT}"

bitthumb-cli "$@"
