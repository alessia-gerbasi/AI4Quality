"""
Batch Root Cause Analysis

Loads QC results, filters series with critical_low / critical_high outcomes,
joins to injection history via link table, runs the schema rule engine,
and writes a result CSV.

Usage:
    python batch_analysis.py [--schema timing_schema] [--output rca_results.csv]
    python batch_analysis.py --list-schemas
"""
import argparse
import ast
import pandas as pd
from pathlib import Path

from rule_engine import RuleEvaluator
from excel_loader import ExcelLoader

# ── Paths (all relative to this file) ────────────────────────────────────────
BASE          = Path(__file__).parent
SCHEMA_DIR    = BASE / 'schemas'
THRESHOLD_CFG = BASE.parent / 'config' / 'common' / 'ct_protocols.yaml'
QC_RESULTS    = BASE.parent / '_02_QualityCheck' / 'OUTPUTS' / 'roi_hu_qc_results.csv'
SERIES_TABLE  = BASE.parent / '_00_Preprocessing' / 'OUTPUTS' / 'retained_series_unified_filtered.csv'
QC_TABLE      = BASE.parent / '_02_QualityCheck' / 'OUTPUTS' / 'roi_hu_qc_results.csv'
LINK_TABLE    = BASE.parent.parent / 'DATA' / 'CDI_NEXO_072026' / '0_files' / 'link_anonymization.xlsx'
INJECTION_XLS = BASE.parent.parent / 'DATA' / 'CDI_NEXO_072026' / '0_files' / 'Injection History Anonymized.xlsx'
DEFAULT_OUT   = BASE / 'rca_results.csv'
RESULTS_DIR   = BASE / 'results'
AGGREGATED_OUT = BASE / 'rca_results_all.csv'

CRITICAL_STATUSES = {'critical_low', 'critical_high'}


def load_data():
    """Load and join QC results → link table → injection history."""

    qc = pd.read_csv(QC_RESULTS)
    series = pd.read_csv(SERIES_TABLE)
    link = pd.read_excel(LINK_TABLE)          # columns: ID, PAT_N, index
    inj = pd.read_excel(INJECTION_XLS)

    # Build join key: CT_QUALITY_{ct_id}
    qc['_link_id'] = 'CT_QUALITY_' + qc['ct_id'].astype(str)

    # Merge QC → link table
    merged = qc.merge(
        link.rename(columns={'ID': '_link_id', 'index': 'injection_index'}),
        on='_link_id', how='left'
    )

    return merged, inj, series


