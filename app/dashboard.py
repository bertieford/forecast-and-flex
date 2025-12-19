from __future__ import annotations

import math

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from app.data import load_forecast_df, load_metrics_df


st.set_page_config(page_title="Energy Demand Forecast", layout="wide")

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
        html, body, [class*="css"]  {
            font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
        }
        .block-container {
            padding-top: 2.2rem;
            padding-bottom: 4rem;
        }
        .hero {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        .hero-icon {
            background: #2352f3;
            color: white;
            width: 56px;
            height: 56px;
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            box-shadow: 0 16px 24px rgba(35, 82, 243, 0.18);
        }
        .hero-title {
            font-size: 30px;
            font-weight: 700;
            margin-bottom: 0.1rem;
        }
        .hero-subtitle {
            color: #6b7280;
            font-size: 16px;
        }
        .card {
            background: #ffffff;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 18px;
            padding: 1.2rem 1.3rem;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        }
        .metric-label {
            color: #6b7280;
            font-size: 14px;
            margin-bottom: 0.6rem;
        }
        .metric-value {
            font-size: 26px;
            font-weight: 700;
            color: #0f172a;
        }
        .soft-panel {
            background: #f8fafc;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 20px;
            padding: 1.5rem;
        }
        .segment-card {
            border-radius: 18px;
            padding: 1.2rem 1.4rem;
            border: 1px solid rgba(0,0,0,0.08);
        }
        .segment-title {
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        .segment-value {
            font-size: 26px;
            font-weight: 700;
        }
        .segment-sub {
            color: #6b7280;
            margin-top: 0.25rem;
        }
        .panel-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 0.35rem;
        }
        .panel-subtitle {
            color: #6b7280;
            margin-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def _normalize(series: np.ndarray) -> np.ndarray:
    total = series.sum()
    return series / total if total else series


def build_hourly_forecast(
    weekend: bool,
    month: str,
    max_temp: float,
    feels_like: float,
    wind_speed: float,
    humidity: float,
    residential_customers: int,
    commercial_customers: int,
    industrial_customers: int,
) -> pd.DataFrame:
    hours = np.arange(24)

    base = 0.4 + 0.7 * np.exp(-((hours - 8) / 3.4) ** 2) + 1.1 * np.exp(
        -((hours - 18) / 4.2) ** 2
    )
    base = _normalize(base)

    res_profile = _normalize(base + 0.3 * np.exp(-((hours - 20) / 2.5) ** 2))
    comm_profile = _normalize(0.2 + 1.2 * np.exp(-((hours - 13) / 3.6) ** 2))
    ind_profile = _normalize(0.85 + 0.1 * np.cos((hours - 4) * 0.3))

    temp_delta = 16 - max_temp
    weather_factor = 1.0 + np.clip(temp_delta * 0.025, -0.12, 0.35)
    feels_factor = 1.0 + np.clip((16 - feels_like) * 0.015, -0.08, 0.2)
    wind_factor = 1.0 + np.clip(wind_speed * 0.01, 0.0, 0.15)
    humidity_factor = 1.0 + np.clip((humidity - 55) * 0.002, -0.05, 0.12)

    seasonal_factor = {
        "January": 1.12,
        "February": 1.08,
        "March": 1.03,
        "April": 0.98,
        "May": 0.95,
        "June": 0.97,
        "July": 1.04,
        "August": 1.06,
        "September": 1.0,
        "October": 1.03,
        "November": 1.07,
        "December": 1.15,
    }[month]

    res_scale = weather_factor * feels_factor * seasonal_factor
    comm_scale = (weather_factor * 0.8 + 0.2) * seasonal_factor
    ind_scale = 0.95 * seasonal_factor

    if weekend:
        res_scale *= 1.08
        comm_scale *= 0.78
        ind_scale *= 0.9

    res_daily = residential_customers * 12.0 * res_scale
    comm_daily = commercial_customers * 32.0 * comm_scale
    ind_daily = industrial_customers * 70.0 * ind_scale

    df = pd.DataFrame(
        {
            "hour": hours,
            "Residential": res_profile * res_daily,
            "Commercial": comm_profile * comm_daily,
            "Industrial": ind_profile * ind_daily,
        }
    )
    df["Total"] = df[["Residential", "Commercial", "Industrial"]].sum(axis=1)
    df["label"] = df["hour"].apply(lambda h: f"{h:02d}:00")
    return df


header_col, _ = st.columns([0.8, 0.2])
with header_col:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-icon">⚡️</div>
            <div>
                <div class="hero-title">Energy Demand Forecast</div>
                <div class="hero-subtitle">24-Hour Consumption Prediction Dashboard</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown("##")

left, right = st.columns([0.35, 0.65], gap="large")

with left:
    st.markdown('<div class="soft-panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Time Parameters</div>', unsafe_allow_html=True)
    weekend = st.toggle("Weekend", value=False)
    month = st.selectbox(
        "Month",
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        index=11,
    )

    st.markdown('<div class="panel-title" style="margin-top:1rem;">Weather Forecast</div>', unsafe_allow_html=True)
    max_temp = st.slider("Max Temperature (°C)", -5.0, 35.0, 6.0, 0.5)
    feels_like = st.slider("Feels Like (°C)", -10.0, 30.0, 3.0, 0.5)
    wind_speed = st.slider("Wind Speed (km/h)", 0.0, 50.0, 12.0, 1.0)
    humidity = st.slider("Humidity (%)", 10.0, 100.0, 68.0, 1.0)

    st.markdown('<div class="panel-title" style="margin-top:1rem;">Customer Segments</div>', unsafe_allow_html=True)
    residential_customers = st.number_input(
        "Segment A (Residential)",
        min_value=500,
        max_value=15000,
        value=5000,
        step=100,
    )
    commercial_customers = st.number_input(
        "Segment B (Commercial)",
        min_value=100,
        max_value=5000,
        value=1200,
        step=50,
    )
    industrial_customers = st.number_input(
        "Segment C (Industrial)",
        min_value=50,
        max_value=2000,
        value=300,
        step=25,
    )
    st.markdown("</div>", unsafe_allow_html=True)


forecast = build_hourly_forecast(
    weekend=weekend,
    month=month,
    max_temp=max_temp,
    feels_like=feels_like,
    wind_speed=wind_speed,
    humidity=humidity,
    residential_customers=residential_customers,
    commercial_customers=commercial_customers,
    industrial_customers=industrial_customers,
)

total_daily = forecast["Total"].sum()
avg_hourly = forecast["Total"].mean()
peak_idx = forecast["Total"].idxmax()
peak_hour = forecast.loc[peak_idx, "label"]
peak_value = forecast.loc[peak_idx, "Total"]
total_customers = residential_customers + commercial_customers + industrial_customers
col_a, col_b, col_c, col_d = st.columns(4)
metric_items = [
    ("Total Daily Consumption", f"{total_daily:,.0f} kWh"),
    ("Peak Hour", f"{peak_hour} ({peak_value:,.0f} kWh)"),
    ("Avg Hourly Consumption", f"{avg_hourly:,.0f} kWh"),
    ("Total Customers", f"{total_customers:,} accounts"),
]
for col, (label, value) in zip([col_a, col_b, col_c, col_d], metric_items):
    col.markdown(
        f"""
        <div class="card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="panel-title">24-Hour Consumption Forecast</div>'
        '<div class="panel-subtitle">Predicted energy consumption by hour and customer segment</div>',
        unsafe_allow_html=True,
    )

    chart_data = forecast.melt(
        id_vars=["hour", "label"],
        value_vars=["Total", "Residential", "Commercial", "Industrial"],
        var_name="Segment",
        value_name="kwh",
    )

    color_scale = alt.Scale(
        domain=["Total", "Residential", "Commercial", "Industrial"],
        range=["#2F6CF6", "#22C55E", "#F59E0B", "#EF4444"],
    )

    chart = (
        alt.Chart(chart_data)
        .mark_line(strokeWidth=3, interpolate="monotone")
        .encode(
            x=alt.X("hour:Q", axis=alt.Axis(labelExpr="datum.value + ':00'", title="Hour")),
            y=alt.Y("kwh:Q", axis=alt.Axis(title="kWh")),
            color=alt.Color("Segment:N", scale=color_scale, legend=alt.Legend(title=None)),
        )
        .properties(height=340)
    )

    st.altair_chart(chart, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


st.markdown("##")
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(
    '<div class="panel-title">Segment Breakdown</div>'
    '<div class="panel-subtitle">Daily consumption by customer segment</div>',
    unsafe_allow_html=True,
)

seg_cols = st.columns(3)
segment_totals = {
    "Segment A (Residential)": ("#ECFDF3", "#22C55E", forecast["Residential"].sum(), residential_customers),
    "Segment B (Commercial)": ("#FFFBEB", "#F59E0B", forecast["Commercial"].sum(), commercial_customers),
    "Segment C (Industrial)": ("#FEF2F2", "#EF4444", forecast["Industrial"].sum(), industrial_customers),
}

for col, (label, (bg, dot, total, customers)) in zip(seg_cols, segment_totals.items()):
    col.markdown(
        f"""
        <div class="segment-card" style="background:{bg}; border-color:{dot}33;">
            <div class="segment-title" style="color:{dot}; display:flex; justify-content:space-between;">
                <span>{label}</span>
                <span style="font-size:14px;">●</span>
            </div>
            <div class="segment-value">{total:,.0f} kWh</div>
            <div class="segment-sub">{customers:,} customers</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)


with st.expander("Historical SARIMA Forecast (Daily Aggregate)"):
    try:
        forecast_df = load_forecast_df()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    metrics_df = None
    try:
        metrics_df = load_metrics_df()
    except FileNotFoundError:
        metrics_df = None

    min_date = forecast_df["day"].min()
    max_date = forecast_df["day"].max()
    selected_range = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="history_range",
    )
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date = selected_range
        end_date = selected_range

    filtered = forecast_df[
        (forecast_df["day"] >= start_date) & (forecast_df["day"] <= end_date)
    ].sort_values("day")

    if filtered.empty:
        st.warning("No data available for the selected date range.")
    else:
        filtered["abs_error"] = (
            filtered["forecast_energy_sum"] - filtered["actual_energy_sum"]
        ).abs()
        filtered["ape"] = (
            filtered["abs_error"] / filtered["actual_energy_sum"].replace(0, pd.NA)
        ).astype(float)

        mape = float(filtered["ape"].mean(skipna=True) * 100)
        mae = float(filtered["abs_error"].mean())

        st.caption(f"MAE: {mae:,.2f} | MAPE: {mape:,.2f}%")
        st.line_chart(
            filtered.set_index("day")[["actual_energy_sum", "forecast_energy_sum"]],
            use_container_width=True,
        )
        st.bar_chart(filtered.set_index("day")[["abs_error"]], use_container_width=True)
        if metrics_df is not None and not metrics_df.empty:
            st.dataframe(metrics_df, use_container_width=True)
