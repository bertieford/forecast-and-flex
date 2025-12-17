"""
Compute and plot average weekday/weekend load profiles per cluster.

Expected input CSV columns:
  - household_id
  - cluster_id
  - timestamp (ISO8601, half-hourly)
  - consumption_kwh (float)

Outputs:
  - CSV: outputs/cluster_profiles/profiles_<date>.csv
  - JSON: outputs/cluster_profiles/profiles_<date>.json
  - Plots: outputs/cluster_profiles/plots/cluster_<id>.png
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build cluster load profiles.")
    parser.add_argument(
        "--consumption-csv",
        type=Path,
        required=False,
        help="Path to household consumption CSV.",
    )
    parser.add_argument(
        "--sample-households",
        type=int,
        default=None,
        help="Random sample size of households to include (None = all).",
    )
    parser.add_argument(
        "--clusters",
        type=str,
        default=None,
        help="Comma-separated cluster ids to include (optional).",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Filter records from this date (YYYY-MM-DD, optional).",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Filter records up to this date inclusive (YYYY-MM-DD, optional).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/cluster_profiles"),
        help="Base output directory.",
    )
    parser.add_argument(
        "--lcl-info-csv",
        type=Path,
        required=False,
        help="(LCL dataset) Path to informations_households.csv.",
    )
    parser.add_argument(
        "--lcl-blocks-dir",
        type=Path,
        required=False,
        help="(LCL dataset) Directory containing block_*.csv files.",
    )
    parser.add_argument(
        "--lcl-cluster-col",
        type=str,
        default="Acorn_grouped",
        help="Info CSV column to use as cluster id (default: Acorn_grouped).",
    )
    return parser.parse_args()


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"household_id", "cluster_id", "timestamp", "consumption_kwh"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp", "consumption_kwh", "cluster_id", "household_id"])
    return df


def load_lcl_dataset(
    info_csv: Path,
    blocks_dir: Path,
    cluster_col: str,
    sample_households: Optional[int],
    clusters: Optional[Iterable[str]],
    start_date: Optional[str],
    end_date: Optional[str],
) -> pd.DataFrame:
    info = pd.read_csv(info_csv, encoding="latin1")
    required_info_cols = {"LCLid", "file", cluster_col}
    missing = required_info_cols - set(info.columns)
    if missing:
        raise ValueError(f"Missing columns in info CSV {info_csv}: {missing}")
    if clusters:
        info = info[info[cluster_col].astype(str).isin({str(c) for c in clusters})]
    if info.empty:
        raise SystemExit("No households remain after filtering by cluster.")
    if sample_households:
        info = info.sample(n=min(sample_households, len(info)), random_state=42)
    households = info["LCLid"].unique()
    blocks = info.groupby("file")["LCLid"].apply(set).to_dict()
    frames = []
    for block_file, ids in blocks.items():
        block_path = blocks_dir / f"{block_file}.csv"
        if not block_path.exists():
            print(f"Warning: block file missing: {block_path}")
            continue
        df_block = pd.read_csv(block_path)
        df_block = df_block.rename(
            columns={
                "LCLid": "household_id",
                "tstp": "timestamp",
                "energy(kWh/hh)": "consumption_kwh",
            }
        )
        df_block = df_block[df_block["household_id"].isin(ids)]
        if df_block.empty:
            continue
        df_block["timestamp"] = pd.to_datetime(df_block["timestamp"], errors="coerce")
        df_block["consumption_kwh"] = pd.to_numeric(df_block["consumption_kwh"], errors="coerce")
        df_block = df_block.dropna(subset=["timestamp", "consumption_kwh"])
        df_block = df_block.merge(
            info[["LCLid", cluster_col]].rename(
                columns={"LCLid": "household_id", cluster_col: "cluster_id"}
            ),
            on="household_id",
            how="left",
        )
        if start_date:
            df_block = df_block[df_block["timestamp"] >= pd.to_datetime(start_date)]
        if end_date:
            df_block = df_block[df_block["timestamp"] <= pd.to_datetime(end_date) + pd.Timedelta(days=1)]
        frames.append(df_block)
    if not frames:
        raise SystemExit("No data loaded from blocks; check paths and filters.")
    return pd.concat(frames, ignore_index=True)


def filter_data(
    df: pd.DataFrame,
    sample_households: Optional[int],
    clusters: Optional[Iterable[str]],
    start_date: Optional[str],
    end_date: Optional[str],
) -> pd.DataFrame:
    if clusters:
        df = df[df["cluster_id"].astype(str).isin({str(c) for c in clusters})]
    if start_date:
        df = df[df["timestamp"] >= pd.to_datetime(start_date, utc=True)]
    if end_date:
        df = df[df["timestamp"] <= pd.to_datetime(end_date, utc=True) + pd.Timedelta(days=1)]
    if sample_households:
        households = df["household_id"].drop_duplicates()
        sample = households.sample(n=min(sample_households, len(households)), random_state=42)
        df = df[df["household_id"].isin(sample)]
    return df


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df["is_weekend"] = df["timestamp"].dt.dayofweek >= 5
    df["slot"] = df["timestamp"].dt.hour * 2 + (df["timestamp"].dt.minute // 30)
    # Filter out non half-hour aligned rows to avoid skewing averages.
    df = df[df["timestamp"].dt.minute.isin([0, 30])]
    return df


def compute_profiles(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["cluster_id", "is_weekend", "slot"])["consumption_kwh"]
        .mean()
        .reset_index()
        .rename(columns={"consumption_kwh": "avg_consumption_kwh"})
    )
    # Expand to wide format for easier plotting if needed.
    pivot = grouped.pivot_table(
        index=["cluster_id", "slot"],
        columns="is_weekend",
        values="avg_consumption_kwh",
    ).reset_index()
    pivot = pivot.rename(columns={False: "weekday_kwh", True: "weekend_kwh"})
    return pivot


def plot_profiles(profiles: pd.DataFrame, out_dir: Path) -> None:
    plot_dir = out_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    for cluster_id, group in profiles.groupby("cluster_id"):
        group = group.sort_values("slot")
        plt.figure(figsize=(10, 5))
        plt.plot(group["slot"], group["weekday_kwh"], label="Weekday")
        plt.plot(group["slot"], group["weekend_kwh"], label="Weekend")
        plt.title(f"Cluster {cluster_id}: Average Load Profile")
        plt.xlabel("Half-hour slot (0-47)")
        plt.ylabel("kWh")
        plt.xticks(ticks=range(0, 48, 4), labels=[f"{h:02d}:00" for h in range(0, 24, 2)])
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(plot_dir / f"cluster_{cluster_id}.png", dpi=150)
        plt.close()


def save_outputs(profiles: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d")
    csv_path = out_dir / f"profiles_{stamp}.csv"
    json_path = out_dir / f"profiles_{stamp}.json"
    profiles.to_csv(csv_path, index=False)
    profiles.to_json(json_path, orient="records", indent=2)
    print(f"Saved profiles to {csv_path} and {json_path}")


def main() -> None:
    args = parse_args()
    clusters = args.clusters.split(",") if args.clusters else None
    if args.lcl_info_csv and args.lcl_blocks_dir:
        df = load_lcl_dataset(
            info_csv=args.lcl_info_csv,
            blocks_dir=args.lcl_blocks_dir,
            cluster_col=args.lcl_cluster_col,
            sample_households=args.sample_households,
            clusters=clusters,
            start_date=args.start_date,
            end_date=args.end_date,
        )
    else:
        if not args.consumption_csv:
            raise SystemExit("Provide --consumption-csv or LCL dataset args.")
        df = load_data(args.consumption_csv)
        df = filter_data(df, args.sample_households, clusters, args.start_date, args.end_date)
    if df.empty:
        raise SystemExit("No data after filtering; check inputs.")
    df = add_time_features(df)
    profiles = compute_profiles(df)
    save_outputs(profiles, args.output_dir)
    plot_profiles(profiles, args.output_dir)
    print("Done.")


if __name__ == "__main__":
    main()
