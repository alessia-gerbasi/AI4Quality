"""Run AI4Quality end to end from mounted input files.

Inputs are a DICOM exam folder or a folder containing CT_QUALITY_* folders,
plus the two Excel files required for anonymization/injection enrichment.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "_05_FullPipeline" / "work"
PREPROCESSING_OUTPUT = WORK / "preprocessing"
NII_OUTPUT = WORK / "nifti"
QC_OUTPUT = WORK / "quality_check"


def run(command: list[str]) -> None:
    print("+", " ".join(str(part) for part in command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def write_configs(input_path: Path, injection_xlsx: Path, link_xlsx: Path, device: str) -> None:
    default = yaml.safe_load((ROOT / "_00_Preprocessing/config/defaults.yaml").read_text())
    default["io"]["dicom_roots"] = [str(input_path.resolve())]
    default["io"]["injection_history_xlsx"] = str(injection_xlsx.resolve())
    default["io"]["link_anonymization_xlsx"] = str(link_xlsx.resolve())
    default["io"]["output_dir"] = str(PREPROCESSING_OUTPUT.resolve())
    default["runtime"]["max_ct"] = None
    PREPROCESSING_OUTPUT.mkdir(parents=True, exist_ok=True)
    (WORK / "preprocessing.yaml").write_text(yaml.safe_dump(default, sort_keys=False))

    segmentation = yaml.safe_load((ROOT / "_01_Segmentation/config/defaults.yaml").read_text())
    segmentation["csv_path"] = str((PREPROCESSING_OUTPUT / "retained_series_unified_filtered.csv").resolve())
    segmentation["output_root"] = str(NII_OUTPUT.resolve())
    segmentation["device"] = device
    segmentation["log_file"] = str((WORK / "segmentation_run_log.jsonl").resolve())
    (WORK / "segmentation.yaml").write_text(yaml.safe_dump(segmentation, sort_keys=False))

    legacy_files = ROOT.parent / "DATA" / "CDI_NEXO_072026" / "0_files"
    legacy_files.mkdir(parents=True, exist_ok=True)
    shutil.copy2(injection_xlsx, legacy_files / "Injection History Anonymized.xlsx")
    shutil.copy2(link_xlsx, legacy_files / "link_anonymization.xlsx")


def copy_outputs(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for source_dir, target_dir in (
        (PREPROCESSING_OUTPUT, output_dir / "preprocessing"),
        (QC_OUTPUT, output_dir / "quality_check"),
        (ROOT / "_03_RootCauseAnalysis/results", output_dir / "rca"),
    ):
        if source_dir.exists():
            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
    for source in (
        ROOT / "_03_RootCauseAnalysis/rca_results.csv",
        ROOT / "_03_RootCauseAnalysis/rca_results_all.csv",
        ROOT / "_03_RootCauseAnalysis/rca_results_*.csv",
    ):
        for path in source.parent.glob(source.name):
            if path.exists():
                shutil.copy2(path, output_dir / "rca" / path.name)
    database = ROOT / "_04_Recommendations/data/ai4quality_recommendations.sqlite"
    if database.exists():
        shutil.copy2(database, output_dir / database.name)


def sync_preprocessing_output() -> None:
    shutil.copytree(PREPROCESSING_OUTPUT, ROOT / "_00_Preprocessing/OUTPUTS", dirs_exist_ok=True)


def sync_qc_output() -> None:
    shutil.copytree(QC_OUTPUT, ROOT / "_02_QualityCheck/OUTPUTS", dirs_exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="One CT_QUALITY_* folder or a folder containing exams")
    parser.add_argument("--injection-xlsx", type=Path, required=True)
    parser.add_argument("--link-xlsx", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("/output"))
    parser.add_argument("--device", default="cpu", help="Segmentation device: cpu, gpu, or gpu:N")
    parser.add_argument("--ct-ids", nargs="*", help="Optional CT IDs for a small/debug run")
    parser.add_argument("--skip-segmentation", action="store_true", help="Use only when NIfTI/masks already exist")
    parser.add_argument("--serve", action="store_true", help="Serve the recommendations dashboard after the run")
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(args.input)
    if not args.injection_xlsx.exists() or not args.link_xlsx.exists():
        raise FileNotFoundError("Both Excel inputs must exist")

    if WORK.exists():
        shutil.rmtree(WORK)
    if QC_OUTPUT.exists():
        shutil.rmtree(QC_OUTPUT)
    write_configs(args.input, args.injection_xlsx, args.link_xlsx, args.device)

    run([sys.executable, "_00_Preprocessing/main.py", "--config", str(WORK / "preprocessing.yaml")])
    sync_preprocessing_output()
    segmentation_command = [sys.executable, "_01_Segmentation/main.py", "--config", str(WORK / "segmentation.yaml")]
    if args.ct_ids:
        segmentation_command += ["--ct-ids", *args.ct_ids]
    if not args.skip_segmentation:
        run(segmentation_command)

    qc_command = [
        sys.executable, "_02_QualityCheck/main.py",
        "--csv", str(PREPROCESSING_OUTPUT / "retained_series_unified_filtered.csv"),
        "--rules", str(ROOT / "config/common/ct_protocols.yaml"),
        "--nii-root", str(NII_OUTPUT),
        "--output-dir", str(QC_OUTPUT),
    ]
    if args.ct_ids:
        qc_command += ["--ct-ids", *args.ct_ids]
    run(qc_command)
    sync_qc_output()

    for schema in ("dose_schema_v1", "other_schema_v1", "protocol_schema_v1", "timing_schema_v1"):
        run([sys.executable, "_03_RootCauseAnalysis/batch_analysis.py", "--schema", schema])

    run([sys.executable, "_04_Recommendations/generate_recommendations.py"])
    copy_outputs(args.output)
    print(f"Complete pipeline output: {args.output.resolve()}")

    if args.serve:
        run([sys.executable, "-m", "streamlit", "run", "_04_Recommendations/dashboard.py", "--server.address", "0.0.0.0", "--server.port", "8506"])


if __name__ == "__main__":
    main()
