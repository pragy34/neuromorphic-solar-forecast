# backend/app.py
import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
import torch.nn as nn
import snntorch as snn
from snntorch import surrogate
from sklearn.preprocessing import MinMaxScaler

sys.path.append(os.path.abspath(".."))
import config

# Paths
FEATURES_DIR = os.path.join("..", config.FEATURES_DATA_DIR)
CKPT_DIR = os.path.join("..", config.CHECKPOINTS_DIR)
METRICS_DIR = os.path.join("..", config.OUTPUTS_METRICS)
FORECAST_DIR = os.path.join("..", config.OUTPUTS_FORECASTS)

PAST_HOURS = config.PAST_HOURS
HORIZONS = config.PRED_HORIZONS
TRAIN_FRAC = config.TRAIN_FRAC
PANEL_EFFICIENCY = config.PANEL_EFFICIENCY
PANEL_AREA_M2 = config.PANEL_AREA_M2
TARGET = "GHI"
DEVICE = torch.device("cpu")

SEQUENCE_FEATURES = [
    "clear_sky_ghi", "solar_elevation", "cos_zenith",
    "hour_sin", "hour_cos", "doy_sin", "doy_cos",
    "month_sin", "month_cos",
    "temperature", "humidity", "wind_speed",
    "pressure", "precipitation",
    "GHI_lag1", "GHI_lag2", "GHI_lag3",
    "GHI_lag6", "GHI_lag12", "GHI_lag24", "GHI_lag48",
    "GHI_roll3_mean", "GHI_roll3_std",
    "GHI_roll6_mean", "GHI_roll6_std",
    "GHI_roll24_mean", "GHI_roll24_std",
    "clearness_index", "clearness_index_lag1",
    "clearness_index_lag24",
    "clearsky_x_kt", "temp_x_humidity",
    "wind_x_humidity", "lag24_x_kt",
    "is_daytime", "is_daytime_clear_sky",
]

UTC_OFFSETS = {
    "riyadh": 3, "cairo": 2, "istanbul": 3,
    "new_delhi": 5.5, "dubai": 4, "london": 0,
    "sydney": 10, "tokyo": 9,
    "los_angeles": -8, "nairobi": 3,
}


# SNN Model Class
class NeuroSpikeSNN(nn.Module):
    def __init__(self, n_time_steps, n_features, horizon=1, hidden_sizes=[512, 256, 128], beta=0.95, dropout_rate=0.2):
        super().__init__()
        self.n_time_steps = n_time_steps
        self.n_features = n_features
        self.horizon = horizon
        input_dim = n_time_steps * n_features
        spike_grad = surrogate.fast_sigmoid(slope=25)

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_sizes[0]),
            nn.LayerNorm(hidden_sizes[0]),
        )
        self.fc1 = nn.Linear(hidden_sizes[0], hidden_sizes[0])
        self.lif1 = snn.Leaky(beta=beta, spike_grad=spike_grad, learn_beta=True, threshold=1.0)
        self.drop1 = nn.Dropout(dropout_rate)
        self.fc2 = nn.Linear(hidden_sizes[0], hidden_sizes[1])
        self.lif2 = snn.Leaky(beta=beta, spike_grad=spike_grad, learn_beta=True, threshold=1.0)
        self.drop2 = nn.Dropout(dropout_rate)
        self.fc3 = nn.Linear(hidden_sizes[1], hidden_sizes[2])
        self.lif3 = snn.Leaky(beta=beta, spike_grad=spike_grad, learn_beta=True, threshold=1.0)
        self.decoder = nn.Sequential(
            nn.Linear(hidden_sizes[2], 64),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.5),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, horizon),
        )

    def forward(self, x):
        b = x.shape[0]
        x_flat = x.reshape(b, -1)
        encoded = self.encoder(x_flat)
        mem1 = self.lif1.init_leaky()
        mem2 = self.lif2.init_leaky()
        mem3 = self.lif3.init_leaky()
        spike3_rec = []
        cur = encoded
        for _ in range(10):
            spk1, mem1 = self.lif1(self.fc1(cur), mem1)
            spk1 = self.drop1(spk1)
            spk2, mem2 = self.lif2(self.fc2(spk1), mem2)
            spk2 = self.drop2(spk2)
            spk3, mem3 = self.lif3(self.fc3(spk2), mem3)
            spike3_rec.append(spk3)
        rate = torch.stack(spike3_rec).mean(dim=0)
        return self.decoder(rate)


# Helper functions
def inverse_ghi(scaled_vals, scaler):
    n_cols = scaler.n_features_in_
    dummy = np.zeros((len(scaled_vals), n_cols))
    dummy[:, 0] = scaled_vals.flatten()
    return scaler.inverse_transform(dummy)[:, 0]


