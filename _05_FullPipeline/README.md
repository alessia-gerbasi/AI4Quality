# Full pipeline delivery

This folder provides:

- `run_pipeline.py`: readable, editable end-to-end runner.
- `Dockerfile`: reproducible container image.
- `.dockerignore`: keeps datasets and generated outputs out of the image.

The input is a DICOM exam folder or a folder containing `CT_QUALITY_*` exam folders, plus `Injection History Anonymized.xlsx` and `link_anonymization.xlsx`. The runner performs preprocessing, TotalSegmentator conversion/segmentation, QC, all four RCA schemas, SQLite construction, and LLM recommendations.

The included example test input is:

```text
/data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/1_dicom
/data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/0_files/Injection History Anonymized.xlsx
/data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/0_files/link_anonymization.xlsx
```

## Give this to external users

Distribute these files:

- `ai4quality-full-pipeline.tar`, exported from the built Podman image.
- This `README.md`.
- The two Excel files, if you want to provide your own data/linkage templates:
  `Injection History Anonymized.xlsx` and `link_anonymization.xlsx`.

Do not distribute your conda environment, project output folders, model cache, or patient data unless intentionally required. The external user supplies their own DICOM data and output folder.

The external computer needs:

- Podman, or Docker with permission to access its daemon.
- NVIDIA drivers and GPU container support for GPU segmentation, or a CPU-capable setup using `--device cpu`.
- Ollama running on the host with the `qwen2.5:7b` model:

```bash
ollama pull qwen2.5:7b
ollama serve
```

The link workbook must contain `ID`, `PAT_N`, and `index`. The injection workbook must contain `index`, `Patient Id`, `Order Procedure`, and the injector/patient metadata columns used by RCA.

Export the image for delivery:

```bash
podman save -o ai4quality-full-pipeline.tar ai4quality-full-pipeline
```

The external user imports it with:

```bash
podman load -i ai4quality-full-pipeline.tar
```

Their input should look like this:

```text
my_input/
  CT_QUALITY_123_patient/
    studyinstanceuid/
      ... DICOM files ...
my_output/
model_cache/
Injection History Anonymized.xlsx
link_anonymization.xlsx
```

They then run the complete pipeline without using a dashboard button:

```bash
mkdir -p /absolute/path/my_output /absolute/path/model_cache

podman run --rm \
  --network host \
  -v /absolute/path/my_input:/input:ro \
  -v "/absolute/path/Injection History Anonymized.xlsx:/input/injection.xlsx:ro" \
  -v /absolute/path/link_anonymization.xlsx:/input/link.xlsx:ro \
  -v /absolute/path/my_output:/output \
  -v /absolute/path/model_cache:/root/.cache \
  -e OLLAMA_URL=http://127.0.0.1:11434/api/generate \
  ai4quality-full-pipeline \
  --input /input \
  --injection-xlsx /input/injection.xlsx \
  --link-xlsx /input/link.xlsx \
  --output /output \
  --device cpu \
  --serve
```

The dashboard opens at `http://localhost:8506` after processing. Results remain in `my_output`, including CSV summaries, QC images, RCA results, SQLite, and stored LLM recommendations. For selected exams, add `--ct-ids 1 4` or the relevant IDs at the end of the command.

For Docker, use the same image and mounts after changing `podman` to `docker`. Docker may require administrator setup; rootless Podman does not. The image packages dependencies and code but does not provide source-code secrecy: anyone with access to the image can inspect its layers.

## Debug version

Use the project environment so the code and intermediate files are easy to inspect:

```bash
cd /data/alessia.gerbasi/AI4Quality
OLLAMA_URL=http://localhost:11434/api/generate \
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python \
_05_FullPipeline/run_pipeline.py \
  --input /data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/1_dicom \
  --injection-xlsx "/data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/0_files/Injection History Anonymized.xlsx" \
  --link-xlsx /data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/0_files/link_anonymization.xlsx \
  --output /data/alessia.gerbasi/AI4Quality/_05_FullPipeline/test_2cases/debug_output \
  --ct-ids 1 4 \
  --device cpu
```

For a small run, use `--ct-ids 472`. Use `--skip-segmentation` only when the required `CT.nii.gz` files and ROI masks already exist in the configured NIfTI tree.

The debug runner leaves readable CSV files, logs, RCA outputs, SQLite, and generated recommendations in the selected output folder.

## Docker or rootless Podman

