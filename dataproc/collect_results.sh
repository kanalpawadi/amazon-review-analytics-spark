#!/usr/bin/env bash
# Collect all full-scale results from the bucket into results_full.zip (run in Cloud Shell).
# Then: Cloud Shell More (⋮) -> Download -> results_full.zip, unzip it, and copy the folders
#       results_full\scalability  and  results_full\full  into  D:\PROJECTS\BIG_DATA_project\dashboard\dashboard_data\
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

rm -rf ~/results_full && mkdir -p ~/results_full/scalability/runs
gcloud storage cp -r "$BUCKET/results/full" ~/results_full/ 2>/dev/null || echo "(no full-scale results yet)"
gcloud storage cp "$BUCKET/results/scalability/runs/*.json" ~/results_full/scalability/runs/ 2>/dev/null \
    || echo "(no scalability runs yet)"

# one CSV for the dashboard: data_fraction, cores, step, seconds, rows
python3 - <<'PY'
import csv, glob, json, os
rows = []
for f in sorted(glob.glob(os.path.expanduser("~/results_full/scalability/runs/*.json"))):
    r = json.load(open(f))
    for step, sec in r["steps"].items():
        rows.append({"data_fraction": r["data_fraction"], "cores": r["cores"], "step": step,
                     "seconds": sec, "rows": r["rows"].get(step, "")})
out = os.path.expanduser("~/results_full/scalability/scalability_runs.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["data_fraction", "cores", "step", "seconds", "rows"])
    w.writeheader(); w.writerows(rows)
print(f"{len(rows)} scalability rows -> {out}")
PY

cd ~ && rm -f results_full.zip && zip -qr results_full.zip results_full
ls -lh ~/results_full.zip
echo "Download it: Cloud Shell More (⋮) -> Download -> results_full.zip"
