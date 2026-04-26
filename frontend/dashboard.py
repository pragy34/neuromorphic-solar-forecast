import os
import sys
import json
import warnings
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

warnings.filterwarnings("ignore")
sys.path.append(os.path.abspath(".."))
import config

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="NeuroSpike — Solar Forecasting",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Modern Theme ───────────────────────────────────────────────────
st.markdown("""
<style>

.main {
    background-color: #0e1117;
}

.block-container {
    padding-top: 2rem;
}

h1, h2, h3 {
    color: #f5f5f5;
}

.stMetric {
    background-color: #161b22;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #30363d;
}

</style>
""", unsafe_allow_html=True)

# ── Paths ──────────────────────────────────────────────────────────
FEATURES_DIR = os.path.join("..", config.FEATURES_DATA_DIR)
METRICS_DIR = os.path.join("..", config.OUTPUTS_METRICS)
FORECAST_DIR = os.path.join("..", config.OUTPUTS_FORECASTS)

CITIES = list(config.CITIES.keys())
PANEL_EFFICIENCY = config.PANEL_EFFICIENCY
PANEL_AREA_M2 = config.PANEL_AREA_M2
API_URL = "http://localhost:8000"

CITY_DISPLAY = {c: c.replace("_", " ").title() for c in CITIES}

# ── Helper Functions ───────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_feature_data(city: str) -> pd.DataFrame:
    path = os.path.join(FEATURES_DIR, f"{city}_features.csv")
    df = pd.read_csv(path, index_col="datetime", parse_dates=True)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


@st.cache_data
def load_metrics() -> dict:
    results = {}
    for fname in ["baseline_results.csv", "lstm_results.csv", "snn_results.csv"]:
        path = os.path.join(METRICS_DIR, fname)
        if os.path.exists(path):
            results[fname.replace(".csv", "")] = pd.read_csv(path)
    return results


def call_api(city: str, horizon: int) -> dict:
    try:
        resp = requests.post(
            f"{API_URL}/forecast",
            json={"city": city, "horizon": horizon},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:

    st.markdown("## ⚙️ Settings")

    selected_city = st.selectbox(
        "Select City",
        options=CITIES,
        format_func=lambda x: CITY_DISPLAY[x],
        index=CITIES.index("new_delhi"),
    )

    selected_horizon = st.selectbox(
        "Forecast Horizon",
        options=[1, 6, 24],
        format_func=lambda x: f"{x} hour{'s' if x > 1 else ''} ahead",
    )

    n_panels = st.slider("Number of Solar Panels", 1, 1000, 100, step=10)

    panel_area = st.slider(
        "Panel Area (m² each)",
        min_value=0.5,
        max_value=4.0,
        value=float(PANEL_AREA_M2),
        step=0.1,
    )

    api_online = False
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        api_online = r.status_code == 200
    except Exception:
        pass

    if api_online:
        st.success("API Online")
    else:
        st.warning("API Offline — using stored forecasts")


# ── Hero Header ───────────────────────────────────────────────────
st.markdown("""
# ☀️ NeuroSpike Solar Intelligence Platform

Real-time Solar Irradiance Forecasting  
AI Powered — SNN + LSTM + XGBoost

---
""")

# ── KPI Cards ─────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

k1.metric("City", CITY_DISPLAY[selected_city])
k2.metric("Forecast Horizon", f"{selected_horizon} hr")
k3.metric("Panels", n_panels)
k4.metric("Efficiency", f"{PANEL_EFFICIENCY*100:.0f}%")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Forecast",
        "Model Performance",
        "City Comparison",
        "Power Output",
        "Data Explorer",
    ]
)

