"""
Results Dashboard — run a schema on a patient case and display the diagnosis.

Run:  streamlit run dashboard.py
"""
import streamlit as st
import pandas as pd
from pathlib import Path

try:
    from rule_engine import RuleEvaluator
    from excel_loader import ExcelLoader
    from batch_analysis import run_batch, DEFAULT_OUT, SCHEMA_DIR as BATCH_SCHEMA_DIR, build_patient_context
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()


def _label_colors(label: str) -> tuple[str, str]:
    if label == 'timing_ok_optimal':
        return '#e8f5e9', '#388e3c'
    if label in {'timing_ok_tolerated', 'timing_data_missing', 'phase_not_supported'}:
        return '#fff8e1', '#f9a825'
    return '#ffebee', '#c62828'


def main():
    st.set_page_config(layout="wide", page_title="Root Cause Analysis")
    st.title("📋 Root Cause Analysis")

    base_path   = Path(__file__).parent
    schema_dir  = base_path / 'schemas'
    thresh_path = base_path.parent / 'config' / 'common' / 'ct_protocols.yaml'
    excel_path  = base_path.parent.parent / 'DATA' / 'CDI_NEXO_072026' / '0_files' / 'Injection History Anonymized.xlsx'

    # Sidebar — schema selection used by both tabs
    with st.sidebar:
        st.header("Configuration")
        schemas = sorted([f.stem for f in schema_dir.glob('*.yaml')])
        if not schemas:
            st.error("No schemas found. Run the Schema Editor first."); st.stop()
        selected_schema = st.selectbox("Schema", schemas)

    tab_single, tab_batch = st.tabs(["🔍 Single case", "📦 Batch (critical series)"])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — Single case
    # ════════════════════════════════════════════════════════════════════════
    with tab_single:
        # Load QC results and link table once
        qc_path   = base_path.parent / '_02_QualityCheck' / 'OUTPUTS' / 'roi_hu_qc_results.csv'
        link_path = base_path.parent.parent / 'DATA' / 'CDI_NEXO_072026' / '0_files' / 'link_anonymization.xlsx'

        try:
            qc_df   = pd.read_csv(qc_path)
            link_df = pd.read_excel(link_path)           # columns: ID, PAT_N, index
            series_df = pd.read_csv(base_path.parent / '_00_Preprocessing' / 'OUTPUTS' / 'retained_series_unified_filtered.csv')
            qc_detail_df = pd.read_csv(qc_path)
            timing_results_path = base_path / 'rca_results.csv'
            timing_results = pd.read_csv(timing_results_path) if timing_results_path.exists() else pd.DataFrame()
            inj_loader = ExcelLoader(str(excel_path))
            inj_loader.load()
        except Exception as e:
            st.error(f"Failed to load data: {e}"); st.stop()

        with st.sidebar:
            st.header("Case selection")

            # Only folders with at least one critical series, ordered numerically by ct_id
            critical_mask = qc_df['status'].isin({'critical_low', 'critical_high'})
            critical_folders = (
                qc_df[critical_mask][['ct_id', 'ct_folder']]
                .drop_duplicates()
                .sort_values('ct_id')
                ['ct_folder']
                .tolist()
            )
            display_names = [f.replace('CT_QUALITY_', '') for f in critical_folders]
            display_to_full = dict(zip(display_names, critical_folders))

            selected_display = st.selectbox("CT case", display_names)
            selected_folder  = display_to_full[selected_display]

            # Only series within this folder that have a critical outcome
            folder_series = sorted(
                qc_df[
                    (qc_df['ct_folder'] == selected_folder) &
                    (qc_df['status'].isin({'critical_low', 'critical_high'}))
                ]['series_folder'].unique()
            )
            selected_series = st.selectbox("Series", folder_series)

            run = st.button("▶ Run analysis", type="primary", use_container_width=True)

        if not run:
            st.info("Select a case and series in the sidebar, then click **Run analysis**.")
        else:
            # Get ct_id from QC results
            qc_row = qc_df[
                (qc_df['ct_folder'] == selected_folder) &
                (qc_df['series_folder'] == selected_series)
            ].iloc[0]

            ct_id         = str(qc_row['ct_id'])
            procedure_code = qc_row.get('procedure_code', '')
            phase_name     = qc_row.get('phase_name', '')
            qc_rows = qc_df[
                (qc_df['ct_folder'] == selected_folder) &
                (qc_df['series_folder'] == selected_series)
            ]
            affected_rois = qc_rows['roi_name'].dropna().unique().tolist()

            # Look up injection index via link table
            link_key  = f'CT_QUALITY_{ct_id}'
            link_match = link_df[link_df['ID'] == link_key]
            injection_index = link_match.iloc[0]['index'] if not link_match.empty else None

            # Get injection data; prefer matching procedure
            patient_data = {}
            if injection_index:
                rows = inj_loader.df[inj_loader.df['index'].astype(str) == str(injection_index)]
                match = rows[rows['Order Procedure'].astype(str) == str(procedure_code)]
                patient_data = (match.iloc[0] if not match.empty else rows.iloc[0]).to_dict() if not rows.empty else {}

            patient_data = build_patient_context(
                patient_data,
                series_df,
                selected_folder,
                selected_series,
                phase_name,
                procedure_code,
                qc_detail_df,
                ', '.join(affected_rois),
            )
            if not timing_results.empty and 'rca_label' in timing_results.columns:
                timing_match = timing_results[
                    (timing_results['ct_id'].astype(str) == str(ct_id))
                    & (timing_results['series_folder'].astype(str) == str(selected_series))
                    & timing_results['rca_schema'].astype(str).str.startswith('timing_schema')
                ]
                if not timing_match.empty:
                    patient_data['rca_label'] = timing_match.iloc[0]['rca_label']

            try:
                evaluator = RuleEvaluator(str(schema_dir / f'{selected_schema}.yaml'), str(thresh_path))
                result    = evaluator.evaluate(patient_data)
            except Exception as e:
                st.error(f"Evaluation failed: {e}"); st.stop()

            # QC context banner
            qc_rows = qc_df[
                (qc_df['ct_folder'] == selected_folder) &
                (qc_df['series_folder'] == selected_series)
            ]
            qc_statuses  = qc_rows['status'].unique().tolist()
            affected_rois = qc_rows['roi_name'].unique().tolist()
            worst = 'critical_high' if 'critical_high' in qc_statuses else ('critical_low' if 'critical_low' in qc_statuses else qc_statuses[0] if qc_statuses else '—')
            qc_color = '#ffebee' if 'critical' in worst else '#fff9c4'
            st.markdown(
                f"""<div style="background:{qc_color}; border-left:4px solid #c62828;
                               padding:10px 16px; border-radius:6px; margin-bottom:12px; font-size:13px;">
                    <b>QC result</b> — {selected_display} / {selected_series}<br/>
                    Status: <b>{worst}</b> &nbsp;|&nbsp; Procedure: <b>{procedure_code}</b>
                    &nbsp;|&nbsp; Phase: <b>{phase_name}</b><br/>
                    Affected ROIs: {', '.join(affected_rois)}
                </div>""",
                unsafe_allow_html=True
            )

            card  = result.get('card', {})
            label = result.get('diagnosis_label', 'unknown')
            cards = result.get('cards', [card])

            if result.get('success'):
                status_color, border_color = _label_colors(label)

                for result_card in cards:
                    st.markdown(
                        f"""
                        <div style="background:{status_color}; border-left:6px solid {border_color};
                                    padding:20px 24px; border-radius:8px; margin-bottom:16px;">
                            <h2 style="margin:0 0 6px 0;">{result_card.get('title', label)}</h2>
                            <p style="margin:0; font-size:15px;">{result_card.get('explanation', '')}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                col1, col2 = st.columns([1, 1])

                with col1:
                    st.subheader("Impact")
                    st.write(card.get('impact', '—'))

                    recs = card.get('recommendations', [])
                    if recs:
                        st.subheader("Suggestions")
                        for rec in recs:
                            st.markdown(f"- {rec}")

                with col2:
                    st.subheader("Decision path")
                    for step in result.get('decision_path', []):
                        icon = "✅" if step['result'] else "❌"
                        st.markdown(f"{icon} **{step['question']}**")
                        st.caption(f"`{step['condition']}` → `{step.get('substituted_condition', '')}`")

            else:
                st.error(f"Evaluation error: {card.get('explanation', '')}")

            if selected_schema == 'other_schema_v1':
                st.subheader('eGFR reference')
                egfr_table = pd.DataFrame([
                    {'Stage': 'Stage 1', 'eGFR result': '90 or higher', 'What it means': 'Mild kidney damage; kidneys work as well as normal'},
                    {'Stage': 'Stage 2', 'eGFR result': '60-89', 'What it means': 'Mild kidney damage; kidneys still work well'},
                    {'Stage': 'Stage 3a', 'eGFR result': '45-59', 'What it means': 'Mild to moderate kidney damage; kidneys do not work as well as they should'},
                    {'Stage': 'Stage 3b', 'eGFR result': '30-44', 'What it means': 'Moderate to severe kidney damage; kidneys do not work as well as they should'},
                    {'Stage': 'Stage 4', 'eGFR result': '15-29', 'What it means': 'Severe kidney damage; kidneys are close to not working at all'},
                    {'Stage': 'Stage 5', 'eGFR result': 'Less than 15', 'What it means': 'Most severe kidney damage; kidneys are very close to not working or have stopped working'},
                ])
                egfr_value = result.get('calculated_variables', {}).get('egfr')

                def highlight_egfr_row(row):
                    if egfr_value is None:
                        return [''] * len(row)
                    if row['Stage'] == 'Stage 1':
                        matches = egfr_value >= 90
                    elif row['Stage'] == 'Stage 2':
                        matches = 60 <= egfr_value <= 89
                    elif row['Stage'] == 'Stage 3a':
                        matches = 45 <= egfr_value <= 59
                    elif row['Stage'] == 'Stage 3b':
                        matches = 30 <= egfr_value <= 44
                    elif row['Stage'] == 'Stage 4':
                        matches = 15 <= egfr_value <= 29
                    else:
                        matches = egfr_value < 15
                    return ['background-color: #d9ead3; font-weight: bold' if matches else '' for _ in row]

                st.dataframe(egfr_table.style.apply(highlight_egfr_row, axis=1), hide_index=True)
                if egfr_value is not None and egfr_value >= 0:
                    st.caption(f'Patient eGFR: {egfr_value:g} ml/min/1.73 m2')

            with st.expander("Patient data & variables"):
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Patient data")
                    st.json(patient_data)
                with c2:
                    st.subheader("Calculated variables")
                    st.json(result.get('calculated_variables', {}))

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — Batch results
    # ════════════════════════════════════════════════════════════════════════
    with tab_batch:
        st.subheader("Batch Root Cause Analysis — Critical Series")
        st.caption("Runs the selected schema on every series where QC outcome is critical_low or critical_high.")

        col_run, col_load = st.columns([1, 1])
        if col_run.button("▶ Run batch analysis", type="primary"):
            with st.spinner("Running batch analysis..."):
                try:
                    df = run_batch(schema_name=selected_schema, output_path=DEFAULT_OUT)
                    st.session_state['batch_df'] = df
                    st.success(f"Done — {len(df)} critical series analysed. Results saved to `{DEFAULT_OUT.name}`.")
                except Exception as e:
                    st.error(f"Batch failed: {e}")

        if col_load.button("📂 Load previous results") and DEFAULT_OUT.exists():
            st.session_state['batch_df'] = pd.read_csv(DEFAULT_OUT)

        if 'batch_df' in st.session_state:
            df = st.session_state['batch_df']

            # Summary metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Critical series", len(df))
            m2.metric("Unique patients", df['ct_id'].nunique())
            label_counts = df['rca_label'].value_counts()
            m3.metric("Most common RCA", label_counts.index[0] if len(label_counts) else '—')

            # Filters
            fc1, fc2 = st.columns(2)
            qc_filter  = fc1.multiselect("Filter QC status",
                                          options=df['qc_worst_status'].unique().tolist(),
                                          default=df['qc_worst_status'].unique().tolist())
            rca_filter = fc2.multiselect("Filter RCA diagnosis",
                                          options=df['rca_label'].unique().tolist(),
                                          default=df['rca_label'].unique().tolist())

            view = df[df['qc_worst_status'].isin(qc_filter) & df['rca_label'].isin(rca_filter)]

            # Table
            display_cols = ['ct_id', 'ct_folder', 'series_folder', 'phase_name',
                            'procedure_code', 'injection_index',
                            'qc_worst_status', 'affected_rois',
                            'rca_label', 'rca_title', 'rca_notes', 'rca_recommendations']
            st.dataframe(
                view[[c for c in display_cols if c in view.columns]],
                use_container_width=True, height=350
            )

            # Detail card for selected row
            if not view.empty:
                st.subheader("Case detail")
                row_idx = st.selectbox("Select row", view.index,
                                       format_func=lambda i: f"{view.loc[i,'ct_folder']} | {view.loc[i,'series_folder']}")
                row = view.loc[row_idx]
                label = row['rca_label']
                status_color, border_color = _label_colors(label)
                st.markdown(
                    f"""<div style="background:{status_color}; border-left:6px solid {border_color};
                                   padding:16px 20px; border-radius:8px; margin-bottom:12px;">
                        <b>QC:</b> {row['qc_worst_status']} — {row['affected_rois']}<br/>
                        <b>RCA:</b> {row['rca_title']}<br/>
                        <small>{row['rca_explanation']}</small>
                    </div>""",
                    unsafe_allow_html=True
                )
                recs = str(row.get('rca_recommendations', ''))
                if recs and recs != 'nan':
                    st.markdown("**Suggestions:**")
                    for r in recs.split(' | '):
                        st.markdown(f"- {r}")
                with st.expander("Variables & decision path"):
                    st.write(f"**Variables**: {row.get('rca_variables', '')}")
                    st.write(f"**Path**: {row.get('rca_decision_path', '')}")

            st.download_button("⬇ Download CSV", data=view.to_csv(index=False),
                               file_name="rca_results.csv", mime="text/csv")


if __name__ == '__main__':
    main()