def build_scaler_and_window(city: str):
    """Load stored feature CSV, fit scaler, return last window."""
    path = os.path.join(FEATURES_DIR, f"{city}_features.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No feature file for {city}")

    df = pd.read_csv(path, index_col="datetime", parse_dates=True)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    avail_feats = [f for f in SEQUENCE_FEATURES if f in df.columns and f != TARGET]
    all_cols = [TARGET] + avail_feats

    n = len(df)
    train_end = int(n * TRAIN_FRAC)
    scaler = MinMaxScaler()
    scaler.fit(df[all_cols].iloc[:train_end].values)

    df_sc = pd.DataFrame(scaler.transform(df[all_cols].values), columns=all_cols, index=df.index)
    last_window = df_sc[avail_feats].iloc[-PAST_HOURS:].values
    return last_window, scaler, len(avail_feats), df.index[-1]


def load_model(city: str, horizon: int, n_features: int) -> NeuroSpikeSNN:
    path = os.path.join(CKPT_DIR, f"snn_{city}_h{horizon}.pt")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model not found: snn_{city}_h{horizon}.pt")
    model = NeuroSpikeSNN(n_time_steps=PAST_HOURS, n_features=n_features, horizon=horizon).to(DEVICE)
    model.load_state_dict(torch.load(path, map_location=DEVICE))
    model.eval()
    return model


# FastAPI App
app = FastAPI(
    title="NeuroSpike API",
    description="Solar Irradiance Forecasting - SNN Backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request / Response Models
class ForecastRequest(BaseModel):
    city: str
    horizon: Optional[int] = 1


class ForecastResponse(BaseModel):
    city: str
    horizon: int
    forecast_from: str
    timestamps: list
    ghi_wm2: list
    power_watts: list
    mean_ghi: float
    max_ghi: float
    mean_power: float
    panel_efficiency: float
    panel_area_m2: float


# Routes
@app.get("/")
def root():
    return {
        "message": "NeuroSpike API is running",
        "version": "1.0.0",
        "endpoints": [
            "/forecast",
            "/cities",
            "/metrics",
            "/health",
        ],
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device": str(DEVICE),
    }


@app.get("/cities")
def get_cities():
    """Return list of supported cities with coordinates."""
    return {
        "cities": [
            {
                "name": city,
                "lat": config.CITIES[city]["lat"],
                "lon": config.CITIES[city]["lon"],
                "utc_offset": UTC_OFFSETS.get(city, 0),
            }
            for city in config.CITIES
        ]
    }


@app.get("/metrics")
def get_metrics():
    """Return model evaluation metrics from training."""
    results = {}
    for fname in ["baseline_results.csv", "lstm_results.csv", "snn_results.csv"]:
        path = os.path.join(METRICS_DIR, fname)
        if os.path.exists(path):
            df = pd.read_csv(path)
            results[fname.replace(".csv", "")] = df.to_dict(orient="records")
    return results


@app.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest):
    """
    Run NeuroSpike SNN forecast for a city and horizon.

    - city    : one of the 10 supported cities
    - horizon : 1, 6, or 24 hours ahead
    """
    city = req.city.lower().replace(" ", "_")
    horizon = req.horizon

    if city not in config.CITIES:
        raise HTTPException(
            status_code=400,
            detail=f"City '{city}' not supported. Use /cities to see available options.",
        )
    if horizon not in HORIZONS:
        raise HTTPException(
            status_code=400,
            detail=f"Horizon {horizon} not supported. Use one of {HORIZONS}.",
        )

    try:
        last_window, scaler, n_features, last_time = build_scaler_and_window(city)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        model = load_model(city, horizon, n_features)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Run inference
    x_input = torch.tensor(last_window[np.newaxis, :, :], dtype=torch.float32).to(DEVICE)

    with torch.no_grad():
        pred_scaled = model(x_input).cpu().numpy().flatten()

    pred_ghi = np.clip(inverse_ghi(pred_scaled, scaler), 0, None)
    pred_power = pred_ghi * PANEL_EFFICIENCY * PANEL_AREA_M2

    timestamps = [str(last_time + pd.Timedelta(hours=h + 1)) for h in range(len(pred_ghi))]

    return ForecastResponse(
        city=city,
        horizon=horizon,
        forecast_from=str(last_time),
        timestamps=timestamps,
        ghi_wm2=pred_ghi.tolist(),
        power_watts=pred_power.tolist(),
        mean_ghi=round(float(pred_ghi.mean()), 2),
        max_ghi=round(float(pred_ghi.max()), 2),
        mean_power=round(float(pred_power.mean()), 2),
        panel_efficiency=PANEL_EFFICIENCY,
        panel_area_m2=PANEL_AREA_M2,
    )


@app.get("/forecast/{city}")
def forecast_get(city: str, horizon: int = 1):
    """GET version of forecast endpoint for easy browser testing."""
    return forecast(ForecastRequest(city=city, horizon=horizon))


# Run
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
