#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

echo "ISeeYou install.sh — creating virtualenv at ${VENV_DIR} and installing pinned dependencies..."

if [ -d "${VENV_DIR}" ]; then
  echo "Virtualenv already exists at ${VENV_DIR}"
else
  python3 -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip wheel setuptools

if [ ! -f "${ROOT_DIR}/requirements.txt" ]; then
  echo "ERROR: requirements.txt not found in ${ROOT_DIR}"
  exit 2
fi

pip install -r "${ROOT_DIR}/requirements.txt"

echo "Setting file permissions for repository (owner read/write, remove world access)..."
chmod -R u+rwX,go-rwx "${ROOT_DIR}"

echo "Optional: generating a self-signed dev certificate (dev only)."
read -r -p "Generate a dev HTTPS cert and key in ${ROOT_DIR}/certs? [y/N] " gen
if [[ "${gen}" =~ ^[Yy]$ ]]; then
  mkdir -p "${ROOT_DIR}/certs"
  # Create a 2048-bit key and one-year cert for localhost (development only)
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -subj "/CN=localhost" \
    -keyout "${ROOT_DIR}/certs/iseeyou.key" \
    -out "${ROOT_DIR}/certs/iseeyou.crt"
  echo "Dev cert generated at ${ROOT_DIR}/certs/iseeyou.crt"
fi

echo ""
echo "Installation complete."
echo "Activate the environment with:"
echo "  source ${VENV_DIR}/bin/activate"
echo ""
echo "Developer notes:"
echo "- To run tests: pytest -q"
echo "- To run with Gunicorn (recommended for production test):"
echo "    gunicorn --bind 0.0.0.0:8080 --workers 3 \"iseeyou.dashboard:create_app()\""