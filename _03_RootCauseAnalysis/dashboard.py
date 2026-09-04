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
    if label in {'timing_ok_optimal', 'egfr_normal'}:
        return '#e8f5e9', '#388e3c'
    if label in {'timing_ok_tolerated', 'timing_data_missing', 'phase_not_supported'}:
        return '#fff8e1', '#f9a825'
    return '#ffebee', '#c62828'


def _load_timing_results(base_path: Path) -> pd.DataFrame:
    frames = []
    for path in (
        base_path / 'results' / 'rca_results_timing_schema_v1.csv',
        base_path / 'rca_results_all.csv',
        base_path / 'rca_results.csv',
    ):
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        if 'rca_schema' not in frame.columns:
            continue
        frame = frame[frame['rca_schema'].astype(str).str.startswith('timing_schema')]
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates(
        subset=['ct_id', 'series_folder', 'rca_schema'], keep='first'
    )


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

        patient_warning_path = base_path.parent / '_02_QualityCheck' / 'OUTPUTS' / 'patient_hu_qc_summary.csv'

        try:
            qc_df   = pd.read_csv(qc_path)
            link_df = pd.read_excel(link_path)           # columns: ID, PAT_N, index
            series_df = pd.read_csv(base_path.parent / '_00_Preprocessing' / 'OUTPUTS' / 'retained_series_unified_filtered.csv')
            qc_detail_df = pd.read_csv(qc_path)
            timing_results = _load_timing_results(base_path)
            patient_warning_df = pd.read_csv(patient_warning_path) if patient_warning_path.exists() else pd.DataFrame()
            inj_loader = ExcelLoader(str(excel_path))
            inj_loader.load()
        except Exception as e:
            st.error(f"Failed to load data: {e}"); st.stop()

        # Bring in scanner metadata (not part of the QC output) for filtering.
        if 'scanner' not in qc_df.columns:
            if 'scanner' in series_df.columns:
                scanner_lookup = series_df[['ct_id', 'series_folder', 'scanner']].drop_duplicates(subset=['ct_id', 'series_folder'])
                qc_df = qc_df.merge(scanner_lookup, on=['ct_id', 'series_folder'], how='left')
            else:
                qc_df['scanner'] = ''
        qc_df['scanner'] = qc_df['scanner'].fillna('').astype(str)

        # Reserve the top sidebar slot for case selection; filled in after filters are applied below.
        case_selection_slot = st.sidebar.container()

        with st.sidebar:
            st.header("Filters")
            ct_types = sorted(qc_df['CT_type'].dropna().astype(str).unique().tolist()) if 'CT_type' in qc_df.columns else []
            procedures = sorted(qc_df['procedure_code'].dropna().astype(str).unique().tolist())
            phases = sorted(qc_df['phase_name'].dropna().astype(str).unique().tolist())
            statuses = sorted(qc_df['status'].dropna().astype(str).unique().tolist())
            metrics = sorted(qc_df['metric_name'].dropna().astype(str).unique().tolist()) if 'metric_name' in qc_df.columns else []
            scanners = sorted(qc_df['scanner'].dropna().astype(str).unique().tolist())

            selected_ct_types = st.multiselect("CT Type", ct_types, default=ct_types) if ct_types else []
            selected_procedures = st.multiselect("Procedure code", procedures, default=procedures)
            selected_phases = st.multiselect("Phase", phases, default=phases)
            selected_statuses = st.multiselect("Status", statuses, default=statuses)
            selected_metrics = st.multiselect("Metric", metrics, default=metrics) if metrics else []
            selected_scanners = st.multiselect("Scanner", scanners, default=scanners)

            warning_priority_labels = {
                "none": "No warning",
                "low": "Low priority warning",
                "medium": "Medium priority warning",
                "high": "High priority warning",
            }
            segmentation_warning_label = "Segmentation warning"
            selected_warning_labels = st.multiselect(
                "Patient warning",
                [*warning_priority_labels.values(), segmentation_warning_label],
                default=[*warning_priority_labels.values(), segmentation_warning_label],
            )
            selected_warning_priorities = [
                priority for priority, label in warning_priority_labels.items()
                if label in selected_warning_labels
            ]
            only_warning_series = st.checkbox("Only series with warnings", value=False)

        qc_df_filtered = qc_df[
            (qc_df['CT_type'].isin(selected_ct_types) if ct_types else True)
            & qc_df['procedure_code'].isin(selected_procedures)
            & qc_df['phase_name'].isin(selected_phases)
            & qc_df['status'].isin(selected_statuses)
            & (qc_df['metric_name'].isin(selected_metrics) if metrics else True)
            & qc_df['scanner'].isin(selected_scanners)
        ].copy()

        if not patient_warning_df.empty and 'warning_priority' in patient_warning_df.columns:
            patient_warning_mask = patient_warning_df['warning_priority'].fillna('none').isin(selected_warning_priorities)
            if segmentation_warning_label in selected_warning_labels and 'segmentation_warning' in patient_warning_df.columns:
                segmentation_mask = patient_warning_df['segmentation_warning'].fillna('').astype(str).str.strip().ne('')
                patient_warning_mask |= segmentation_mask
            warning_patient_ids = patient_warning_df.loc[patient_warning_mask, 'ct_id'].astype(str).unique()
            qc_df_filtered = qc_df_filtered[qc_df_filtered['ct_id'].astype(str).isin(warning_patient_ids)]

        if only_warning_series and 'series_warnings' in qc_df_filtered.columns:
            has_warning = qc_df_filtered['series_warnings'].fillna('').astype(str).str.strip().ne('')
            warning_keys = qc_df_filtered.loc[has_warning, ['ct_id', 'series_folder']].drop_duplicates()
            qc_df_filtered = qc_df_filtered.merge(warning_keys, on=['ct_id', 'series_folder'], how='inner')

        with case_selection_slot:
            st.header("Case selection")

            # Only folders with at least one QC issue, ordered numerically by ct_id
            critical_mask = qc_df_filtered['status'].isin({'critical_low', 'critical_high'})
            incoherent_mask = (
                qc_df_filtered['attenuation_consistency'].fillna('').eq('incoherent')
                if 'attenuation_consistency' in qc_df_filtered.columns
                else pd.Series(False, index=qc_df_filtered.index)
            )
            issue_mask = critical_mask | incoherent_mask
            critical_folders = (
                qc_df_filtered[issue_mask][['ct_id', 'ct_folder']]
                .drop_duplicates()
                .sort_values('ct_id')
                ['ct_folder']
                .tolist()
            )
            display_names = [str(ct_id) for ct_id in qc_df_filtered[issue_mask][['ct_id', 'ct_folder']].drop_duplicates().sort_values('ct_id')['ct_id'].tolist()]
            display_to_full = dict(zip(display_names, critical_folders))

            if not display_names:
                st.warning("No cases match the current filters.")
                st.stop()

            selected_display = st.selectbox("CT case", display_names)
            selected_folder  = display_to_full[selected_display]

            # Only series within this folder that have a critical or incoherent outcome
            folder_series = sorted(
                qc_df_filtered[
                    (qc_df_filtered['ct_folder'] == selected_folder) &
                    issue_mask
                ]['series_folder'].unique()
            )
            selected_series = st.selectbox("Series", folder_series)

            run = st.button("▶ Run analysis", type="primary", width="stretch")

        if not run:
            st.info("Select a case and series in the sidebar, then click **Run analysis**.")
        else:
            # Get ct_id from QC results
            qc_row = qc_df_filtered[
                (qc_df_filtered['ct_folder'] == selected_folder) &
                (qc_df_filtered['series_folder'] == selected_series)
            ].iloc[0]

            ct_id         = str(qc_row['ct_id'])
            procedure_code = qc_row.get('procedure_code', '')
            phase_name     = qc_row.get('phase_name', '')
            qc_rows = qc_df_filtered[
                (qc_df_filtered['ct_folder'] == selected_folder) &
                (qc_df_filtered['series_folder'] == selected_series)
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
                timing_issue_match = timing_results[
                    (timing_results['ct_id'].astype(str) == str(ct_id))
                    & (timing_results['injection_index'].astype(str) == str(injection_index))
                    & timing_results['rca_label'].astype(str).str.strip().str.lower().isin({'early', 'late'})
                ]
                if not timing_issue_match.empty:
                    timing_issue = timing_issue_match.iloc[0]
                    patient_data['_timing_issue_label'] = str(timing_issue['rca_label']).strip().lower()
                    patient_data['_timing_issue_series_folder'] = timing_issue.get('series_folder', '')

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
            has_incoherent_attenuation = (
                'attenuation_consistency' in qc_rows.columns
                and qc_rows['attenuation_consistency'].fillna('').eq('incoherent').any()
            )
            worst = 'critical_high' if 'critical_high' in qc_statuses else ('critical_low' if 'critical_low' in qc_statuses else ('incoherent_attenuation' if has_incoherent_attenuation else qc_statuses[0] if qc_statuses else '—'))
            qc_color = '#ffebee' if 'critical' in worst else '#fff9c4'
            st.markdown(
                f"""<div style="background:{qc_color}; border-left:4px solid #c62828;
                               padding:10px 16px; border-radius:6px; margin-bottom:12px; font-size:13px;">
                    <b>QC result</b> — CT {selected_display} / {selected_series}<br/>
                    Status: <b>{worst}</b> &nbsp;|&nbsp; Procedure: <b>{procedure_code}</b>
                    &nbsp;|&nbsp; Phase: <b>{phase_name}</b><br/>
                    Affected ROIs: {', '.join(affected_rois)}
                </div>""",
                unsafe_allow_html=True
            )

            if 'attenuation_message' in qc_rows.columns:
                attenuation_rows = qc_rows[qc_rows['attenuation_message'].fillna('').astype(str).str.strip().ne('')]
                for _, attenuation_row in attenuation_rows.iterrows():
                    incoherent = attenuation_row.get('attenuation_consistency') == 'incoherent'
                    color = '#c62828' if incoherent else '#0277bd'
                    n_slices = attenuation_row.get('edge_slice_count')
                    slice_label = f"first/last {int(n_slices)} vessel slices" if pd.notna(n_slices) else 'vessel endpoints'
                    st.markdown(
                        f"""<div style="background:{color}0d; border-left:4px solid {color};
                                       padding:10px 16px; border-radius:6px; margin-bottom:12px; font-size:13px;">
                            <b>Attenuation consistency ({slice_label})</b><br/>
                            {attenuation_row.get('attenuation_message')}
                        </div>""",
                        unsafe_allow_html=True,
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
                        icon = "✅" if step['result'] else ("⚠️" if step.get('trace_type') == 'availability' else "❌")
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

            # Apply the same sidebar filters used for case selection (CT Type, Scanner not
            # part of the batch output, so they're joined in from the QC detail table).
            join_cols = [c for c in ('CT_type', 'scanner') if c not in df.columns and c in qc_df.columns]
            if join_cols:
                lookup = qc_df[['ct_id', 'series_folder', *join_cols]].drop_duplicates(subset=['ct_id', 'series_folder']).copy()
                lookup['ct_id'] = lookup['ct_id'].astype(str)
                lookup['series_folder'] = lookup['series_folder'].astype(str)
                df = df.copy()
                df['_ct_id_str'] = df['ct_id'].astype(str)
                df['_series_folder_str'] = df['series_folder'].astype(str)
                df = df.merge(
                    lookup, left_on=['_ct_id_str', '_series_folder_str'],
                    right_on=['ct_id', 'series_folder'], how='left', suffixes=('', '_lookup'),
                ).drop(columns=['_ct_id_str', '_series_folder_str', 'ct_id_lookup', 'series_folder_lookup'], errors='ignore')
            for col in ('CT_type', 'scanner'):
                if col in df.columns:
                    df[col] = df[col].fillna('').astype(str)

            df = df[
                (df['CT_type'].isin(selected_ct_types) if 'CT_type' in df.columns and ct_types else True)
                & (df['scanner'].isin(selected_scanners) if 'scanner' in df.columns else True)
                & (df['phase_name'].isin(selected_phases) if 'phase_name' in df.columns else True)
                & (df['procedure_code'].isin(selected_procedures) if 'procedure_code' in df.columns else True)
                & (
                    df['patient_warning_priority'].fillna('none').isin(selected_warning_priorities)
                    if 'patient_warning_priority' in df.columns else True
                )
            ]

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
            display_cols = ['ct_id', 'series_folder', 'phase_name',
                            'procedure_code', 'injection_index',
                            'qc_worst_status', 'affected_rois',
                            'rca_label', 'rca_title', 'rca_notes', 'rca_recommendations']
            st.dataframe(
                view[[c for c in display_cols if c in view.columns]],
                width="stretch", height=350
            )

            # Detail card for selected row
            if not view.empty:
                st.subheader("Case detail")
                row_idx = st.selectbox("Select row", view.index,
                                       format_func=lambda i: f"CT {view.loc[i,'ct_id']} | {view.loc[i,'series_folder']}")
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

            st.download_button("⬇ Download CSV", data=view.drop(columns=['ct_folder'], errors='ignore').to_csv(index=False),
                               file_name="rca_results.csv", mime="text/csv")


if __name__ == '__main__':
    main()
