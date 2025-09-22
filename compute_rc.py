#!/usr/bin/env python3
import csv
from pathlib import Path
from statistics import median

INPUT = Path("complexity_raw.csv")
OUTPUT = Path("complexity_summary.csv")

# Definisikan baseline per grup:
BASELINE = {
    "entropy": "CAVLC + dia + p16x16",
    "me":      "CABAC + diamond + p16x16",
    "part":    "CABAC + dia + p16x16",
}

rows = []
with INPUT.open() as f:
    r = csv.DictReader(f)
    for row in r:
        rows.append(row)

# grupkan per (clip_id, group)
from collections import defaultdict
grp = defaultdict(list)
for row in rows:
    key = (row["clip_id"], row["group"])
    grp[key].append(row)

out = []
for key, items in grp.items():
    clip_id, group = key
    # cari baseline item
    base_name = BASELINE[group]
    base_items = [it for it in items if it["name"]==base_name]
    if not base_items:
        # kalau tak ada, lewati grup ini
        continue
    base = base_items[0]
    try:
        base_tpmpf = float(base["time_per_MP_per_frame_ms"])
    except:
        base_tpmpf = None

    for it in items:
        try:
            tpmpf = float(it["time_per_MP_per_frame_ms"])
        except:
            tpmpf = None
        if tpmpf and base_tpmpf and base_tpmpf>0:
            rc = 100.0 * tpmpf / base_tpmpf
        else:
            rc = ""
        out.append({
            "clip_id": clip_id,
            "group": group,
            "name": it["name"],
            "width": it["width"],
            "height": it["height"],
            "frames": it["frames"],
            "time_per_frame_ms": it["time_per_frame_ms"],
            "time_per_MP_per_frame_ms": it["time_per_MP_per_frame_ms"],
            "RC_vs_baseline_%": f"{rc:.1f}" if isinstance(rc, float) else "",
            "bitrate_Mbps": it["bitrate_Mbps"],
            "psnr_dB": it["psnr_dB"],
        })

with OUTPUT.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

print(f"Rekap + RC → {OUTPUT}")
