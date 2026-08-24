#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import pydicom

# =====================================================
# INSERISCI QUI LE SERIE DA CONTROLLARE
# =====================================================

SERIES_DIRS = [

    "/data/alessia.gerbasi/DATA/CDI_NEXO_072026/1_dicom/CT_QUALITY_6_margaret_jones/studyinstanceuid/12_arteriosa__2_0__i30f__3",

    "/data/alessia.gerbasi/DATA/CDI_NEXO_072026/1_dicom/CT_QUALITY_6_margaret_jones/studyinstanceuid/13_venosa__2_0__i30f__3",

]

# =====================================================


def parse_tm(tm_value):
    """
    Converte un TM DICOM tipo:
    085824.209009
    in datetime.time utilizzabile
    """

    s = str(tm_value)

    if "." in s:
        main, frac = s.split(".")
    else:
        main, frac = s, "0"

    main = main.zfill(6)

    hh = int(main[0:2])
    mm = int(main[2:4])
    ss = int(main[4:6])

    micro = int((frac + "000000")[:6])

    return datetime(
        1900,
        1,
        1,
        hh,
        mm,
        ss,
        micro
    )


for series_dir in SERIES_DIRS:

    series_dir = Path(series_dir)

    if not series_dir.exists():
        print(f"\n[ERROR] Directory not found: {series_dir}")
        continue

    files = [f for f in series_dir.iterdir() if f.is_file()]

    if not files:
        print(f"\n[ERROR] No files found in: {series_dir}")
        continue

    ds = pydicom.dcmread(
        str(files[0]),
        stop_before_pixels=True,
        force=True
    )

    acquisition_time = getattr(
        ds,
        "AcquisitionTime",
        None
    )

    bolus_start = getattr(
        ds,
        "ContrastBolusStartTime",
        None
    )

    bolus_stop = getattr(
        ds,
        "ContrastBolusStopTime",
        None
    )

    print("\n" + "=" * 80)
    print("SERIES:", getattr(ds, "SeriesDescription", "N/A"))
    print("PATH  :", series_dir)

    print("AcquisitionTime      :", acquisition_time)
    print("ContrastBolusStart   :", bolus_start)
    print("ContrastBolusStop    :", bolus_stop)

    if acquisition_time and bolus_start:

        try:
            acq_dt = parse_tm(acquisition_time)
            start_dt = parse_tm(bolus_start)

            delay_sec = (
                acq_dt - start_dt
            ).total_seconds()

            print(
                f"Delay from injection start: "
                f"{delay_sec:.2f} s"
            )

        except Exception as e:
            print(
                f"Cannot compute delay: {e}"
            )

    else:

        print(
            "Cannot compute delay "
            "(missing ContrastBolusStartTime)"
        )