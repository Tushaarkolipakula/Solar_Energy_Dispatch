# Solar_Energy_Dispatch

## Battery Energy Management Optimization

This project simulates and optimizes battery energy storage behavior for a residential or commercial setting using solar generation and time-of-use pricing. It includes data preprocessing, heuristic simulation, linear programming-based optimization, and reporting/visualization.

---

## Project Structure

```
.
├── hourly_data.csv                  # Cleaned hourly input dataset
├── main.py                          # Main simulation and optimization script
├── make_reports.py                  # Generates post-optimization reports
├── comparison_schedule.csv          # Output comparison of Heuristic vs LP
├── optimal_hourly_flow.csv          # Detailed power flow results
├── battery_profile.csv              # Battery-specific activity report
└── plots/                           # Directory containing generated plots
```

---

## 1. Data Cleaning & Preparation

**Purpose:**

* Convert 15-minute resolution data to hourly resolution.
* Strip unnecessary columns.
* Ensure consistent formatting and handle missing values.

**Files:**

* `hourly_data.csv` (cleaned dataset)

**Main Columns Expected:**

* `Timestamp`: Date and hour
* `Demand`: Load demand in kW
* `Solar_Gen`: Solar generation in kW
* `Grid_Buy_Price`: Price to buy from grid
* `Grid_Sell_Price`: Price to sell to grid

---

## 2. Simulation and Optimization (`main.py`)

### Key Features:

* **Heuristic Simulation:**

  * Simple rule-based energy flow control.
  * Prioritizes PV → Load → Charge → Export logic.

* **LP Optimization (Using PuLP):**

  * Minimizes net electricity cost.
  * Constraints include:

    * Power balance
    * Battery capacity
    * SOC limits
    * Cyclic SOC for 24-hour loop

### Outputs:

* **comparison_schedule.csv:**
  Contains Heuristic vs LP import/export/charge/discharge schedules.
* Printed net bills and grid usage comparisons.

---

## 3. Report Generation (`make_reports.py`)

### Generates:

* **optimal_hourly_flow.csv**

  * Hourly power breakdown (load, solar, battery, grid).
* **battery_profile.csv**

  * Timestamped battery charge/discharge cycles with SOC.
* **Console Summary:**

  * Aggregated stats for import/export, throughput, etc.

---

## 4. Plots and Visualizations

### Key Graphs:

* Hourly Demand Over Time
* Distribution of Demand and Solar Generation
* Daily Trends (e.g., battery activity, SOC)
* Heuristic vs LP comparisons:

  * Grid Import
  * Battery Charge/Discharge
* Optimal Power Flow Trends

> 📌 Tip: Most graphs also include both daily and full-period views for clarity.

---

## 5. How to Run

```bash
# Step 1: Prepare hourly_data.csv (cleaned)

# Step 2: Run the main optimization script
python main.py

# Step 3: Generate reports
python make_reports.py

# Step 4: Visualize using provided plotting scripts or notebooks
```

---

## 6. Dependencies

* Python 3.7+
* pandas
* numpy
* PuLP
* matplotlib (for plotting)
* seaborn (optional, for styled histograms)

Install with:

```bash
pip install pandas numpy pulp matplotlib seaborn
```

---

## 7. Notes

* SOC stands for **State of Charge** (how full the battery is).
* PV refers to **Photovoltaic solar generation**.
* Assumes hourly time steps and fixed battery parameters.
* Pricing can be customized for real-world use cases.

---
