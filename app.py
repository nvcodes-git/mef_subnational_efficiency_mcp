"""
MEF Subnational Efficiency Analytics — 4-Tab Streamlit Dashboard

Tab 1: Executive Macro Summary & Dual-Era Opening Dashboard (2025 + 1964)
Tab 2: Territorial Distribution & Geospatial Analysis (2025)
Tab 3: Budget "Hall of Shame" & Anomaly Explorer (2025)
Tab 4: Multi-Agent Audit Log & Live Period Playground (2025)
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.analytical_engine import (
    get_dept_execution,
    get_hall_of_shame,
    get_historical_summary,
    get_national_kpis,
)
from src.utils import PROCESSED_DIR, fmt_soles, fmt_pct

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="MEF Subnational Efficiency Analytics",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f1117; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e2130, #252840);
        border: 1px solid #3a3f5c;
        border-radius: 12px;
        padding: 16px;
    }
    [data-testid="metric-container"] label {
        color: #8b9bb4 !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #e8eaf6 !important;
        font-size: 1.6rem !important;
        font-weight: 700;
    }

    /* Tab headers */
    .stTabs [data-baseweb="tab"] {
        font-size: 0.9rem;
        font-weight: 600;
        color: #8b9bb4;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        color: #7986cb !important;
        border-bottom: 3px solid #7986cb !important;
    }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #7986cb;
        border-left: 4px solid #7986cb;
        padding-left: 10px;
        margin: 20px 0 12px 0;
    }

    /* Era divider */
    .era-divider {
        border: none;
        border-top: 2px dashed #3a3f5c;
        margin: 32px 0;
    }

    /* AI narrative box */
    .ai-narrative {
        background: linear-gradient(135deg, #1a1f35, #1e2540);
        border: 1px solid #3d5a80;
        border-radius: 10px;
        padding: 18px 22px;
        color: #c5cae9;
        font-size: 0.92rem;
        line-height: 1.7;
        margin: 12px 0;
    }

    /* Historical box */
    .historical-box {
        background: linear-gradient(135deg, #1a2510, #1e2f14);
        border: 1px solid #4a6741;
        border-radius: 10px;
        padding: 18px 22px;
        color: #c8e6c9;
        font-size: 0.88rem;
        line-height: 1.7;
        margin: 12px 0;
    }

    /* Shame badge */
    .badge-critical { color: #ef5350; font-weight: 700; }
    .badge-low      { color: #ffa726; font-weight: 700; }
    .badge-ok       { color: #66bb6a; font-weight: 700; }

    /* Audit log */
    .audit-entry {
        background: #1a1f35;
        border-left: 4px solid #7986cb;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.85rem;
        color: #c5cae9;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Cached data loaders
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def cached_kpis() -> dict:
    return get_national_kpis()


@st.cache_data(ttl=300)
def cached_dept() -> pd.DataFrame:
    return get_dept_execution()


@st.cache_data(ttl=300)
def cached_shame(top_n: int = 30) -> pd.DataFrame:
    return get_hall_of_shame(top_n)


@st.cache_data(ttl=300)
def cached_historical() -> dict:
    return get_historical_summary()


@st.cache_data(ttl=300)
def load_audit_report() -> str:
    path = PROCESSED_DIR / "evaluator_audit_report.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "_Audit report not yet generated. Run the Evaluator Skill first._"


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("# 🏛️ MEF Subnational Efficiency Analytics")
st.markdown(
    "**Fiscal Transparency & Budget Execution Intelligence Platform** · "
    "Perú 2025 · powered by Claude Code Multi-Agent Architecture"
)
st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Executive Summary",
    "🗺️ Territorial Distribution",
    "🚨 Hall of Shame",
    "🤖 Audit Log & Playground",
])


# ===========================================================================
# TAB 1 — Executive Macro Summary & Dual-Era Opening Dashboard
# ===========================================================================
with tab1:
    kpis = cached_kpis()
    hist = cached_historical()

    # ---- 2025 Section ----
    st.markdown('<div class="section-header">🇵🇪 Modern Fiscal Period — 2025</div>',
                unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total PIM 2025", kpis["total_pim_fmt"],
              help="Presupuesto Institucional Modificado — total modified appropriation")
    c2.metric("Total Devengado", kpis["total_devengado_fmt"],
              help="Funds formally committed and spent")
    c3.metric("National Execution Rate", kpis["national_rate_fmt"],
              delta=f"{kpis['national_execution_rate_pct'] - 70:.1f}% vs 70% target")
    c4.metric("Frozen Capital", kpis["frozen_capital_fmt"],
              help="Saldo No Devengado — unspent appropriation")

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Entities Analysed", f"{kpis['n_entities_total']:,}")
    with col_b:
        st.metric("⚠️ Low Execution (<60%)", f"{kpis['n_entities_low_execution']:,}",
                  delta=f"{kpis['n_entities_critical']} critical (<40%)",
                  delta_color="inverse")

    st.markdown('<div class="ai-narrative">'
                '<b>🤖 AI Fiscal Advisor — 2025 Bottleneck Analysis</b><br><br>'
                f"As of fiscal period <b>{kpis['period']}</b>, Peru's subnational governments "
                f"have executed only <b>{kpis['national_rate_fmt']}</b> of their combined budget, "
                f"leaving <b>{kpis['frozen_capital_fmt']}</b> in unspent appropriations — "
                "a structural bottleneck driven by three converging factors: "
                "<b>(1)</b> procurement process delays at the municipal level, "
                "<b>(2)</b> insufficient technical capacity in smaller regional executing units, "
                "and <b>(3)</b> chronic late-year budget modifications (PIM adjustments) that "
                "compress the effective execution window. "
                f"<b>{kpis['n_entities_critical']}</b> entities with budgets exceeding S/ 10M "
                "are executing below the 40% critical threshold — these represent the highest "
                "transparency risk and are highlighted in Tab 3."
                "</div>", unsafe_allow_html=True)

    st.markdown('<hr class="era-divider">', unsafe_allow_html=True)

    # ---- 1964 Historical Section ----
    st.markdown('<div class="section-header">📜 Historical Archive — Fiscal Year 1964</div>',
                unsafe_allow_html=True)

    st.markdown(
        f'<div class="historical-box">'
        f'<b>📄 OCR Source:</b> Ministerio de Hacienda y Comercio — '
        f'Cuenta General de la República 1964<br>'
        f'<b>Pages Processed:</b> {hist["pages_processed"]} pages via PaddleOCR<br>'
        f'<b>Currency:</b> Soles de Oro (S/O) — the monetary unit in use during 1964<br><br>'
        f'<b>Key Historical Findings:</b><br>'
        f'• The 1964 budget reflects a highly centralised fiscal structure — '
        f'the Ministry of Education alone absorbed the largest single expenditure block.<br>'
        f'• Customs revenue (Renta de Aduanas) was the dominant income source, '
        f'reflecting Peru\'s export-driven economy of the era.<br>'
        f'• The near-zero deficit (−80 S/O) indicates a formally balanced budget, '
        f'though off-budget expenditures were common in that period.<br>'
        f'• The absence of subnational government lines confirms the fully centralised '
        f'fiscal architecture that preceded the 1990s decentralisation reforms.'
        f'</div>',
        unsafe_allow_html=True,
    )

    h_col1, h_col2 = st.columns(2)

    with h_col1:
        st.markdown("**Revenue Structure — 1964 (Soles de Oro)**")
        rev = hist.get("revenue_categories", [])
        if rev:
            rev_df = pd.DataFrame(rev)
            fig_rev = px.bar(
                rev_df, x="monto_soles", y="categoria",
                orientation="h",
                color="monto_soles",
                color_continuous_scale="Greens",
                title="Ingresos por Categoría — 1964",
                labels={"monto_soles": "Soles de Oro (S/O)", "categoria": ""},
            )
            fig_rev.update_layout(
                plot_bgcolor="#1a1f35", paper_bgcolor="#1a1f35",
                font_color="#c5cae9", showlegend=False,
                coloraxis_showscale=False, height=380,
                margin=dict(l=10, r=10, t=40, b=10),
            )
            fig_rev.update_xaxes(gridcolor="#2a2f4a")
            fig_rev.update_yaxes(gridcolor="#2a2f4a")
            st.plotly_chart(fig_rev, use_container_width=True)

    with h_col2:
        st.markdown("**Expenditure by Ministry — 1964 (Soles de Oro)**")
        exp = hist.get("expenditure_categories", [])
        if exp:
            exp_df = pd.DataFrame(exp)
            fig_exp = px.pie(
                exp_df, values="monto_soles", names="ministerio",
                title="Distribución del Gasto por Ministerio — 1964",
                color_discrete_sequence=px.colors.sequential.Teal,
                hole=0.4,
            )
            fig_exp.update_layout(
                plot_bgcolor="#1a1f35", paper_bgcolor="#1a1f35",
                font_color="#c5cae9", height=380,
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(font=dict(size=10)),
            )
            st.plotly_chart(fig_exp, use_container_width=True)

    totals = hist.get("totals", {})
    if totals:
        t1, t2, t3 = st.columns(3)
        t1.metric("Total Ingresos 1964",
                  f"S/O {totals.get('TOTAL INGRESOS', totals.get('total_ingresos_soles', 0)):,.0f}")
        t2.metric("Total Egresos 1964",
                  f"S/O {totals.get('TOTAL EGRESOS', totals.get('total_egresos_soles', 0)):,.0f}")
        deficit = totals.get("superavit_deficit_soles", totals.get("DÉFICIT", totals.get("deficit", 0)))
        t3.metric("Déficit / Superávit",
                  f"S/O {deficit:,.0f}",
                  delta="Near-balanced budget",
                  delta_color="off")


# ===========================================================================
# TAB 2 — Territorial Distribution & Geospatial Analysis (2025 only)
# ===========================================================================
with tab2:
    st.markdown('<div class="section-header">🗺️ Territorial Budget Execution — 2025</div>',
                unsafe_allow_html=True)
    st.caption("Exclusively 2025 subnational data — Regional & Local Governments with PIM > S/ 10M")

    dept_df = cached_dept()

    dept_col = next((c for c in ["departamento", "region", "DEPARTAMENTO"] if c in dept_df.columns), None)
    pim_col  = next((c for c in ["pim_total", "monto_pim"] if c in dept_df.columns), None)
    dev_col  = next((c for c in ["devengado_total", "monto_devengado"] if c in dept_df.columns), None)

    if dept_col and "avance_pct" in dept_df.columns:
        # Execution rate bar chart by department
        fig_dept = px.bar(
            dept_df.sort_values("avance_pct"),
            x="avance_pct", y=dept_col,
            orientation="h",
            color="avance_pct",
            color_continuous_scale=[
                (0.0, "#ef5350"), (0.4, "#ffa726"),
                (0.6, "#ffee58"), (1.0, "#66bb6a"),
            ],
            range_color=[0, 100],
            title="Tasa de Ejecución Presupuestal por Departamento (Avance %)",
            labels={"avance_pct": "Avance (%)", dept_col: "Departamento"},
            text="avance_pct",
        )
        fig_dept.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_dept.add_vline(x=60, line_dash="dash", line_color="#ffa726",
                           annotation_text="60% threshold", annotation_font_color="#ffa726")
        fig_dept.add_vline(x=40, line_dash="dash", line_color="#ef5350",
                           annotation_text="40% critical", annotation_font_color="#ef5350")
        fig_dept.update_layout(
            plot_bgcolor="#1a1f35", paper_bgcolor="#0f1117",
            font_color="#c5cae9", height=700,
            coloraxis_showscale=False,
            margin=dict(l=10, r=60, t=60, b=10),
        )
        fig_dept.update_xaxes(gridcolor="#2a2f4a", range=[0, 110])
        fig_dept.update_yaxes(gridcolor="#2a2f4a")
        st.plotly_chart(fig_dept, use_container_width=True)

        # Risk category breakdown
        st.markdown('<div class="section-header">Risk Category Breakdown</div>',
                    unsafe_allow_html=True)

        if "risk_category" in dept_df.columns:
            risk_counts = dept_df["risk_category"].value_counts().reset_index()
            risk_counts.columns = ["category", "count"]
            color_map = {
                "Crítico": "#ef5350", "Bajo": "#ffa726",
                "Moderado": "#ffee58", "Adecuado": "#66bb6a",
            }
            fig_risk = px.bar(
                risk_counts, x="category", y="count",
                color="category", color_discrete_map=color_map,
                title="Departamentos por Categoría de Riesgo Fiscal",
                labels={"category": "Categoría", "count": "N° Departamentos"},
                text="count",
            )
            fig_risk.update_traces(textposition="outside")
            fig_risk.update_layout(
                plot_bgcolor="#1a1f35", paper_bgcolor="#0f1117",
                font_color="#c5cae9", showlegend=False, height=350,
                margin=dict(l=10, r=10, t=50, b=10),
            )
            fig_risk.update_yaxes(gridcolor="#2a2f4a")
            st.plotly_chart(fig_risk, use_container_width=True)

        # PIM vs Devengado scatter
        if pim_col and dev_col:
            st.markdown('<div class="section-header">PIM vs Devengado — Spending Gap Heatmap</div>',
                        unsafe_allow_html=True)
            fig_scatter = px.scatter(
                dept_df,
                x=pim_col, y=dev_col,
                color="avance_pct",
                size=pim_col,
                hover_name=dept_col,
                color_continuous_scale="RdYlGn",
                range_color=[0, 100],
                title="PIM vs Devengado por Departamento (tamaño = PIM)",
                labels={pim_col: "PIM (S/)", dev_col: "Devengado (S/)",
                        "avance_pct": "Avance %"},
            )
            fig_scatter.update_layout(
                plot_bgcolor="#1a1f35", paper_bgcolor="#0f1117",
                font_color="#c5cae9", height=450,
                margin=dict(l=10, r=10, t=50, b=10),
            )
            fig_scatter.update_xaxes(gridcolor="#2a2f4a")
            fig_scatter.update_yaxes(gridcolor="#2a2f4a")
            st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Run the executor pipeline to load territorial data.")


# ===========================================================================
# TAB 3 — Budget "Hall of Shame" & Anomaly Explorer (2025 only)
# ===========================================================================
with tab3:
    st.markdown('<div class="section-header">🚨 Budget Hall of Shame — Worst Executing Units 2025</div>',
                unsafe_allow_html=True)
    st.caption("Subnational entities with PIM > S/ 10M and execution rate below 60% · Exclusively 2025")

    top_n = st.slider("Show top N worst performers", min_value=10, max_value=50,
                      value=20, step=5)

    shame_df = cached_shame(top_n)

    if not shame_df.empty:
        # Summary metrics
        s1, s2, s3 = st.columns(3)
        pim_col_s = next((c for c in ["pim_total", "monto_pim"] if c in shame_df.columns), None)
        saldo_col = "saldo_no_devengado" if "saldo_no_devengado" in shame_df.columns else None

        s1.metric("Entities in Hall of Shame", len(shame_df))
        if pim_col_s:
            s2.metric("Combined PIM at Risk", fmt_soles(shame_df[pim_col_s].sum()))
        if saldo_col:
            s3.metric("Total Frozen Capital", fmt_soles(shame_df[saldo_col].sum()))

        # Execution rate chart
        entity_col = next((c for c in ["pliego", "entidad"] if c in shame_df.columns), shame_df.columns[0])
        fig_shame = px.bar(
            shame_df,
            x="avance_pct", y=entity_col,
            orientation="h",
            color="avance_pct",
            color_continuous_scale=[(0.0, "#ef5350"), (0.4, "#ffa726"), (1.0, "#ffee58")],
            range_color=[0, 60],
            title=f"Top {top_n} Worst Executing Entities — Avance %",
            labels={"avance_pct": "Avance (%)", entity_col: ""},
            text="avance_pct",
        )
        fig_shame.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_shame.add_vline(x=40, line_dash="dash", line_color="#ef5350",
                            annotation_text="Critical 40%", annotation_font_color="#ef5350")
        fig_shame.update_layout(
            plot_bgcolor="#1a1f35", paper_bgcolor="#0f1117",
            font_color="#c5cae9", height=max(400, top_n * 22),
            coloraxis_showscale=False,
            margin=dict(l=10, r=60, t=60, b=10),
        )
        fig_shame.update_xaxes(gridcolor="#2a2f4a", range=[0, 70])
        fig_shame.update_yaxes(gridcolor="#2a2f4a", tickfont=dict(size=10))
        st.plotly_chart(fig_shame, use_container_width=True)

        # Frozen capital bar
        if saldo_col and pim_col_s:
            st.markdown('<div class="section-header">Frozen Capital by Entity (Saldo No Devengado)</div>',
                        unsafe_allow_html=True)
            fig_frozen = px.bar(
                shame_df.sort_values(saldo_col, ascending=False),
                x=entity_col, y=saldo_col,
                color="risk_category" if "risk_category" in shame_df.columns else saldo_col,
                color_discrete_map={"Crítico": "#ef5350", "Bajo": "#ffa726"},
                title="Presupuesto Paralizado — Capital No Ejecutado (S/)",
                labels={saldo_col: "Saldo No Devengado (S/)", entity_col: ""},
            )
            fig_frozen.update_layout(
                plot_bgcolor="#1a1f35", paper_bgcolor="#0f1117",
                font_color="#c5cae9", height=380,
                showlegend=True,
                margin=dict(l=10, r=10, t=50, b=80),
            )
            fig_frozen.update_yaxes(gridcolor="#2a2f4a")
            fig_frozen.update_xaxes(tickangle=45, tickfont=dict(size=9))
            st.plotly_chart(fig_frozen, use_container_width=True)

        # Interactive sortable table
        st.markdown('<div class="section-header">📋 Interactive Data Matrix</div>',
                    unsafe_allow_html=True)

        display_cols = [c for c in [
            entity_col, "departamento", "risk_category",
            "avance_fmt", "pim_fmt", "devengado_fmt", "saldo_fmt",
        ] if c in shame_df.columns]

        st.dataframe(
            shame_df[display_cols].rename(columns={
                entity_col: "Entidad", "departamento": "Departamento",
                "risk_category": "Riesgo", "avance_fmt": "Avance %",
                "pim_fmt": "PIM", "devengado_fmt": "Devengado",
                "saldo_fmt": "Saldo No Devengado",
            }),
            use_container_width=True,
            height=420,
        )
    else:
        st.success("No entities found below the 60% execution threshold. Pipeline data may need refreshing.")


# ===========================================================================
# TAB 4 — Multi-Agent Audit Log & Live Period Playground (2025 only)
# ===========================================================================
with tab4:
    st.markdown('<div class="section-header">🤖 Multi-Agent Audit Log</div>',
                unsafe_allow_html=True)
    st.caption("Evaluator Skill report — structural changes, bugs found, optimisations applied · 2025 data only")

    audit_md = load_audit_report()
    st.markdown(audit_md)

    st.divider()

    st.markdown('<div class="section-header">🔄 Live Period Playground</div>',
                unsafe_allow_html=True)
    st.caption("Simulate period-driven CLI updates — equivalent to: claude \"run executor_skill for period <X>\"")

    col_period, col_nivel, col_run = st.columns([2, 1, 1])
    with col_period:
        period_input = st.text_input(
            "Fiscal Period", value="2025",
            placeholder="e.g. 2025, 2025-12, 2025-Q4",
            help="Period string forwarded to the data pipeline's --period argument",
        )
    with col_nivel:
        nivel_input = st.selectbox(
            "Government Level",
            options=["GL", "G", "L"],
            format_func=lambda x: {"GL": "Both (G+L)", "G": "Regional only", "L": "Local only"}[x],
        )
    with col_run:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("▶ Run Pipeline", type="primary", use_container_width=True)

    if run_btn:
        import subprocess, sys as _sys
        with st.spinner(f"Running pipeline for period={period_input}, nivel={nivel_input} …"):
            pipeline = Path(__file__).parent / "src" / "data_pipeline.py"
            result = subprocess.run(
                [_sys.executable, str(pipeline),
                 "--period", period_input,
                 "--nivel", nivel_input],
                capture_output=True, text=True, timeout=120,
            )
        if result.returncode == 0:
            st.success(f"Pipeline completed for period **{period_input}**.")
            try:
                summary = json.loads(result.stdout)
                r1, r2, r3 = st.columns(3)
                r1.metric("National Execution Rate",
                          fmt_pct(summary.get("national_execution_rate_pct", 0)))
                r2.metric("Total PIM", fmt_soles(summary.get("total_pim", 0)))
                r3.metric("Frozen Capital", fmt_soles(summary.get("frozen_capital", 0)))
            except Exception:
                st.code(result.stdout[:1000])
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Pipeline failed.")
            st.code(result.stderr[:500])

    st.divider()

    # Architecture notes
    st.markdown('<div class="section-header">⚙️ Architecture & Agent Cooperation Notes</div>',
                unsafe_allow_html=True)

    arch_data = {
        "Component": [
            "MCP Server", "Executor Skill", "Evaluator Skill",
            "Data Pipeline", "OCR Engine", "Analytical Engine",
        ],
        "Role": [
            "Exposes 10 tools to Claude Code CLI",
            "Data extraction, OCR trigger, app draft",
            "QA audit, performance optimisation, UX polish",
            "Subprocess: streams CSV, filters, saves Parquet",
            "Subprocess: PaddleOCR on 15+ pages of 1964 doc",
            "Reads processed Parquet, computes all KPIs",
        ],
        "Anti-Flooding": [
            "✅ Subprocess isolation",
            "✅ Never ingests raw CSV",
            "✅ Reads only processed artefacts",
            "✅ Chunk streaming + Parquet output",
            "✅ Per-page processing, JSON output",
            "✅ Parquet → micro DataFrames only",
        ],
    }
    st.dataframe(pd.DataFrame(arch_data), use_container_width=True, hide_index=True)
