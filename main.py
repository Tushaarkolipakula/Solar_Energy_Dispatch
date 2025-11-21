import os
import pandas as pd
import numpy as np
import pulp

CSV_FILE = "hourly_data.csv"

# Battery settings
E_MAX = 10.0
P_MAX_CH = 3.5
P_MAX_DIS = 3.5
ETA_CH = 0.95
ETA_DIS = 0.95

SOC_MIN = 0.10 * E_MAX
SOC_MAX = 0.95 * E_MAX
SOC_INIT = SOC_MIN

DEGRAD_COST = 0.2

CH_DIS_PENALTY = 0.05
GRID_ARBITRAGE_PENALTY = 0.05

DT = 1.0
SOLVER_LIMIT = 300

# TOU pricing (override)
OVERRIDE_PRICES = True
BUY_OFFPEAK = 5
BUY_PEAK = 12.0
PEAK_HOURS = list(range(17, 22))
SELL_FIXED = 3.0

# Load the CSV file
df = pd.read_csv(CSV_FILE)

# Removing Extra Spaces
df.columns = [col.strip() for col in df.columns]

# Converting into lowercase
col_map = {col.lower(): col for col in df.columns}

load_col = col_map["demand"]
pv_col = col_map["solar_gen"]
buy_col = col_map["grid_buy_price"]
sell_col = col_map["grid_sell_price"]

# Timestamp
timestamp_col = "Timestamp"
df[timestamp_col] = pd.to_datetime(df[timestamp_col])

# Converting into float and filling empty values to 0.0
Pload_raw = pd.to_numeric(df[load_col], errors="coerce").fillna(0.0).values
Ppv_raw = pd.to_numeric(df[pv_col], errors="coerce").fillna(0.0).values

