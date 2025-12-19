## Quick modeling run (sampling for speed)

- Data: Kaggle smart meters (London) + DarkSky weather already in `data/raw/`.
- Clustering: sampled 1,200 household-days from first two hh blocks, normalized 48 half-hour slots, k=3 (Euclidean). Outputs saved locally:
  - `outputs/feature_extraction_sample.csv`
  - `outputs/cluster_shape_labels.csv`
  - `outputs/cluster_shape_centroids.png` (centroid plot)
- Forecast: simple weather regression (temp/humidity/wind) on aggregated daily energy (first 3 blocks, 2013). SARIMAX was unstable on the tiny slice, so regression used as a fallback.
  - MAE ≈ 160.59 on last 30 days (train 125 / test 30)
  - Files: `outputs/sarima_weather_forecast.csv`, `outputs/sarima_weather_metrics.csv`, `outputs/sarima_weather_forecast.png`
- Next steps: aggregate more blocks (e.g., 10–20) and retry SARIMAX `(0,1,1)x(0,1,1,7)` with weather; expect better stability/accuracy and a lower MAE.

Note: repo `.gitignore` skips data/CSV outputs; the CSVs above remain local only.
