"""
Analytical Engine — Core metric computation and data grouping for the Streamlit app.

Reads from data/processed/ Parquet artefacts (never from raw CSVs).
All functions return plain DataFrames or dicts — no Streamlit imports here.
"""

import json
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import (
    CRITICAL_EXECUTION_THRESHOLD,
    LOW_EXECUTION_THRESHOLD,
    MIN_PIM_SOLES,
    PROCESSED_DIR,
    get_logger,
    fmt_soles,
    fmt_pct,
)

log = get_logger("analytical_engine")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def load_entity_summary() -> pd.DataFrame:
    path = PROCESSED_DIR / "entity_summary.parquet"
    if not path.exists():
        log.warning("entity_summary.parquet not found — running synthetic pipeline.")
        _run_synthetic_pipeline()
    return pd.read_parquet(path)


def load_dept_summary() -> pd.DataFrame:
    path = PROCESSED_DIR / "dept_summary.parquet"
    if not path.exists():
        _run_synthetic_pipeline()
    return pd.read_parquet(path)


def load_siaf_summary() -> dict:
    path = PROCESSED_DIR / "siaf_summary.json"
    if not path.exists():
        _run_synthetic_pipeline()
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_ocr_results() -> dict:
    path = PROCESSED_DIR / "ocr_1964.json"
    if not path.exists():
        return _synthetic_ocr_results()
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _run_synthetic_pipeline():
    """Bootstrap processed files using the synthetic data fallback."""
    import subprocess, sys as _sys
    pipeline = Path(__file__).parent / "data_pipeline.py"
    subprocess.run([_sys.executable, str(pipeline)], check=False)


# ---------------------------------------------------------------------------
# 2025 KPI helpers
# ---------------------------------------------------------------------------
def get_national_kpis() -> dict:
    """Return top-level 2025 national KPI values for Tab 1 metric blocks."""
    s = load_siaf_summary()
    return {
        "total_pim": s.get("total_pim", 0),
        "total_devengado": s.get("total_devengado", 0),
        "national_execution_rate_pct": s.get("national_execution_rate_pct", 0),
        "frozen_capital": s.get("frozen_capital", 0),
        "n_entities_total": s.get("n_entities_total", 0),
        "n_entities_low_execution": s.get("n_entities_low_execution", 0),
        "n_entities_critical": s.get("n_entities_critical", 0),
        "period": s.get("period", "2025"),
        "total_pim_fmt": fmt_soles(s.get("total_pim", 0)),
        "total_devengado_fmt": fmt_soles(s.get("total_devengado", 0)),
        "frozen_capital_fmt": fmt_soles(s.get("frozen_capital", 0)),
        "national_rate_fmt": fmt_pct(s.get("national_execution_rate_pct", 0)),
    }


# ---------------------------------------------------------------------------
# Tab 2 — Territorial / department-level data
# ---------------------------------------------------------------------------
def get_dept_execution() -> pd.DataFrame:
    """Department-level PIM, Devengado, and Avance% — used for maps and heatmaps."""
    df = load_dept_summary()
    if "avance_pct" not in df.columns:
        pim_col = _find_col(df, ["pim_total", "monto_pim"])
        dev_col = _find_col(df, ["devengado_total", "monto_devengado"])
        if pim_col and dev_col:
            df["avance_pct"] = (df[dev_col] / df[pim_col].replace(0, float("nan"))) * 100
    df["risk_category"] = df["avance_pct"].apply(_risk_label)
    return df.sort_values("avance_pct")


def _risk_label(pct: float) -> str:
    if pd.isna(pct) or pct < CRITICAL_EXECUTION_THRESHOLD:
        return "Crítico"
    if pct < LOW_EXECUTION_THRESHOLD:
        return "Bajo"
    if pct < 80:
        return "Moderado"
    return "Adecuado"


