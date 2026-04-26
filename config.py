# NeuroSpike Global Configuration

# --- Cities ---
CITIES = {
    "riyadh":    {"lat": 24.7136, "lon": 46.6753},
    "cairo":     {"lat": 30.0444, "lon": 31.2357},
    "istanbul":  {"lat": 41.0082, "lon": 28.9784},
    "new_delhi": {"lat": 28.6139, "lon": 77.2090},
    "dubai":     {"lat": 25.2048, "lon": 55.2708},
    "london":    {"lat": 51.5072, "lon": -0.1276},
    "sydney":    {"lat": -33.8688, "lon": 151.2093},
    "tokyo":     {"lat": 35.6762, "lon": 139.6503},
    "los_angeles": {"lat": 34.0522, "lon": -118.2437},
    "nairobi":   {"lat": -1.2921, "lon": 36.8219},
}

# --- Data ---
START_DATE = "20210101"
END_DATE   = "20231231"

NASA_PARAMETERS = [
    "ALLSKY_SFC_SW_DWN",   # GHI � target variable
    "T2M",                 # Temperature (�C)
    "WS10M",               # Wind speed (m/s)
    "RH2M",                # Relative humidity (%)
    "CLRSKY_SFC_SW_DWN",   # Clear-sky irradiance
    "PRECTOTCORR",         # Precipitation (mm/hr)
    "PS",                  # Surface pressure (kPa)
    "ALLSKY_KT",           # Clearness index
]

# --- Paths ---
RAW_DATA_DIR       = "data/raw"
PROCESSED_DATA_DIR = "data/processed"
FEATURES_DATA_DIR  = "data/features"
MODELS_DIR         = "models/saved"
CHECKPOINTS_DIR    = "models/checkpoints"
OUTPUTS_PLOTS      = "outputs/plots"
OUTPUTS_METRICS    = "outputs/metrics"
OUTPUTS_FORECASTS  = "outputs/forecasts"

# --- Model ---

SEED           = 42
PAST_HOURS     = 24          # was 48
PRED_HORIZONS  = [1]         # was [1, 6, 24]
BATCH_SIZE     = 256         # was 64
EPOCHS         = 50          # was 100
LEARNING_RATE  = 1e-3
TRAIN_FRAC     = 0.72
VAL_FRAC       = 0.08
DAYTIME_THR    = 10.0      # W/m� threshold for daytime

# --- Solar Power ---
PANEL_EFFICIENCY = 0.20    # 20% standard panel
PANEL_AREA_M2    = 1.6     # m� per panel
