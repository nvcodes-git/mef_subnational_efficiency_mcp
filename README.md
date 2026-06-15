# MEF Subnational Efficiency Analytics

A production-grade **Local Multi-Agent Analytics Pipeline** for auditing Peruvian public expenditure. Built with Claude Code Skills and the Model Context Protocol (MCP), it interfaces with `datosabiertos.gob.pe` to process 2025 subnational budget data and digitises the 1964 *Cuenta General de la República* via PaddleOCR.

---

## Architecture Overview

```
Claude Code CLI
      │
      ├─── executor_skill  ──► MCP Server (10 tools)
      │                              │
      │                     ┌────────┴────────┐
      │                     │                 │
      │               datosabiertos      Google Books
      │               .gob.pe API        1964 PDF
      │                     │                 │
      │              data_pipeline.py   ocr_engine.py
      │              (chunk streaming)  (PaddleOCR)
      │                     │                 │
      │              data/processed/    data/processed/
      │              entity_summary     ocr_1964.json
      │              .parquet
      │
      └─── evaluator_skill ──► Cross-validates aggregations
                               Optimises app.py
                               Writes audit report
                                      │
                               app.py (Streamlit)
                               4-tab dashboard
```

### Anti-Context Flooding Strategy (Critical Rule 1)
Raw SIAF datasets exceed 200MB–1GB. The pipeline **never** loads these into any LLM context window:
1. `inspeccionar_esquema_csv` reads only the first 512 KB to map columns and types.
2. `data_pipeline.py` runs as an isolated subprocess, streams the CSV in 50K-row chunks, filters, aggregates, and saves a micro Parquet file to `data/processed/`.
3. The Streamlit app reads **only** the processed Parquet artefacts.

### Period-Driven CLI Updates (Critical Rule 2)
The system is not hardcoded to any date. Trigger a full pipeline refresh for any period:
```bash
claude "run executor_skill for period 2025-12"
claude "execute mef_update for 2025-Q4"
```

---

## Repository Structure

```
mef_subnational_efficiency_mcp/
│
├── app.py                        # 4-tab Streamlit dashboard
├── README.md                     # This file
├── requirements.txt              # Python dependencies
│
├── .claude/skills/
│   ├── executor_skill.json       # Data engineering & app composition agent
│   └── evaluator_skill.json     # QA auditor & UX optimiser agent
│
├── src/
│   ├── mcp_server.py             # Local MCP server (10 tools)
│   ├── data_pipeline.py          # Anti-flooding SIAF processor
│   ├── ocr_engine.py             # PaddleOCR engine (15+ pages, 1964 doc)
│   ├── analytical_engine.py      # KPI computation for the Streamlit app
│   └── utils.py                  # Logging, constants, formatters
│
├── data/
│   ├── raw_pdfs/                 # 1964 PDF (manual download required)
│   ├── snapshots/                # Schema inspection results
│   └── processed/                # Parquet artefacts + OCR JSON + audit report
│
└── video/
    └── link.txt                  # 5-minute presentation video URL
```

---

## Prerequisites

### System dependencies
```bash
# Linux — required by pdf2image for PDF-to-image conversion
sudo apt-get install -y poppler-utils
```

### Python environment
Python **3.10 or 3.11** is recommended. PaddlePaddle 3.x has a known MKL incompatibility with Python 3.13 on some Linux systems.

```bash
# Create a dedicated environment (optional but recommended)
conda create -n mef python=3.11
conda activate mef
```

### Install dependencies
```bash
pip install -r requirements.txt
```

> **Note:** `paddleocr` and `paddlepaddle` are large packages (~500 MB total including model files downloaded on first run). Allow several minutes on first execution.

---

## Setup

### 1. Download the 1964 historical PDF
The Google Books download is blocked for automated requests. Download it manually:

1. Open in your browser: `https://books.google.com.pe/books/download/Cuenta_general.pdf?id=9YkbAQAAMAAJ`
2. Save the file as `data/raw_pdfs/cuenta_general_1964.pdf`

### 2. Generate processed data

