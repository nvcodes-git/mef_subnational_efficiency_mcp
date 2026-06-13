"""
Local MCP Server — MEF Subnational Efficiency Analytics
Exposes 10 tools for interacting with datosabiertos.gob.pe and the
1964 historical fiscal archive via PaddleOCR.

Run with:
    python src/mcp_server.py
"""

import json
import subprocess
import sys
from pathlib import Path

import requests
from fastmcp import FastMCP

from src.utils import (
    CKAN_BASE,
    GOOGLE_BOOKS_PDF_1964,
    PDF_1964_LOCAL,
    PROCESSED_DIR,
    SNAPSHOTS_DIR,
    ensure_dirs,
    get_logger,
)

log = get_logger("mcp_server")
mcp = FastMCP("mef-analytics-server")

_REQUEST_TIMEOUT = 30  # seconds


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _ckan_get(action: str, params: dict) -> dict:
    url = f"{CKAN_BASE}/{action}"
    resp = requests.get(url, params=params, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Tool 1 — Search datasets
# ---------------------------------------------------------------------------
@mcp.tool()
def buscar_datasets(query: str, rows: int = 5) -> str:
    """Search datasets on datosabiertos.gob.pe using keyword strings.

    Args:
        query: Keyword string (e.g. 'ejecucion presupuestal 2025 SIAF').
        rows:  Maximum number of results to return (default 5).
    """
    try:
        data = _ckan_get("package_search", {"q": query, "rows": rows})
        results = data.get("result", {}).get("results", [])
        if not results:
            return json.dumps({"status": "no_results", "query": query})
        summary = [
            {"id": r["id"], "name": r["name"], "title": r.get("title", ""),
             "notes": r.get("notes", "")[:200]}
            for r in results
        ]
        return json.dumps({"status": "ok", "count": len(summary), "datasets": summary},
                          ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("buscar_datasets failed: %s", exc)
        return json.dumps({"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Tool 2 — Get dataset detail + resource download URLs
# ---------------------------------------------------------------------------
@mcp.tool()
def obtener_detalle_dataset(dataset_id: str) -> str:
    """Extract direct download URLs for data resources via dataset ID.

    Args:
        dataset_id: The CKAN dataset ID returned by buscar_datasets.
    """
    try:
        data = _ckan_get("package_show", {"id": dataset_id})
        pkg = data.get("result", {})
        resources = [
            {"id": r["id"], "name": r.get("name", ""),
             "format": r.get("format", ""), "url": r.get("url", "")}
            for r in pkg.get("resources", [])
        ]
        return json.dumps(
            {"status": "ok", "title": pkg.get("title", ""), "resources": resources},
            ensure_ascii=False, indent=2,
        )
    except Exception as exc:
        log.error("obtener_detalle_dataset failed: %s", exc)
        return json.dumps({"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Tool 3 — Download the 1964 historical PDF
# ---------------------------------------------------------------------------
@mcp.tool()
def descargar_documento_1964() -> str:
    """Download the 1964 Cuenta General de la República PDF into data/raw_pdfs/.

    Uses the Google Books public-domain download link. Skips if already present.
    """
    ensure_dirs()
    if PDF_1964_LOCAL.exists():
        return json.dumps({"status": "already_present", "path": str(PDF_1964_LOCAL)})
    try:
        log.info("Downloading 1964 document from Google Books …")
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(GOOGLE_BOOKS_PDF_1964, headers=headers,
                            timeout=120, stream=True)
        resp.raise_for_status()
        with open(PDF_1964_LOCAL, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)
        size_mb = PDF_1964_LOCAL.stat().st_size / 1_048_576
        return json.dumps({"status": "downloaded", "path": str(PDF_1964_LOCAL),
                           "size_mb": round(size_mb, 2)})
    except Exception as exc:
        log.error("descargar_documento_1964 failed: %s", exc)
        return json.dumps({"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Tool 4 — List active public entities
# ---------------------------------------------------------------------------
@mcp.tool()
def listar_entidades_publicas(query: str = "entidades publicas peru") -> str:
    """Fetch lists of active public ministries and regional/municipal entities.

    Args:
        query: Search term to narrow the entity list (default generic search).
    """
    return buscar_datasets(query, rows=10)


# ---------------------------------------------------------------------------
# Tool 5 — List thematic categories
# ---------------------------------------------------------------------------
@mcp.tool()
def listar_categorias_tematicas() -> str:
    """Map high-level data groups (groups/categories) available on the portal."""
    try:
        data = _ckan_get("group_list", {"all_fields": True})
        groups = [
            {"name": g["name"], "display_name": g.get("display_name", ""),
             "package_count": g.get("package_count", 0)}
            for g in data.get("result", [])
        ]
        return json.dumps({"status": "ok", "groups": groups},
                          ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Tool 6 — Latest updates feed
# ---------------------------------------------------------------------------
@mcp.tool()
def obtener_ultimas_actualizaciones(rows: int = 10) -> str:
    """Feed chronological changes or recently added data blocks to the agent.

    Args:
        rows: Number of recently updated datasets to return.
    """
    try:
        data = _ckan_get("package_search",
                         {"sort": "metadata_modified desc", "rows": rows})
        results = data.get("result", {}).get("results", [])
        items = [
            {"id": r["id"], "title": r.get("title", ""),
             "modified": r.get("metadata_modified", "")}
            for r in results
        ]
        return json.dumps({"status": "ok", "items": items},
                          ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Tool 7 — Inspect CSV schema (snapshot, no full download)
# ---------------------------------------------------------------------------
@mcp.tool()
def inspeccionar_esquema_csv(resource_url: str, n_rows: int = 10) -> str:
    """Open a partial stream of a CSV resource to capture headers and sample rows.

    CRITICAL: This tool never downloads the full file — it reads only the first
    n_rows to map column names and dtypes, preventing context window flooding.

    Args:
        resource_url: Direct CSV download URL obtained from obtener_detalle_dataset.
        n_rows:       Number of sample rows to capture (default 10, max 20).
    """
    import io
    import pandas as pd

    n_rows = min(n_rows, 20)
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Range": "bytes=0-524288"}  # first 512 KB
        resp = requests.get(resource_url, headers=headers,
                            timeout=_REQUEST_TIMEOUT, stream=True)
        content = b""
        for chunk in resp.iter_content(chunk_size=65536):
            content += chunk
            if len(content) >= 524288:
                break

        df = pd.read_csv(io.BytesIO(content), nrows=n_rows,
                         encoding="utf-8", on_bad_lines="skip")
        schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
        sample = df.head(n_rows).to_dict(orient="records")

        snapshot = {"columns": schema, "sample_rows": sample}
        snap_path = SNAPSHOTS_DIR / "latest_schema.json"
        ensure_dirs()
        with open(snap_path, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, ensure_ascii=False, indent=2, default=str)

        return json.dumps({"status": "ok", "n_columns": len(schema),
                           "columns": list(schema.keys()),
                           "dtypes": schema,
                           "snapshot_saved": str(snap_path)},
                          ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("inspeccionar_esquema_csv failed: %s", exc)
        return json.dumps({"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Tool 8 — Filtered datastore query
# ---------------------------------------------------------------------------
@mcp.tool()
def consultar_datastore_filtrado(resource_id: str, filters: str = "",
                                 limit: int = 100) -> str:
    """Perform SQL-like queries on the portal's datastore when available.

    Args:
        resource_id: CKAN resource ID (UUID).
        filters:     JSON string of filter key/value pairs, e.g. '{"nivel_gobierno":"G"}'.
        limit:       Max rows to return (default 100).
    """
    try:
        params: dict = {"resource_id": resource_id, "limit": limit}
        if filters:
            params["filters"] = filters
        data = _ckan_get("datastore_search", params)
        records = data.get("result", {}).get("records", [])
        fields = data.get("result", {}).get("fields", [])
        return json.dumps({"status": "ok", "n_records": len(records),
                           "fields": [f["id"] for f in fields],
                           "records": records[:limit]},
                          ensure_ascii=False, indent=2, default=str)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Tool 9 — Trigger PaddleOCR on 15+ pages of the 1964 document
# ---------------------------------------------------------------------------
@mcp.tool()
def procesar_ocr_paginas_1964(start_page: int = 1, end_page: int = 20) -> str:
    """Trigger local PaddleOCR routines over selected pages of the 1964 document.

    Calls src/ocr_engine.py as a subprocess so the heavy OCR work stays out of
    the MCP context window. Results are saved to data/processed/ocr_1964.json.

    Args:
        start_page: First page to process (1-indexed, default 1).
        end_page:   Last page to process (inclusive, default 20 — covers 15+ pages).
    """
    if not PDF_1964_LOCAL.exists():
        return json.dumps({
            "status": "error",
            "message": "1964 PDF not found. Run descargar_documento_1964 first.",
        })
    ocr_script = Path(__file__).parent / "ocr_engine.py"
    try:
        result = subprocess.run(
            [sys.executable, str(ocr_script),
             "--start", str(start_page), "--end", str(end_page)],
            capture_output=True, text=True, timeout=600,
        )
        output_path = PROCESSED_DIR / "ocr_1964.json"
        if result.returncode == 0 and output_path.exists():
            return json.dumps({"status": "ok",
                               "output": str(output_path),
                               "stdout_tail": result.stdout[-500:]})
        return json.dumps({"status": "error",
                           "returncode": result.returncode,
                           "stderr": result.stderr[-500:]})
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "error", "message": "OCR subprocess timed out."})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Tool 10 — Download, filter, and summarise budget statistics
# ---------------------------------------------------------------------------
@mcp.tool()
def descargar_y_analizar_estadisticas(resource_url: str, period: str = "2025",
                                      nivel_gobierno: str = "GL") -> str:
    """Run light local aggregations and feed descriptive summaries back to the agent.

    Calls src/data_pipeline.py as a subprocess to avoid flooding the context
    with large CSVs. Results are saved to data/processed/.

    Args:
        resource_url:    Direct CSV download URL for the SIAF budget dataset.
        period:          Fiscal period string (e.g. '2025', '2025-12', '2025-Q4').
        nivel_gobierno:  Filter code: 'G' (Regional), 'L' (Local), 'GL' (both).
    """
    pipeline_script = Path(__file__).parent / "data_pipeline.py"
    try:
        result = subprocess.run(
            [sys.executable, str(pipeline_script),
             "--url", resource_url,
             "--period", period,
             "--nivel", nivel_gobierno],
            capture_output=True, text=True, timeout=300,
        )
        summary_path = PROCESSED_DIR / "siaf_summary.json"
        if result.returncode == 0 and summary_path.exists():
            with open(summary_path, encoding="utf-8") as fh:
                summary = json.load(fh)
            return json.dumps({"status": "ok", "summary": summary},
                              ensure_ascii=False, indent=2)
        return json.dumps({"status": "error",
                           "returncode": result.returncode,
                           "stderr": result.stderr[-500:]})
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "error", "message": "Pipeline subprocess timed out."})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ensure_dirs()
    log.info("Starting MEF Analytics MCP server …")
    mcp.run()
