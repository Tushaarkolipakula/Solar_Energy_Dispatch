import os
import pandas as pd
import numpy as np
import pulp

CSV_FILE = "hourly_data.csv"

PEAK_HOURS = list(range(17, 22))

# Battery settings
E_MAX = 10.0
P_MAX_CH = 3.5
P_MAX_DIS = 3.5
ETA_CH = 0.95
ETA_DIS = 0.95

# SOC is the measure of how full the battery is
SOC_MIN = 0.10 * E_MAX
SOC_MAX = 0.95 * E_MAX
SOC_INIT = SOC_MIN

DEGRAD_COST = 0.2

CH_DIS_PENALTY = 0.05
GRID_ARBITRAGE_PENALTY = 0.05

DT = 1.0
SOLVER_LIMIT = 300

# Load the CSV file
df = pd.read_csv(CSV_FILE)

# Data Cleaning
df.columns = [col.strip() for col in df.columns]
col_map = {col.lower(): col for col in df.columns}

load_col = col_map["demand"]
pv_col = col_map["solar_gen"]
buy_col = col_map["grid_buy_price"]
sell_col = col_map["grid_sell_price"]

# Timestamp
timestamp_col = "Timestamp"
df[timestamp_col] = pd.to_datetime(df[timestamp_col])

# Converting into float and filling empty/error values to 0.0
Pload_raw = pd.to_numeric(df[load_col], errors="coerce").fillna(0.0).values
Ppv_raw = pd.to_numeric(df[pv_col], errors="coerce").fillna(0.0).values

# Converting Watts to KW
if np.max(Pload_raw) > 500:
    Pload = Pload_raw / 1000.0
    Ppv = Ppv_raw / 1000.0
else:
    Pload = Pload_raw.copy()
    Ppv = Ppv_raw.copy()

hours = len(Pload)

# Determining hour of day
hours_of_day = np.tile(np.arange(24), int(np.ceil(hours / 24)))[:hours]

Price_buy = pd.to_numeric(df[buy_col], errors="coerce").fillna(0.0).values

Price_sell = np.minimum(
    pd.to_numeric(df[sell_col], errors="coerce").fillna(0.0).values,
    Price_buy - 0.001
)

# To make sure all arrays are numpy float arrays
Pload = np.asarray(Pload, float)
Ppv = np.asarray(Ppv, float)
Price_buy = np.asarray(Price_buy, float)
Price_sell = np.asarray(Price_sell, float)

# Heuristic Approach
# 1. Serve load from PV first
# 2. If PV remains, charge the battery
# 3. After charging, export remaining PV
# 4. In peak hours, discharge battery to reduce import
# 5. If load remains, import from the grid
# 6. Make sure battery stays in SOC limits
def simulate_heuristic(Pload, Ppv, hours_of_day, Price_buy, Price_sell):
    soc = np.zeros(hours + 1)
    soc[0] = SOC_INIT

    imp = np.zeros(hours)
    exp = np.zeros(hours)
    ch = np.zeros(hours)
    dis = np.zeros(hours)

    for t in range(hours):

        soc_cur = soc[t]
        load = Pload[t]
        pv = Ppv[t]

        # PV → load
        serve = min(pv, load)
        load_rem = load - serve
        pv_rem = pv - serve

        # Charge from PV
        if pv_rem > 0:
            max_charge = (SOC_MAX - soc_cur) / (ETA_CH)
            cp = min(pv_rem, P_MAX_CH, max_charge)
            ch[t] = cp
            soc_cur = soc_cur + (ETA_CH * cp)
            pv_rem = pv_rem - cp

        # Export remaining PV
        exp[t] = max(pv_rem, 0)

        # Peak hour: discharge
        if hours_of_day[t] in PEAK_HOURS and load_rem > 0:
            max_dis = (soc_cur - SOC_MIN) * ETA_DIS
            dp = min(P_MAX_DIS, max_dis, load_rem)
            dis[t] = dp
            soc_cur = soc_cur - (dp / ETA_DIS)
            load_rem = load_rem - dp

        imp[t] = max(load_rem, 0)
        soc[t + 1] = min(max(soc_cur, SOC_MIN), SOC_MAX)

    cost_buy = np.sum(imp * Price_buy)
    rev_sell = np.sum(exp * Price_sell)

    return {
        "imp": imp, "exp": exp,
        "ch": ch, "dis": dis,
        "soc": soc,
        "net_bill": cost_buy - rev_sell,
        "grid_import": np.sum(imp),
        "grid_export": np.sum(exp),
        "throughput": np.sum(ch + dis)
    }

heur = simulate_heuristic(Pload, Ppv, hours_of_day, Price_buy, Price_sell)

print(f"Heuristic net bill:  {heur['net_bill']:.2f} ₹")

# Using LP
prob = pulp.LpProblem("HomeEnergyLP", pulp.LpMinimize)


Pbuy = pulp.LpVariable.dicts("Pbuy", range(hours), lowBound=0)
Psell = pulp.LpVariable.dicts("Psell", range(hours), lowBound=0)
Pch = pulp.LpVariable.dicts("Pch", range(hours), lowBound=0, upBound=P_MAX_CH)
Pdis = pulp.LpVariable.dicts("Pdis", range(hours), lowBound=0, upBound=P_MAX_DIS)


E = pulp.LpVariable.dicts("E", range(hours + 1), lowBound=SOC_MIN, upBound=SOC_MAX)


prob += (E[0] == SOC_INIT)


# Objective
prob += pulp.lpSum([
   Price_buy[t] * Pbuy[t] - Price_sell[t] * Psell[t]
   + (DEGRAD_COST + CH_DIS_PENALTY) * (Pch[t] + Pdis[t])
   for t in range(hours)
])


# Constraints
for t in range(hours):


   prob += Ppv[t] + Pbuy[t] + Pdis[t] == Pload[t] + Pch[t] + Psell[t]


   prob += E[t + 1] == E[t] + ETA_CH * Pch[t] - (1.0 / ETA_DIS) * Pdis[t]


# Cyclic SOC
prob += E[hours] == SOC_INIT


print("Solving LP...")
solver = pulp.PULP_CBC_CMD(msg=1, timeLimit=SOLVER_LIMIT)
prob.solve(solver)
print("Status:", pulp.LpStatus[prob.status])


def val(v): return float(pulp.value(v) or 0)


res_buy = np.array([val(Pbuy[t]) for t in range(hours)])
res_sell = np.array([val(Psell[t]) for t in range(hours)])
res_ch = np.array([val(Pch[t]) for t in range(hours)])
res_dis = np.array([val(Pdis[t]) for t in range(hours)])
res_soc = np.array([val(E[t + 1]) for t in range(hours)])


eps = 1e-8
for arr in [res_buy, res_sell, res_ch, res_dis, res_soc]:
   arr[np.abs(arr) < eps] = 0


# Costs
cost_buy_lp = np.sum(res_buy * Price_buy)
rev_sell_lp = np.sum(res_sell * Price_sell)
net_bill_lp = cost_buy_lp - rev_sell_lp
throughput_lp = np.sum(res_ch + res_dis)
grid_import_lp_kwh = np.sum(res_buy)
grid_export_lp_kwh = np.sum(res_sell)


print(f"LP optimized bill:   {net_bill_lp:.2f} ₹")
