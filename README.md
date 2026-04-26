# NeuroSpike

Global solar irradiance forecasting with machine learning, deep learning, and spiking neural networks.

NeuroSpike predicts solar GHI (Global Horizontal Irradiance), estimates photovoltaic power output, compares model performance, and exposes the results through API and dashboard interfaces.

## What Is Included

- Data pipeline notebooks for collection, preprocessing, feature engineering, training, evaluation, and forecasting.
- Reusable Python modules in `src/` for preprocessing, modeling, evaluation, and utilities.
- FastAPI forecasting backend powered by trained NeuroSpike SNN checkpoints.
- Streamlit dashboard for model metrics, city comparison, forecasts, and power simulation.
- Standalone web dashboard in `neurospikeapp/` with forecast, savings, comparison, and static frontend views.
- Saved model artifacts, forecast outputs, plots, and evaluation metrics.

## Project Structure

```text
NeuroSpike/
  backend/            FastAPI model inference API
  frontend/           Streamlit analytics dashboard
  neurospikeapp/      Standalone FastAPI + static web dashboard
  notebooks/          Step-by-step notebooks from data collection to forecasting
  src/                Shared training, preprocessing, model, and evaluation code
  data/               Raw, processed, and feature datasets
  models/             Saved models and checkpoints
  outputs/            Forecasts, plots, and metrics
  config.py           Global cities, paths, model settings, and solar constants
  requirements.txt    Python dependencies
```

## Supported Cities

The main forecasting pipeline is configured for:

- Riyadh
- Cairo
- Istanbul
- New Delhi
- Dubai
- London
- Sydney
- Tokyo
- Los Angeles
- Nairobi

City coordinates and project constants are defined in `config.py`.

## Setup

From the `NeuroSpike` directory:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If you are using an existing environment, install the dependencies directly:

```powershell
pip install -r requirements.txt
```

## Run The Forecasting API

The model API lives in `backend/app.py`. Run it from the `backend` directory so the relative paths resolve correctly:

```powershell
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Useful endpoints:

- `GET /health` - API health check
- `GET /cities` - supported city list
- `GET /metrics` - saved model evaluation metrics
- `POST /forecast` - forecast request body: `{"city": "new_delhi", "horizon": 1}`
- `GET /forecast/{city}?horizon=1` - browser-friendly forecast endpoint

Note: `config.py` currently sets `PRED_HORIZONS = [1]`, so the backend supports 1-hour forecasts unless additional horizon models are trained and configured.

## Run The Streamlit Dashboard

The Streamlit dashboard lives in `frontend/dashboard.py`. Run it from the `frontend` directory:

```powershell
cd frontend
streamlit run dashboard.py
```

The dashboard can call the API at `http://localhost:8000` when it is running. If the API is offline, it falls back to stored forecast output in `outputs/forecasts/all_forecasts.json`.

Dashboard tabs include:

- Forecast
- Model Performance
- City Comparison
- Power Output
- Data Explorer

## Run The Standalone Web Dashboard

The newer web app is in `neurospikeapp/`. It serves a static frontend and lightweight API from FastAPI:

```powershell
cd neurospikeapp
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open:

```text
http://localhost:8000
```

Standalone app endpoints:

- `GET /api/cities`
- `POST /api/forecast`
- `POST /api/savings`
- `GET /api/compare`

## Notebook Workflow

The notebooks are organized as a full pipeline:

1. Data collection
2. Preprocessing
3. Exploratory data analysis
4. Feature engineering
5. Feature selection
6. Baseline model training
7. LSTM model training
8. NeuroSpike SNN training
9. Evaluation
10. Forecast generation

Run the notebooks in order when rebuilding data, models, metrics, or forecast outputs from scratch.

## Outputs

Generated artifacts are stored under `outputs/`:

- `outputs/metrics/` - model scores, summaries, histories, and comparison tables
- `outputs/plots/` - visual analysis and model performance charts
- `outputs/forecasts/` - forecast JSON, HTML dashboard output, and power estimates

Model artifacts are stored under:

- `models/checkpoints/` - training checkpoints, including SNN and LSTM checkpoints
- `models/saved/` - saved trained models

## Notes

- The backend and Streamlit dashboard use relative paths, so run each app from its own directory.
- Some source files may contain older encoding artifacts in display strings. The core Python syntax is valid, but cleaning those strings will improve UI text.
- If Python reports an access error while writing `__pycache__` files on OneDrive, close running Python processes or delete the stale cache file after OneDrive finishes syncing.
