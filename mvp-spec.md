# MVP v0: Segment-Based Day-Ahead Demand Forecast

## Goals
- Produce day-ahead, half-hourly demand forecasts at the customer-cluster level.
- Keep the implementation minimal: reproducible scripts, simple data inputs/outputs.
- Enable quick iteration on model choice (ARIMA baseline) and exogenous features.

## Inputs
- Household half-hourly consumption for the past N days (CSV/Parquet).
- Weather forecast for tomorrow: min temp, max temp (optionally full hourly series).
- Calendar features for tomorrow: weekday/weekend, holiday flag.
- Precomputed cluster assignment per household (one cluster id per household).
- Configuration: N (history window), ARIMA order defaults, output paths, email settings.

## Processing Pipeline
1) Ingest & clean
   - Load consumption data; validate 48 records per day per household; drop/flag gaps.
   - Align timezones and daylight-saving shifts to a consistent UTC or local standard.
2) Aggregate to clusters
   - Map each household to its cluster id.
   - Sum or average consumption per cluster per half-hour to build cluster-level series.
   - Optionally normalize by household count in cluster for comparability.
3) Feature assembly
   - Build tomorrow exogenous regressor vector: min/max temp (and optionally hourly temps), weekday/weekend, holiday flag.
   - Create seasonal dummies if needed (hour-of-day, month).
4) Train models
   - For each cluster, fit/refresh an ARIMA (or SARIMA) model on the aggregated history.
   - Include exogenous regressors if available; fallback to univariate ARIMA when missing.
   - Use rolling or expanding window on past N days; persist fitted params per cluster.
5) Forecast
   - Generate 48-step forecasts for each cluster for tomorrow.
   - Optionally compute uncertainty bands (prediction intervals) from the model.
6) Output assembly
   - For each cluster, package predictions (and intervals) into CSV and JSON.
   - Optionally render and email a plot (PNG/PDF) of forecast vs. recent history.

## Outputs
- Per-cluster 48 half-hour demand predictions for tomorrow.
- Optional uncertainty bands (lower/upper) per timestep.
- Saved formats:
  - CSV (cluster_id, timestamp, forecast, lower?, upper?).
  - JSON (same fields).
  - Optional emailed plot per cluster (forecast + history + intervals).

## Operational Notes
- Minimal CLI: `python forecast.py --config config.yaml --date 2024-12-17`.
- Logging and basic metrics: MAPE/RMSE on a holdout day; save per-cluster fit diagnostics.
- Storage layout suggestion:
  - `data/raw/consumption/`, `data/raw/weather/`, `data/interim/cluster_series/`.
  - `models/arima/<cluster_id>.pkl`, `forecasts/<date>/cluster_<id>.csv|json`.
- Edge cases: missing households in a cluster, short history (< N days), and flat consumption; handle with defaults and warnings.
