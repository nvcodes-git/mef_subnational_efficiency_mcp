"""Shared helpers, logging setup, and project-wide constants."""

import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_PDF_DIR = DATA_DIR / "raw_pdfs"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
PROCESSED_DIR = DATA_DIR / "processed"

# ---------------------------------------------------------------------------
# External endpoints
# ---------------------------------------------------------------------------
CKAN_BASE = "https://datosabiertos.gob.pe/api/3/action"
PORTAL_BASE = "https://datosabiertos.gob.pe"
GOOGLE_BOOKS_PDF_1964 = (
    "https://books.google.com.pe/books/download/Cuenta_general.pdf"
    "?id=9YkbAQAAMAAJ"
)
PDF_1964_LOCAL = RAW_PDF_DIR / "cuenta_general_1964.pdf"

# ---------------------------------------------------------------------------
# Budget thresholds
# ---------------------------------------------------------------------------
MIN_PIM_SOLES = 10_000_000          # 10 million PEN
LOW_EXECUTION_THRESHOLD = 60.0      # % — below this = frozen capital zone
CRITICAL_EXECUTION_THRESHOLD = 40.0 # % — below this = severe under-execution

# Government-level codes used in SIAF datasets
SUBNATIONAL_LEVELS = {"G": "Gobierno Regional", "L": "Gobierno Local"}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_LOG_DATE = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def fmt_soles(value: float) -> str:
    """Return a human-readable PEN amount string."""
    if abs(value) >= 1_000_000_000:
        return f"S/ {value / 1_000_000_000:.2f} B"
    if abs(value) >= 1_000_000:
        return f"S/ {value / 1_000_000:.2f} M"
    return f"S/ {value:,.0f}"


def fmt_pct(value: float) -> str:
    return f"{value:.1f}%"


def ensure_dirs() -> None:
    """Create all required data subdirectories if they don't exist."""
    for d in (RAW_PDF_DIR, SNAPSHOTS_DIR, PROCESSED_DIR):
        d.mkdir(parents=True, exist_ok=True)
