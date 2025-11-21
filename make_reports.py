# make_reports.py
import os
import pandas as pd
import numpy as np

# --- CONFIG ---
ETA_CH = 0.95
ETA_DIS = 0.95
SOC_MIN = 0.10 * 10.0   # E_MAX = 10.0 in your main.py
SOC_MAX = 0.95 * 10.0
SOC_INIT = SOC_MIN
DT = 1.0

# --- filenames ---
comparison_file = "comparison_schedule.csv"
hourly_file = "hourly_data.csv"

if not os.path.exists(comparison_file):
    if os.path.exists(hourly_file):
        raise SystemExit(
            f"'{comparison_file}' not found. Run main.py first (it will create '{comparison_file}')."
        )
    else:
        raise SystemExit(
            f"Neither '{comparison_file}' nor '{hourly_file}' found in current folder."
        )

# load schedule saved by your main.py
df = pd.read_csv(comparison_file)
# unify timestamp / hour column if present
if "Timestamp" in df.columns:
    try:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    except Exception:
        pass

# required columns in comparison_schedule.csv produced by your main.py
required = ["Load_kW", "Solar_kW", "LP_Import", "LP_Export", "LP_Ch", "LP_Dis"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise SystemExit(f"comparison_schedule.csv missing columns: {missing}")

# compute solar utilized = solar generation - exported (what's exported by LP is leftover)
df["Solar_utilized_kW"] = df["Solar_kW"] - df["LP_Export"]
# ensure not negative (numerical eps)
df["Solar_utilized_kW"] = df["Solar_utilized_kW"].clip(lower=0.0)

# compute battery SOC profile by simulating LP_Ch and LP_Dis (uses same energy update as main.py)
hours = len(df)
soc = np.zeros(hours + 1)
soc[0] = SOC_INIT
for t in range(hours):
    ch = float(df.loc[t, "LP_Ch"])
    dis = float(df.loc[t, "LP_Dis"])
    # energy update: E[t+1] = E[t] + ETA_CH * Pch - (1/ETA_DIS) * Pdis
    soc[t + 1] = soc[t] + ETA_CH * ch - (1.0 / ETA_DIS) * dis
    # enforce bounds (same logic as your main.py)
    if soc[t + 1] < SOC_MIN - 1e-8:
        soc[t + 1] = SOC_MIN
    if soc[t + 1] > SOC_MAX + 1e-8:
        soc[t + 1] = SOC_MAX

# attach SOC to dataframe (E at end of hour t → show E[t+1] to match main.py's res_soc)
df["SOC_kWh"] = soc[1:]

# Add grid usage column (net import minus export) and battery net
df["Grid_Import_kW"] = df["LP_Import"]         # power drawn from grid that hour
df["Grid_Export_kW"] = df["LP_Export"]         # power exported to grid that hour
df["Battery_Charge_kW"] = df["LP_Ch"]
df["Battery_Discharge_kW"] = df["LP_Dis"]
df["Battery_Net_kW"] = df["Battery_Charge_kW"] - df["Battery_Discharge_kW"]

# Build Optimal hourly power flow table
cols_order = [
    "Timestamp", "Load_kW", "Solar_kW", "Solar_utilized_kW",
    "Grid_Import_kW", "Grid_Export_kW",
    "Battery_Charge_kW", "Battery_Discharge_kW", "Battery_Net_kW", "SOC_kWh"
]
# Keep only columns that exist (Timestamp optional)
cols_present = [c for c in cols_order if c in df.columns]
hourly_table = df[cols_present].copy()

# Round numbers for readability
for c in hourly_table.columns:
    if hourly_table[c].dtype.kind in "f":
        hourly_table[c] = hourly_table[c].round(4)

# Save the hourly table
hourly_table.to_csv("optimal_hourly_flow.csv", index=False)
print("Saved: optimal_hourly_flow.csv")

# Battery charge/discharge profile (rows where battery did something)
profile = df[(df["LP_Ch"] > 1e-6) | (df["LP_Dis"] > 1e-6)].copy()
profile = profile[[
    "Timestamp", "Battery_Charge_kW", "Battery_Discharge_kW", "SOC_kWh",
    "Load_kW", "Solar_kW", "Grid_Import_kW", "Grid_Export_kW"
]].reset_index(drop=True)

# Round for readability
for c in profile.columns:
    if profile[c].dtype.kind in "f":
        profile[c] = profile[c].round(4)

profile.to_csv("battery_profile.csv", index=False)
print("Saved: battery_profile.csv")

# Print concise human readable summary
pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)

print("\n=== Optimal hourly power flow (first 12 rows) ===")
print(hourly_table.head(12).to_string(index=True))

print("\n=== Battery charge/discharge events ===")
if profile.shape[0] == 0:
    print("No battery charging or discharging events found (all zeros).")
else:
    print(profile.to_string(index=True))

# A few aggregated stats
total_import = df["Grid_Import_kW"].sum()
total_export = df["Grid_Export_kW"].sum()
total_ch = df["Battery_Charge_kW"].sum()
total_dis = df["Battery_Discharge_kW"].sum()

print("\n=== Aggregates ===")
print(f"Total grid import (kWh): {total_import:.4f}")
print(f"Total grid export (kWh): {total_export:.4f}")
print(f"Total battery charged (kWh): {total_ch:.4f}")
print(f"Total battery discharged (kWh): {total_dis:.4f}")
print(f"Net battery throughput (kWh): {total_ch + total_dis:.4f}")