# ══════════════════════════════════════════════════════════════════
# TAB 1 — FORECAST
# ══════════════════════════════════════════════════════════════════
with tab1:

    st.subheader(f"Solar Forecast — {CITY_DISPLAY[selected_city]}")

    if st.button("Generate New Forecast"):

        with st.spinner("Running AI models..."):
            forecast_data = call_api(selected_city, selected_horizon)

        st.success("Forecast updated")

    forecast_data = None
    forecast_path = os.path.join(FORECAST_DIR, "all_forecasts.json")

    if api_online:
        forecast_data = call_api(selected_city, selected_horizon)

    if forecast_data is None and os.path.exists(forecast_path):

        with open(forecast_path) as f:
            all_f = json.load(f)

        city_f = all_f.get(selected_city, {})

        horizons_raw = {
            int(k): v for k, v in city_f.get("horizons", {}).items()
        }

        h_data = horizons_raw.get(selected_horizon, {})

        if h_data:
            forecast_data = {
                "city": selected_city,
                "horizon": selected_horizon,
                "timestamps": h_data["timestamps"],
                "ghi_wm2": h_data["ghi_wm2"],
                "power_watts": h_data["power_watts"],
            }

    if forecast_data:

        ghi_vals = np.array(forecast_data["ghi_wm2"])
        power_vals = np.array(forecast_data["power_watts"])
        times = forecast_data["timestamps"]

        scale = n_panels * (panel_area / PANEL_AREA_M2)
        power_total = power_vals * scale

        col1, col2, col3 = st.columns(3)

        col1.metric("Next Hour GHI", f"{ghi_vals[0]:.1f} W/m²")
        col2.metric("Power per Panel", f"{power_vals[0]:.1f} W")
        col3.metric(
            f"Total Power ({n_panels} panels)",
            f"{power_total[0]/1000:.2f} kW",
        )

        fig = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=("Solar Irradiance Forecast", "Expected Power Output"),
        )

        fig.add_trace(
            go.Scatter(
                x=times,
                y=ghi_vals,
                mode="lines+markers",
                line=dict(width=3),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Bar(
                x=times,
                y=power_total / 1000,
            ),
            row=2,
            col=1,
        )

        fig.update_layout(
            height=550,
            template="plotly_dark",
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Forecast Insights")

        avg_ghi = np.mean(ghi_vals)
        max_power = np.max(power_total)/1000

        c1, c2 = st.columns(2)

        c1.success(f"Average Forecast GHI: {avg_ghi:.1f} W/m²")
        c2.info(f"Maximum Predicted Power: {max_power:.2f} kW")

    else:
        st.warning("No forecast data available. Run Notebook 10 first.")


# ══════════════════════════════════════════════════════════════════
# TAB 2 — MODEL PERFORMANCE
# ══════════════════════════════════════════════════════════════════
with tab2:

    metrics = load_metrics()

    if not metrics:
        st.warning("Run notebooks 06–08 first.")
    else:

        combined = pd.concat(metrics.values(), ignore_index=True)

        fig = px.bar(
            combined,
            x="model",
            y="RMSE",
            color="model",
            title="Model Performance Comparison",
        )

        fig.update_layout(template="plotly_dark")

        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# TAB 3 — CITY COMPARISON
# ══════════════════════════════════════════════════════════════════
with tab3:

    city_stats = []

    for city in CITIES:
        try:
            df = load_feature_data(city)

            city_stats.append(
                {
                    "city": CITY_DISPLAY[city],
                    "mean_ghi": df["GHI"].mean(),
                    "lat": config.CITIES[city]["lat"],
                    "lon": config.CITIES[city]["lon"],
                }
            )
        except:
            pass

    if city_stats:

        stats_df = pd.DataFrame(city_stats)

        fig = px.scatter_geo(
            stats_df,
            lat="lat",
            lon="lon",
            size="mean_ghi",
            color="mean_ghi",
            hover_name="city",
            projection="natural earth",
        )

        fig.update_layout(
            template="plotly_dark",
            geo=dict(bgcolor="rgba(0,0,0,0)")
        )

        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# TAB 4 — POWER OUTPUT
# ══════════════════════════════════════════════════════════════════
with tab4:

    st.subheader("Solar Power Output Simulator")

    ghi_input = st.slider(
        "Solar Irradiance (W/m²)",
        0,
        1200,
        600
    )

    power_estimate = (
        ghi_input
        * panel_area
        * PANEL_EFFICIENCY
        * n_panels
    )

    st.metric(
        "Estimated Power Output",
        f"{power_estimate/1000:.2f} kW"
    )


# ══════════════════════════════════════════════════════════════════
# TAB 5 — DATA EXPLORER
# ══════════════════════════════════════════════════════════════════
with tab5:

    try:

        df = load_feature_data(selected_city)

        feature = st.selectbox(
            "Feature",
            ["GHI", "temperature", "humidity"],
        )

        fig = px.line(
            df,
            y=feature,
            title=f"{feature} Trend — {CITY_DISPLAY[selected_city]}",
        )

        fig.update_layout(template="plotly_dark")

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(str(e))


# ── Footer ─────────────────────────────────────────────────────────
st.markdown("""
---

**NeuroSpike AI Platform**

Solar Forecasting using  
Spiking Neural Networks | Deep Learning | Gradient Boosting

Developed for intelligent renewable energy optimization.
""")