def _parse_dicom_time_to_seconds(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        raw = float(text)
    except ValueError:
        return None

    hhmmss = int(raw)
    frac = raw - hhmmss
    hh = hhmmss // 10000
    mm = (hhmmss % 10000) // 100
    ss = hhmmss % 100
    if not (0 <= hh < 24 and 0 <= mm < 60 and 0 <= ss < 60):
        return None
    return hh * 3600 + mm * 60 + ss + frac


def build_patient_context(patient_data: dict, series_df: pd.DataFrame,
                          ct_folder: str, series_folder: str,
                          phase_name: str, procedure_code: str,
                          qc_df: pd.DataFrame = None,
                          affected_rois: str = '') -> dict:
    """Attach DICOM timing metadata for the current series and arterial reference."""
    context = dict(patient_data or {})
    context['_ct_folder'] = ct_folder
    context['_series_folder'] = series_folder
    context['_phase'] = phase_name
    context['_procedure_code'] = procedure_code
    context['_has_noncontrast_series'] = bool(
        not series_df[(series_df['ct_folder'].astype(str) == str(ct_folder))
                      & (series_df['phase_name'].fillna('').astype(str).str.lower() == 'basale')].empty
    )
    context['_liver_problem_present'] = 'liver' in str(affected_rois).lower().split(',')
    if qc_df is not None:
        liver_rows = qc_df[(qc_df['ct_folder'].astype(str) == str(ct_folder))
                           & (qc_df['series_folder'].astype(str) == str(series_folder))
                           & (qc_df['roi_name'].astype(str).str.lower() == 'liver')]
        if not liver_rows.empty:
            context['_liver_hu_precontrast'] = liver_rows.iloc[0].get('mean_hu_precontrast')
            context['_liver_hu_current'] = liver_rows.iloc[0].get('mean_hu')

    ct_series = series_df[series_df['ct_folder'].astype(str) == str(ct_folder)].copy()
    current = ct_series[ct_series['series_folder'].astype(str) == str(series_folder)]
    if current.empty:
        current = ct_series[
            (ct_series['series_folder'].astype(str) == str(series_folder))
            & (ct_series['procedure_code_value'].astype(str) == str(procedure_code))
        ]

    current_row = current.iloc[0] if not current.empty else None
    if current_row is not None:
        context['_current_acquisition_time'] = current_row.get('acquisition_time')
        context['_current_contrast_bolus_start'] = current_row.get('contrast_bolus_start')

    arterial = ct_series[
        ct_series['phase_name'].fillna('').astype(str).str.strip().str.lower() == 'arteriosa'
    ].copy()
    if procedure_code:
        same_proc = arterial[arterial['procedure_code_value'].astype(str) == str(procedure_code)]
        if not same_proc.empty:
            arterial = same_proc

    if not arterial.empty:
        if current_row is not None:
            current_seconds = _parse_dicom_time_to_seconds(current_row.get('acquisition_time'))
            arterial['_acq_seconds'] = arterial['acquisition_time'].apply(_parse_dicom_time_to_seconds)
            if current_seconds is not None and arterial['_acq_seconds'].notna().any():
                arterial['_delta'] = (arterial['_acq_seconds'] - current_seconds).abs()
                arterial = arterial.sort_values('_delta')
        arterial_row = arterial.iloc[0]
        context['_arterial_acquisition_time'] = arterial_row.get('acquisition_time')
        context['_arterial_contrast_bolus_start'] = arterial_row.get('contrast_bolus_start')
        context['_arterial_series_folder'] = arterial_row.get('series_folder')

    return context


def get_injection_record(inj_df: pd.DataFrame, injection_index: str,
                         procedure_code: str) -> dict:
    """Return the injection row matching index + procedure, falling back to first row."""
    rows = inj_df[inj_df['index'].astype(str) == str(injection_index)]
    if rows.empty:
        return {}

    # Prefer row whose Order Procedure matches QC procedure code
    match = rows[rows['Order Procedure'].astype(str) == str(procedure_code)]
    if not match.empty:
        return match.iloc[0].to_dict()

    return rows.iloc[0].to_dict()


def run_batch(schema_name: str, output_path: Path, statuses: set = None):
    """Run RCA for all critical series and write output CSV."""
    if statuses is None:
        statuses = CRITICAL_STATUSES

    schema_path = SCHEMA_DIR / f'{schema_name}.yaml'
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    if not THRESHOLD_CFG.exists():
        raise FileNotFoundError(f"Threshold config not found: {THRESHOLD_CFG}")

    print(f"Loading data...")
    merged, inj, series_df = load_data()
    qc_df = pd.read_csv(QC_TABLE) if QC_TABLE.exists() else None

    timing_labels = {}
    timing_source = AGGREGATED_OUT if AGGREGATED_OUT.exists() else DEFAULT_OUT
    if timing_source.exists():
        timing_results = pd.read_csv(timing_source)
        timing_results = timing_results[timing_results.get('rca_schema', '').astype(str).str.startswith('timing_schema')]
        timing_labels = {
            (str(item.ct_id), str(item.series_folder)): item.rca_label
            for item in timing_results.itertuples()
            if pd.notna(item.rca_label)
        }

    # Filter to critical series only (unique per series, not per ROI)
    critical = merged[merged['status'].isin(statuses)].copy()
    series_keys = ['ct_id', 'ct_folder', 'series_folder', 'phase_name',
                   'procedure_code', 'injection_index']
    critical_series = (
        critical.groupby([k for k in series_keys if k in critical.columns])
        .agg(
            worst_status=('status', lambda x: 'critical_high' if 'critical_high' in x.values else 'critical_low'),
            affected_rois=('roi_name', lambda x: ', '.join(x.dropna().unique())),
            n_critical_rois=('status', 'count'),
            series_warnings=('series_warnings', 'first'),
        )
        .reset_index()
    )

    print(f"Found {len(critical_series)} critical series to analyse.")

    evaluator = RuleEvaluator(str(schema_path), str(THRESHOLD_CFG))
    rows = []

    for _, row in critical_series.iterrows():
        injection_index = row.get('injection_index', '')
        procedure_code  = row.get('procedure_code', '')

        patient_data = get_injection_record(inj, injection_index, procedure_code)
        patient_data = build_patient_context(
            patient_data,
            series_df,
            row.get('ct_folder', ''),
            row.get('series_folder', ''),
            row.get('phase_name', ''),
            procedure_code,
            qc_df,
            row.get('affected_rois', ''),
        )
        timing_label = timing_labels.get((str(row.get('ct_id')), str(row.get('series_folder'))))
        if timing_label:
            patient_data['rca_label'] = timing_label

        result = evaluator.evaluate(patient_data)

        card = result.get('card', {})
        rca_variables = result.get('calculated_variables', {})
        rca_notes = rca_variables.get('note_text', '')
        if not rca_notes:
            rca_notes = ' | '.join(
                f'{label}: {patient_data.get(field)}'
                for label, field in (
                    ('Injection Notes', 'Injection Notes'),
                    ('Injection Reports(Custom)', 'Injection Reports(Custom)'),
                )
                if patient_data.get(field) is not None
                and str(patient_data.get(field)).strip().lower() not in {'', 'nan', 'none', 'null'}
            )
        rows.append({
            # QC identifiers
            'ct_id':           row.get('ct_id'),
            'ct_folder':       row.get('ct_folder'),
            'series_folder':   row.get('series_folder'),
            'phase_name':      row.get('phase_name'),
            'procedure_code':  procedure_code,
            'injection_index': injection_index,
            # QC outcome
            'qc_worst_status': row.get('worst_status'),
            'affected_rois':   row.get('affected_rois'),
            'n_critical_rois': row.get('n_critical_rois'),
            'series_warnings': row.get('series_warnings'),
            # RCA result
            'rca_schema':         schema_name,
            'rca_label':          result.get('diagnosis_label', 'unknown'),
            'rca_diagnoses':      ' | '.join(result.get('diagnoses', [result.get('diagnosis_label', 'unknown')])),
            'rca_title':          card.get('title', ''),
            'rca_explanation':    card.get('explanation', ''),
            'rca_notes':          rca_notes,
            'rca_impact':         card.get('impact', ''),
            'rca_recommendations': ' | '.join(card.get('recommendations', [])),
            'rca_success':        result.get('success', False),
            # Calculated variables (for debugging)
            'rca_variables':      str(rca_variables),
            # Decision path summary
            'rca_decision_path':  ' → '.join(
                f"{s['node']}({'Y' if s['result'] else 'N'})"
                for s in result.get('decision_path', [])
            ),
        })

    out_df = pd.DataFrame(rows)
    RESULTS_DIR.mkdir(exist_ok=True)
    schema_output = RESULTS_DIR / f'rca_results_{schema_name}.csv'
    out_df.to_csv(schema_output, index=False)

    frames = []
    for existing_path in sorted(RESULTS_DIR.glob('rca_results_*.csv')):
        try:
            frames.append(pd.read_csv(existing_path))
        except (OSError, pd.errors.EmptyDataError):
            continue
    aggregate = pd.concat(frames, ignore_index=True) if frames else out_df
    aggregate = aggregate.drop_duplicates(
        subset=['ct_id', 'series_folder', 'rca_schema'], keep='last'
    )
    aggregate.to_csv(AGGREGATED_OUT, index=False)
    # Preserve the legacy output as a snapshot of the selected schema.
    out_df.to_csv(DEFAULT_OUT, index=False)
    print(f"Saved {len(out_df)} results to {schema_output}")
    print(f"Updated aggregate with {len(aggregate)} results at {AGGREGATED_OUT}")

    # Print quick summary
    print("\nDiagnosis distribution:")
    print(out_df.groupby(['qc_worst_status', 'rca_label']).size().to_string())

    return out_df


def main():
    parser = argparse.ArgumentParser(description='Batch Root Cause Analysis')
    parser.add_argument('--schema',  default='timing_schema',
                        help='Schema name (without .yaml)')
    parser.add_argument('--output',  default=str(DEFAULT_OUT),
                        help='Output CSV path')
    parser.add_argument('--statuses', nargs='+',
                        default=['critical_low', 'critical_high'],
                        help='QC statuses to include')
    parser.add_argument('--list-schemas', action='store_true',
                        help='List available schemas and exit')
    args = parser.parse_args()

    if args.list_schemas:
        schemas = sorted(p.stem for p in SCHEMA_DIR.glob('*.yaml'))
        print("Available schemas:")
        for s in schemas:
            print(f"  {s}")
        return

    run_batch(
        schema_name=args.schema,
        output_path=Path(args.output),
        statuses=set(args.statuses)
    )


if __name__ == '__main__':
    main()