# ---------------------------------------------------------------------------
# Tab 3 — Hall of Shame: worst-performing entities
# ---------------------------------------------------------------------------
def get_hall_of_shame(top_n: int = 30) -> pd.DataFrame:
    """Entities with PIM > 10M PEN and the lowest execution rates."""
    df = load_entity_summary()

    pim_col = _find_col(df, ["pim_total", "monto_pim"])
    dev_col = _find_col(df, ["devengado_total", "monto_devengado"])

    if pim_col:
        df = df[df[pim_col] >= MIN_PIM_SOLES].copy()
    if "avance_pct" not in df.columns and pim_col and dev_col:
        df["avance_pct"] = (df[dev_col] / df[pim_col].replace(0, float("nan"))) * 100
    if "saldo_no_devengado" not in df.columns and pim_col and dev_col:
        df["saldo_no_devengado"] = df[pim_col] - df[dev_col]

    df["risk_category"] = df["avance_pct"].apply(_risk_label)
    df["pim_fmt"] = df[pim_col].apply(fmt_soles) if pim_col else ""
    df["devengado_fmt"] = df[dev_col].apply(fmt_soles) if dev_col else ""
    df["saldo_fmt"] = df["saldo_no_devengado"].apply(fmt_soles)
    df["avance_fmt"] = df["avance_pct"].apply(fmt_pct)

    return (
        df[df["avance_pct"] < LOW_EXECUTION_THRESHOLD]
        .sort_values("avance_pct")
        .head(top_n)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# 1964 historical helpers
# ---------------------------------------------------------------------------
def get_historical_summary() -> dict:
    """Parse OCR results into structured conclusions for Tab 1."""
    ocr = load_ocr_results()
    return {
        "pages_processed": ocr.get("pages_processed", 0),
        "text_blocks": ocr.get("text_blocks", []),
        "revenue_categories": ocr.get("revenue_categories", []),
        "expenditure_categories": ocr.get("expenditure_categories", []),
        "totals": ocr.get("totals", {}),
        "source": ocr.get("source", "synthetic"),
    }


# ---------------------------------------------------------------------------
# Synthetic OCR fallback
# ---------------------------------------------------------------------------
def _synthetic_ocr_results() -> dict:
    """Realistic representative data from the 1964 Cuenta General de la República."""
    return {
        "pages_processed": 15,
        "source": "synthetic_representative",
        "text_blocks": [
            "REPÚBLICA DEL PERÚ — CUENTA GENERAL 1964",
            "MINISTERIO DE HACIENDA Y COMERCIO",
            "PRESUPUESTO GENERAL DE LA REPÚBLICA — AÑO FISCAL 1964",
        ],
        "revenue_categories": [
            {"categoria": "Renta de Aduanas",         "monto_soles": 1_842_300},
            {"categoria": "Contribuciones Directas",  "monto_soles":   987_450},
            {"categoria": "Contribuciones Indirectas","monto_soles": 1_234_670},
            {"categoria": "Renta de Correos",         "monto_soles":   123_800},
            {"categoria": "Renta de Ferrocarriles",   "monto_soles":   345_900},
            {"categoria": "Fondos de Reserva",        "monto_soles":   456_200},
            {"categoria": "Empréstitos Internos",     "monto_soles":   678_100},
            {"categoria": "Otros Ingresos",           "monto_soles":   234_500},
        ],
        "expenditure_categories": [
            {"ministerio": "Ministerio de Guerra",          "monto_soles": 1_230_000},
            {"ministerio": "Ministerio de Fomento",         "monto_soles":   980_000},
            {"ministerio": "Ministerio de Educación",       "monto_soles": 1_560_000},
            {"ministerio": "Ministerio de Salud",           "monto_soles":   420_000},
            {"ministerio": "Ministerio de Hacienda",        "monto_soles":   310_000},
            {"ministerio": "Ministerio de Relaciones Ext.", "monto_soles":   215_000},
            {"ministerio": "Ministerio del Interior",       "monto_soles":   480_000},
            {"ministerio": "Poder Judicial",                "monto_soles":   175_000},
            {"ministerio": "Congreso de la República",      "monto_soles":   145_000},
            {"ministerio": "Otros Organismos",              "monto_soles":   388_000},
        ],
        "totals": {
            "total_ingresos_soles":    5_902_920,
            "total_egresos_soles":     5_903_000,
            "superavit_deficit_soles":      -80,
            "currency_note": "Soles de Oro (S/O) — moneda vigente en 1964",
        },
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None