Choose either Docker or Podman. Docker uses the system daemon and may require an administrator to add your user to the `docker` group. Podman runs rootlessly and does not require administrator access.

### Docker build

```bash
cd /data/alessia.gerbasi/AI4Quality
docker build -f _05_FullPipeline/Dockerfile -t ai4quality-full-pipeline .
```

### Docker run

Run the included two-case example. The input folder and Excel files are mounted read-only; results are written to a separate host output folder:

```bash
mkdir -p /data/alessia.gerbasi/AI4Quality/_05_FullPipeline/test_2cases/docker_model_cache

docker run --rm --gpus all \
  -p 8506:8506 \
  -v /data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/1_dicom:/input:ro \
  -v "/data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/0_files/Injection History Anonymized.xlsx:/input/injection.xlsx:ro" \
  -v /data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/0_files/link_anonymization.xlsx:/input/link.xlsx:ro \
  -v /data/alessia.gerbasi/AI4Quality/_05_FullPipeline/test_2cases/docker_output:/output \
  -v /data/alessia.gerbasi/AI4Quality/_05_FullPipeline/test_2cases/docker_model_cache:/root/.cache \
  --add-host=host.docker.internal:host-gateway \
  -e OLLAMA_URL=http://host.docker.internal:11434/api/generate \
  ai4quality-full-pipeline \
  --input /input --injection-xlsx /input/injection.xlsx --link-xlsx /input/link.xlsx --output /output --device gpu --ct-ids 1 4 --serve
```

On a CPU-only machine, remove `--gpus all` and change `--device gpu` to `--device cpu`.

### Podman build

```bash
cd /data/alessia.gerbasi/AI4Quality
podman build -f _05_FullPipeline/Dockerfile -t ai4quality-full-pipeline .
```

### Podman run without administrator access

This CPU command is the most portable rootless option:

```bash
mkdir -p /data/alessia.gerbasi/AI4Quality/_05_FullPipeline/test_2cases/podman_output
mkdir -p /data/alessia.gerbasi/AI4Quality/_05_FullPipeline/test_2cases/podman_model_cache

podman run --rm \
  --network host \
  -v /data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/1_dicom:/input:ro \
  -v "/data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/0_files/Injection History Anonymized.xlsx:/input/injection.xlsx:ro" \
  -v /data/alessia.gerbasi/DATA/CDI_NEXO_072026/3_TEST/0_files/link_anonymization.xlsx:/input/link.xlsx:ro \
  -v /data/alessia.gerbasi/AI4Quality/_05_FullPipeline/test_2cases/podman_output:/output \
  -v /data/alessia.gerbasi/AI4Quality/_05_FullPipeline/test_2cases/podman_model_cache:/root/.cache \
  -e OLLAMA_URL=http://127.0.0.1:11434/api/generate \
  ai4quality-full-pipeline \
  --input /input --injection-xlsx /input/injection.xlsx --link-xlsx /input/link.xlsx --output /output --device cpu --ct-ids 1 4 --serve
```

Ollama must be running on the host with the selected model installed. On Linux, this command uses host networking because Ollama listens on `127.0.0.1:11434`; therefore the dashboard is available at `http://localhost:8506` after the pipeline completes. GPU Podman execution depends on NVIDIA CDI configuration; if available, add `--device nvidia.com/gpu=all` and use `--device gpu` in the container arguments.

The cache mount keeps TotalSegmentator model weights on the host, so later containers reuse them instead of downloading them again. The cache mount must be specified when the container starts; it cannot be added to a container that is already running. If a run is already downloading models, let it finish or stop it with `Ctrl+C`, then restart with the cache mount.

## Rebuild after changes

The image does not update automatically. After changing code, configs, or dependencies:

```bash
cd /data/alessia.gerbasi/AI4Quality
  docker build --no-cache -f _05_FullPipeline/Dockerfile -t ai4quality-full-pipeline .
```

For Podman, replace `docker` with `podman`:

```bash
podman build --no-cache -f _05_FullPipeline/Dockerfile -t ai4quality-full-pipeline .
```

Use `--no-cache` when dependencies or Dockerfile steps changed; omit it for faster code-only rebuilds. The input and output data remain on the host through the mounts.

Docker and Podman provide packaging and dependency isolation, not source-code protection. Anyone with access to an image can inspect its layers.

## Notes

The current legacy RCA and database modules use project-default paths internally. `run_pipeline.py` synchronizes staged preprocessing and QC outputs into those paths inside the container before running downstream stages. The container is isolated, so this does not alter the host repository.
