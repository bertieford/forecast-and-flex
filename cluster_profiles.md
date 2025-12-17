# Cluster Load Profiles (Pre-model Sanity Check)

Generates average weekday/weekend half-hourly load profiles per cluster for a subset of households to validate clustering and create storytelling assets.

## Inputs
- CSV with columns: `household_id`, `cluster_id`, `timestamp`, `consumption_kwh`.
- Optional filters: cluster ids, date range, household sample size.

## Usage
1) Install deps (suggested venv):
   ```bash
   pip install -r requirements.txt
   ```
2) Run:
   ```bash
   python scripts/cluster_profiles.py \
     --consumption-csv data/raw/consumption.csv \
     --sample-households 500 \
     --clusters 1,2,3 \
     --start-date 2024-01-01 \
     --end-date 2024-02-01
   ```
   Flags are optional; omit to use all data.

## Outputs
- CSV/JSON: `outputs/cluster_profiles/profiles_<date>.csv|json`
  - Columns: `cluster_id`, `slot` (0–47), `weekday_kwh`, `weekend_kwh`.
- Plots: `outputs/cluster_profiles/plots/cluster_<id>.png` (weekday vs weekend curves).

## Notes
- Assumes half-hourly aligned timestamps (minute 0 or 30); misaligned rows are dropped.
- Random household sampling is reproducible (`random_state=42`).
- Extend easily to add histograms or per-household spot checks if needed.
