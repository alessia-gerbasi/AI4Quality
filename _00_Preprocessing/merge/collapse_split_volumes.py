from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from merge.collapsed_volume_writer import write_collapsed_volumes


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write collapsed NIfTI volumes for merged split series from an existing decisions CSV."
    )
    parser.add_argument(
        "--decisions-csv",
        default=None,
        help="Path to the decisions.csv file produced by preprocessing.",
    )
    parser.add_argument(
        "--ct-ids",
        default=None,
        help="Optional comma-separated CT ids to process.",
    )
    parser.add_argument(
        "--max-groups",
        type=int,
        default=None,
        help="Optional cap on the number of merge groups to process.",
    )
    parser.add_argument(
        "--include-rejected",
        action="store_true",
        help="Include rejected merged rows instead of limiting to accepted rows.",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Overwrite existing *_collapsed.nii.gz files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the execution summary as JSON.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    if args.decisions_csv:
        decisions_path = Path(args.decisions_csv)
    else:
        # Prefer new output folder naming, keep compatibility with older runs.
        candidate_paths = [
            ROOT / "OUTPUTS" / "decisions.csv",
            ROOT / "artifacts" / "decisions.csv",
        ]
        decisions_path = next((p for p in candidate_paths if p.exists()), candidate_paths[0])

    if not decisions_path.exists():
        raise SystemExit(f"decisions CSV not found: {decisions_path}")

    df = pd.read_csv(decisions_path)
    decision_rows = df.to_dict(orient="records")

    ct_ids = None
    if args.ct_ids:
        ct_ids = {item.strip() for item in args.ct_ids.split(",") if item.strip()}

    report = write_collapsed_volumes(
        decision_rows,
        enabled=True,
        only_accepted=not args.include_rejected,
        skip_existing=not args.no_skip_existing,
        include_ct_ids=ct_ids,
        max_groups=args.max_groups,
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"groups_detected={report['groups_detected']}")
        print(f"groups_considered={report['groups_considered']}")
        print(f"volumes_written={report['volumes_written']}")
        print(f"volumes_skipped_existing={report['volumes_skipped_existing']}")
        print(f"errors={len(report['errors'])}")
        for item in report.get("written_files", []):
            print(item)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
