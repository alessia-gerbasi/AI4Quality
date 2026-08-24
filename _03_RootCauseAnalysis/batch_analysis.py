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
LINK_TABLE    = BASE.parent.parent / 'DATA' / 'CDI_NEXO_072026' / '0_files' / 'link_anonymization.xlsx'
INJECTION_XLS = BASE.parent.parent / 'DATA' / 'CDI_NEXO_072026' / '0_files' / 'Injection History Anonymized.xlsx'
DEFAULT_OUT   = BASE / 'rca_results.csv'

CRITICAL_STATUSES = {'critical_low', 'critical_high'}


def load_data():
    """Load and join QC results → link table → injection history."""

    qc = pd.read_csv(QC_RESULTS)
    link = pd.read_excel(LINK_TABLE)          # columns: ID, PAT_N, index
    inj = pd.read_excel(INJECTION_XLS)

    # Build join key: CT_QUALITY_{ct_id}
    qc['_link_id'] = 'CT_QUALITY_' + qc['ct_id'].astype(str)

    # Merge QC → link table
    merged = qc.merge(
        link.rename(columns={'ID': '_link_id', 'index': 'injection_index'}),
        on='_link_id', how='left'
    )

    return merged, inj


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
    merged, inj = load_data()

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

        result = evaluator.evaluate(patient_data)

        card = result.get('card', {})
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
            'rca_title':          card.get('title', ''),
            'rca_explanation':    card.get('explanation', ''),
            'rca_impact':         card.get('impact', ''),
            'rca_recommendations': ' | '.join(card.get('recommendations', [])),
            'rca_success':        result.get('success', False),
            # Calculated variables (for debugging)
            'rca_variables':      str(result.get('calculated_variables', {})),
            # Decision path summary
            'rca_decision_path':  ' → '.join(
                f"{s['node']}({'Y' if s['result'] else 'N'})"
                for s in result.get('decision_path', [])
            ),
        })

    out_df = pd.DataFrame(rows)
    out_df.to_csv(output_path, index=False)
    print(f"Saved {len(out_df)} results to {output_path}")

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
