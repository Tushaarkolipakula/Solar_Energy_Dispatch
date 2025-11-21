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
