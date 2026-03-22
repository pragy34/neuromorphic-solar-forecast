<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=32&duration=3000&pause=1000&color=F59E0B&center=true&vCenter=true&width=700&lines=NeuroSpike+%F0%9F%8C%9E;Solar+Irradiance+Forecasting;Spiking+Neural+Networks+%2B+Deep+Learning" alt="Typing SVG" />

<br/>

[![Python](https://img.shields.io/badge/Python-3.12.6-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.10-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.21-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)](https://tensorflow.org)
[![SNNTorch](https://img.shields.io/badge/SNNTorch-0.9.4-7C3AED?style=for-the-badge)](https://snntorch.readthedocs.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.55-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)

<br/>

> **First application of LIF-based Spiking Neural Networks to multi-city global solar irradiance forecasting**
> 10 cities · 3 years · 262,800 data points · NASA POWER API · BiLSTM + Attention · NeuroSpike SNN

<br/>

</div>

---

## About

**NeuroSpike** is an end-to-end solar irradiance forecasting system I built as my major project at JIIT Noida. It predicts **Global Horizontal Irradiance (GHI)** — the key variable in solar power generation — across **10 global cities** using 3 years of NASA satellite data.

The core innovation is implementing a **real Spiking Neural Network** using SNNTorch with Leaky Integrate-and-Fire neurons — biologically-inspired models that fire discrete spikes rather than continuous activations. This is combined with a Bidirectional LSTM + Attention model, classical ML baselines, and a full production system including a REST API and interactive dashboard.

---

## Results

<div align="center">

| Model | Mean RMSE (W/m²) | Mean R² | Skill Score |
|:---:|:---:|:---:|:---:|
| Persistence (naive) | 91.3 | 0.890 | 0% |
| Climatology | 69.3 | 0.913 | +24% |
| Random Forest | 46.1 | 0.961 | +49% |
| XGBoost | 47.3 | 0.959 | +48% |
| **BiLSTM + Attention** | **45.5** | **0.962** | **+50%** |
| NeuroSpike SNN | competitive | >0.95 | >35% |

</div>

**BiLSTM beats XGBoost on 6/10 cities** — sequence models excel where temporal complexity is high (Istanbul +23%, Tokyo +23%, London +22%). XGBoost retains advantage on desert cities with highly regular patterns.

---

## Per-City Performance (BiLSTM, h=1)

<div align="center">

| City | RMSE (W/m²) | R² | Skill | Climate |
|:---|:---:|:---:|:---:|:---|
| Dubai | 34.7 | 0.986 | 65.0% | Desert |
| Riyadh | 38.1 | 0.987 | 65.6% | Desert |
| Istanbul | 37.7 | 0.979 | 52.8% | Mediterranean |
| Cairo | 40.6 | 0.984 | 60.6% | Arid |
| London | 41.4 | 0.956 | 28.7% | Cloudy/Oceanic |
| Tokyo | 46.0 | 0.964 | 43.1% | Humid subtropical |
| New Delhi | 54.4 | 0.954 | 37.1% | Monsoon |
| Los Angeles | 49.7 | 0.971 | 40.2% | Mediterranean |
| Nairobi | 52.1 | 0.964 | 38.3% | Equatorial |
| Sydney | 60.5 | 0.954 | 34.8% | Variable |

</div>

> Desert cities achieve R² > 0.98 — highly predictable clear-sky patterns.
> Cloudy and monsoon cities benefit most from BiLSTM temporal memory.

---

## Architecture

### NeuroSpike SNN — The Core Innovation

```
Input (batch, 24 timesteps, 15 features)
        |
    Flatten + FC Encoder + LayerNorm
        |
  LIF Layer 1  -->  256 neurons, beta learnable
        |  spikes (0 or 1)
  LIF Layer 2  -->  128 neurons, beta learnable
        |  spikes
  LIF Layer 3  -->   64 neurons, beta learnable
        |
  Mean spike rate (10 simulation steps)
        |
  Dense Decoder  -->  64 --> 32 --> 1
        |
  GHI prediction (W/m2)
```

**Leaky Integrate-and-Fire equation:**
```
Vm(t) = beta x Vm(t-1) + I(t)
if Vm(t) >= 1.0  -->  spike = 1,  Vm = 0  (reset)
else             -->  spike = 0
```

Backpropagation uses **surrogate gradient (fast sigmoid, slope=25)** to handle the non-differentiable Heaviside spike function. Beta (membrane decay) is **learned per layer** during training.

### BiLSTM + Attention

```
Input (batch, 24, 15)
        |
BiLSTM (64 units, return_sequences=True)  <-- learns forward + backward patterns
        |
Batch Normalization
        |
BiLSTM (32 units, return_sequences=True)
        |
Soft Attention Layer  <-- learns which past hours matter most
        |
Dense(32, ReLU) --> Dropout(0.2) --> Dense(1, linear)
        |
GHI prediction (W/m2)
```

---

## Feature Engineering (35+ features)

```python
# Cyclical time encodings — no false discontinuity at midnight
hour_sin, hour_cos   = sin/cos(2*pi * hour / 24)
doy_sin,  doy_cos    = sin/cos(2*pi * doy  / 365)
month_sin, month_cos = sin/cos(2*pi * month / 12)

# Solar physics
solar_elevation = arcsin(sin(lat)*sin(decl) + cos(lat)*cos(decl)*cos(ha))
clearness_index = GHI / clear_sky_GHI   # clipped to [0, 1]

# Lag features — strongest predictors after physics
GHI_lag1, GHI_lag2, GHI_lag3, GHI_lag6, GHI_lag12, GHI_lag24, GHI_lag48

# Rolling statistics — captures local trend and cloud volatility
GHI_roll3_mean,  GHI_roll3_std
GHI_roll6_mean,  GHI_roll6_std
GHI_roll24_mean, GHI_roll24_std

# Weather features
temperature, humidity, wind_speed, pressure, precipitation
```

---

## Solar Power Estimation

```
P = GHI x eta x A
eta = 0.20  (20% panel efficiency)
A   = 1.6   (m2 per panel)
```

<div align="center">

| City | Annual kWh/Panel | Multiplier vs London |
|:---|:---:|:---:|
| Riyadh | 707.4 | 2.0x |
| Nairobi | 671.4 | 1.9x |
| Cairo | 669.6 | 1.9x |
| Los Angeles | 656.0 | 1.9x |
| Dubai | 646.3 | 1.8x |
| London | 353.2 | 1.0x (reference) |

</div>

---

## Project Structure

```
NeuroSpike/
├── notebooks/
│   ├── 01_data_collection.ipynb      # NASA POWER API — 10 cities x 3 years
│   ├── 02_preprocessing.ipynb        # Cleaning, clearness index fix
│   ├── 03_eda.ipynb                  # Correlation, seasonal, autocorrelation
│   ├── 04_feature_engineering.ipynb  # 35+ feature creation
│   ├── 05_feature_selection.ipynb    # RF + XGBoost + MI consensus
│   ├── 06_baseline_model.ipynb       # Persistence, Climatology, RF, XGBoost
│   ├── 07_lstm_model.ipynb           # BiLSTM + Attention
│   ├── 08_neurospike_snn.ipynb       # NeuroSpike SNN (LIF neurons)
│   ├── 09_evaluation.ipynb           # Full model comparison
│   └── 10_forecasting.ipynb          # Pipeline + Plotly dashboard
│
├── src/                              # Reusable Python modules
├── backend/
│   └── app.py                        # FastAPI REST API (port 8000)
├── frontend/
│   └── dashboard.py                  # Streamlit 5-tab dashboard (port 8502)
├── data/
│   ├── raw/                          # NASA POWER CSVs
│   ├── processed/                    # Cleaned CSVs
│   └── features/                     # Feature-engineered CSVs
├── models/
│   ├── saved/                        # Final .keras and .pt models
│   └── checkpoints/                  # Best checkpoints per city
├── outputs/
│   ├── plots/                        # All generated visualizations
│   ├── metrics/                      # Results CSVs and JSONs
│   └── forecasts/                    # Forecast outputs + HTML dashboard
├── config.py                         # Global configuration
├── requirements.txt
└── start_neurospike.bat              # One-click startup (Windows)
```

---

## Installation

```bash
# 1. Clone
git clone https://github.com/pragyupadhyay/NeuroSpike.git
cd NeuroSpike

# 2. Virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS

# 3. Install all dependencies
pip install -r requirements.txt

# 4. Verify
python -c "import tensorflow as tf; import torch; import snntorch; print('All imports OK')"
```

---

## Running

### One-click (Windows)

```bash
start_neurospike.bat
```

### Manual

```bash
# Terminal 1 — API backend
cd backend
python -m uvicorn app:app --reload --port 8000

# Terminal 2 — Dashboard
cd frontend
python -m streamlit run dashboard.py

# Terminal 3 — Notebooks
python -m jupyter notebook
```

<div align="center">

| Service | URL | Description |
|:---|:---|:---|
| Streamlit Dashboard | http://localhost:8502 | 5-tab interactive UI |
| FastAPI Backend | http://localhost:8000 | REST API |
| API Swagger Docs | http://localhost:8000/docs | Auto-generated docs |
| Jupyter Notebooks | http://localhost:8888 | All 10 notebooks |

</div>

---

## API

```bash
# Health check
curl http://localhost:8000/health

# Forecast — New Delhi, 1 hour ahead
curl -X POST http://localhost:8000/forecast \
  -H "Content-Type: application/json" \
  -d '{"city": "new_delhi", "horizon": 1}'

# List all 10 supported cities
curl http://localhost:8000/cities

# Get all model evaluation metrics
curl http://localhost:8000/metrics
```

---

## Tech Stack

<div align="center">

| Category | Technology |
|:---|:---|
| SNN framework | SNNTorch 0.9.4 |
| Deep learning | TensorFlow 2.21, PyTorch 2.10 |
| Classical ML | Scikit-learn, XGBoost, CatBoost |
| Data processing | Pandas, NumPy, SciPy |
| Visualization | Plotly, Matplotlib, Seaborn |
| Backend | FastAPI, Uvicorn |
| Frontend | Streamlit |
| Data source | NASA POWER API |
| Language | Python 3.12.6 |

</div>

---

## Dataset

- **Source:** [NASA POWER API](https://power.larc.nasa.gov) — Prediction of Worldwide Energy Resources
- **Period:** January 2021 to December 2023 (3 years hourly)
- **Coverage:** 10 cities across all major climate zones
- **Size:** 262,800 hourly records — 26,280 per city
- **Raw features:** GHI, Temperature, Wind Speed, Humidity, Clear-sky GHI, Precipitation, Pressure, Clearness Index

---

## Key Findings

1. **Sequence models beat tabular models on high-variability climates** — BiLSTM temporal memory captures cloud-induced GHI spikes that XGBoost misses entirely
2. **Desert cities are easiest to forecast** — Riyadh and Dubai achieve R² > 0.986 due to consistent clear-sky patterns
3. **Solar yield varies 2x between best and worst cities** — Riyadh (707 kWh/panel/year) vs London (353 kWh/panel/year)
4. **Spiking Neural Networks are viable for solar forecasting** — LIF neurons naturally detect temporal spike patterns in irradiance caused by cloud edges
5. **50% skill score improvement over persistence** — the standard naive baseline used in operational solar forecasting

---

## References

1. Alharbi et al., "Neuromorphic Computing-Based Model for Short-Term Forecasting of GHI in Saudi Arabia," IEEE Access, 2024
2. Qing & Niu, "Hourly day-ahead solar irradiance prediction using LSTM," Energy, 2018
3. Zhang et al., "Methodology based on spiking neural networks for univariate time-series forecasting," Neural Networks, 2024
4. Eshraghian et al., "SNNTorch: Accelerating Neuromorphic Computing with PyTorch," IEEE TNNLS, 2023
5. NASA POWER: Prediction of Worldwide Energy Resources, NASA Langley Research Center

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built by Pragy Upadhyay**

B.Tech Electronics and Communication Engineering
Jaypee Institute of Information Technology, Noida, U.P., India
Major Project · 2024–2025

[![GitHub](https://img.shields.io/badge/GitHub-pragyupadhyay-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/pragyupadhyay)

<br/>

*If this project helped you, consider giving it a star*

</div>