**Option A — Synthetic data (no internet required):**
```bash
python src/data_pipeline.py
python src/ocr_engine.py --start 1 --end 15
```

**Option B — Live SIAF data from datosabiertos.gob.pe:**
```bash
# Start the MCP server first
python src/mcp_server.py &

# Then trigger the executor skill via Claude Code CLI
claude "run executor_skill for period 2025-12"
```

### 3. Launch the dashboard
```bash
streamlit run app.py
```

---

## CLI Period Updates

The pipeline accepts any period string. Examples:

| Command | Effect |
|---|---|
| `claude "run executor_skill for period 2025"` | Full year 2025 |
| `claude "run executor_skill for period 2025-12"` | December 2025 |
| `claude "execute mef_update for 2025-Q4"` | Q4 2025 |

You can also trigger the pipeline directly without the CLI:
```bash
python src/data_pipeline.py --period 2025-12 --nivel GL
```

---

## Streamlit Dashboard Tabs

| Tab | Content | Data Source |
|---|---|---|
| **1 — Executive Summary** | 2025 national KPIs + AI advisor narrative + 1964 OCR historical section (2 charts) | Both eras — independent sections |
| **2 — Territorial Distribution** | Execution rate by department, risk categories, PIM vs Devengado scatter | 2025 only |
| **3 — Hall of Shame** | Worst executing entities (PIM > 10M, Avance < 60%), frozen capital | 2025 only |
| **4 — Audit Log & Playground** | Evaluator quality report + live period re-run interface + architecture table | 2025 only |

---

## MCP Server Tools

Start the server with `python src/mcp_server.py`, then configure Claude Code to use it.

| Tool | Purpose |
|---|---|
| `buscar_datasets` | Keyword search on datosabiertos.gob.pe CKAN API |
| `obtener_detalle_dataset` | Extract resource download URLs by dataset ID |
| `descargar_documento_1964` | Download the 1964 PDF from Google Books |
| `listar_entidades_publicas` | List active public ministries and municipalities |
| `listar_categorias_tematicas` | Map thematic groups on the portal |
| `obtener_ultimas_actualizaciones` | Feed recently updated datasets |
| `inspeccionar_esquema_csv` | Snapshot first 512 KB of a CSV — schema only, no full download |
| `consultar_datastore_filtrado` | SQL-style queries on portal datastore |
| `procesar_ocr_paginas_1964` | Trigger PaddleOCR subprocess on 15+ pages of the 1964 document |
| `descargar_y_analizar_estadisticas` | Trigger data_pipeline.py subprocess for a given period |

---

## Analytical Metrics

### 2025 Modern Track
$$\text{Avance} = \left(\frac{\text{Devengado}}{\text{PIM}}\right) \times 100$$

$$\text{Saldo No Devengado} = \text{PIM} - \text{Devengado}$$

Entities are flagged as:
- **Critical** — Avance < 40% with PIM > S/ 10M
- **Low** — Avance 40–60% with PIM > S/ 10M

### 1964 Historical Track
Descriptive summaries extracted from 15+ PaddleOCR-processed pages:
- Revenue categories in Libras Peruanas (the currency of the era)
- Expenditure by ministry
- Deficit/surplus balance

---

## Known Limitations

| Issue | Workaround |
|---|---|
| PaddleOCR crashes on Python 3.13 + MKL | Use Python 3.10/3.11 environment |
| Google Books PDF download blocked for bots | Manual browser download (one-time) |
| `datosabiertos.gob.pe` API may throttle | Synthetic data fallback auto-activates |
| No choropleth map (department boundaries) | Add `geopandas` + Peru GeoJSON for v2 |

---

## Dual-Skill Cooperation

### Executor Skill (`executor_skill.json`)
Acts as the core worker: discovers datasets via MCP, triggers local subprocess pipelines, runs OCR, and writes the initial Streamlit draft. Never loads raw data into context.

### Evaluator Skill (`evaluator_skill.json`)
Acts as the perfectionist auditor: independently re-samples raw data, cross-verifies aggregations, enforces `@st.cache_data` performance, polishes UI/UX, and writes the structured quality diff report visible in Tab 4.
