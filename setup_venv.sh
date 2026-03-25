#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# U-Ask QA Automation – Virtual Environment Setup Script
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

VENV_DIR="venv"
PYTHON_MIN="3.10"

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Python version check ──────────────────────────────────────────────────────
info "Checking Python version …"
PYTHON_BIN=$(command -v python3 || command -v python || error "Python not found. Install Python ${PYTHON_MIN}+")
PY_VERSION=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    info "Python ${PY_VERSION} ✓"
else
    error "Python ${PYTHON_MIN}+ required, found ${PY_VERSION}"
fi

# ── Create virtual environment ────────────────────────────────────────────────
if [ -d "$VENV_DIR" ]; then
    warn "Virtual environment already exists at ./${VENV_DIR} – skipping creation."
else
    info "Creating virtual environment at ./${VENV_DIR} …"
    $PYTHON_BIN -m venv "$VENV_DIR"
fi

# ── Activate ──────────────────────────────────────────────────────────────────
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

# ── Upgrade pip ───────────────────────────────────────────────────────────────
info "Upgrading pip …"
pip install --quiet --upgrade pip

# ── Install dependencies ──────────────────────────────────────────────────────
info "Installing project dependencies from requirements.txt …"
pip install --quiet -r requirements.txt

# ── Copy .env if needed ───────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    warn "Created .env from .env.example – please review and update values before running tests."
fi

# ── Pre-download sentence-transformer model ───────────────────────────────────
info "Pre-downloading sentence-transformer model (first-time setup, ~120 MB) …"
MODEL=$(grep -E '^SENTENCE_MODEL=' .env 2>/dev/null | cut -d= -f2 || echo "paraphrase-multilingual-MiniLM-L12-v2")
python3 - <<PYEOF
from sentence_transformers import SentenceTransformer
import sys
model_name = "${MODEL}"
print(f"  Downloading: {model_name}")
try:
    SentenceTransformer(model_name)
    print(f"  Model ready ✓")
except Exception as e:
    print(f"  Warning: could not pre-download model – {e}", file=sys.stderr)
PYEOF

# ── Allure CLI check ──────────────────────────────────────────────────────────
info "Checking Allure CLI …"
if command -v allure &>/dev/null; then
    ALLURE_VER=$(allure --version 2>&1 | head -1)
    info "Allure CLI found: ${ALLURE_VER} ✓"
else
    warn "Allure CLI not found. To generate HTML reports install it:"
    warn "  macOS:  brew install allure"
    warn "  Linux:  https://docs.qameta.io/allure/#_linux"
fi

# ── Create report directories ─────────────────────────────────────────────────
mkdir -p reports/allure-results reports/screenshots

echo ""
info "Setup complete! To run the tests:"
echo "  source venv/bin/activate"
echo "  make test"
echo ""
info "To run a specific suite:"
echo "  make test-smoke      # Smoke tests"
echo "  make test-security   # Security injection tests"
echo "  make test-ar         # Arabic-language tests"
echo "  make report          # Generate Allure HTML report"
