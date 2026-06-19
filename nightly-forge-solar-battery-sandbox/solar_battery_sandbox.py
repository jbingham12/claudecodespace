"""
solar_battery_sandbox.py
------------------------
Off-Grid Solar + Battery Sizing Sandbox

A simple, transparent hourly energy balance model for an off-grid cabin.
All parameters are illustrative synthetic defaults — not from any proprietary source.

Model logic (per hour):
  pv_gen   = peak_kw * cf_hour              # PV output
  net      = pv_gen - load_kw               # positive = surplus, negative = deficit
  if net > 0:
      charge battery (up to capacity); remainder is curtailed PV
  if net < 0:
      discharge battery (down to min_soc); remainder is unmet load

Outputs: CSV data per scenario + combined PNG figure.
"""

import csv
import math
import os

# ── optional matplotlib guard ────────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("WARNING: matplotlib not found — PNG will not be generated.")

# ─────────────────────────────────────────────────────────────────────────────
# PARAMETERS (all illustrative / synthetic)
# ─────────────────────────────────────────────────────────────────────────────

# PV array
PV_PEAK_KW = 3.0          # nameplate capacity

# Battery
BATT_CAPACITY_KWH = 10.0  # usable capacity (illustrative; e.g. 2×5 kWh LFP)
BATT_MIN_SOC_KWH  = 1.0   # keep ~10 % as a depth-of-discharge floor
BATT_INIT_SOC_KWH = 5.0   # starting state of charge
BATT_EFF          = 0.95   # round-trip efficiency (applied on charge)

# Hourly load profile — synthetic "cabin" (kW)
# Peaks in morning/evening; low overnight.  Two seasons differ in magnitude.
LOAD_SUMMER = [
    0.15, 0.10, 0.10, 0.10, 0.12, 0.20,   # 00–05
    0.40, 0.60, 0.55, 0.40, 0.35, 0.35,   # 06–11
    0.40, 0.45, 0.40, 0.35, 0.40, 0.65,   # 12–17
    0.80, 0.75, 0.55, 0.40, 0.25, 0.18,   # 18–23
]

LOAD_WINTER = [
    0.20, 0.15, 0.15, 0.15, 0.20, 0.35,   # 00–05  (more heating/lighting)
    0.60, 0.80, 0.70, 0.55, 0.50, 0.50,   # 06–11
    0.55, 0.55, 0.50, 0.55, 0.70, 0.95,   # 12–17
    1.10, 1.00, 0.80, 0.60, 0.40, 0.25,   # 18–23
]

# Hourly PV capacity factor profiles (fraction of peak, synthetic clear-sky shape)
def _bell(hour, peak_hour, width, amplitude):
    """Simple Gaussian bell for a single-hump PV day."""
    return amplitude * math.exp(-0.5 * ((hour - peak_hour) / width) ** 2)

def pv_cf_summer(hour):
    """Longer solar day, higher sun, sunrise ~06:00, sunset ~20:00."""
    if 6 <= hour <= 20:
        return min(1.0, _bell(hour, 13, 3.5, 1.05))
    return 0.0

def pv_cf_winter(hour):
    """Shorter solar day, lower sun angle (~60 % of summer peak), sunrise ~08:00, sunset ~16:00."""
    if 8 <= hour <= 16:
        return min(1.0, _bell(hour, 12, 2.0, 0.60))
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# SIMULATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def simulate(name, load_24h, pv_cf_fn, days=3):
    """
    Run hourly simulation for `days` days.
    Returns list of dicts with columns:
      hour, load_kw, pv_gen_kw, batt_soc_kwh,
      unmet_kw, curtailed_kw, net_kw
    """
    rows = []
    soc = BATT_INIT_SOC_KWH

    for d in range(days):
        for h in range(24):
            abs_hour = d * 24 + h
            load = load_24h[h]
            pv   = PV_PEAK_KW * pv_cf_fn(h)
            net  = pv - load        # + means surplus

            unmet     = 0.0
            curtailed = 0.0

            if net >= 0:
                # Surplus: charge battery
                charge_avail = (BATT_CAPACITY_KWH - soc) / BATT_EFF
                charge       = min(net, charge_avail)
                soc         += charge * BATT_EFF
                curtailed    = net - charge
            else:
                # Deficit: discharge battery
                deficit      = -net
                discharge    = min(deficit, soc - BATT_MIN_SOC_KWH)
                soc         -= discharge
                unmet        = deficit - discharge

            rows.append({
                "scenario":    name,
                "day":         d + 1,
                "hour_of_day": h,
                "abs_hour":    abs_hour,
                "load_kw":     round(load, 4),
                "pv_gen_kw":   round(pv,  4),
                "net_kw":      round(net, 4),
                "batt_soc_kwh":round(soc, 4),
                "unmet_kw":    round(unmet, 4),
                "curtailed_kw":round(curtailed, 4),
            })

    return rows


def summarize(rows, name):
    total_load    = sum(r["load_kw"]     for r in rows)
    total_pv      = sum(r["pv_gen_kw"]   for r in rows)
    total_unmet   = sum(r["unmet_kw"]    for r in rows)
    total_curt    = sum(r["curtailed_kw"] for r in rows)
    reliability   = 100 * (1 - total_unmet / total_load) if total_load else 0
    self_suf      = 100 * (total_pv - total_curt) / total_load if total_load else 0
    print(f"\n── {name} (72-hour summary) ──")
    print(f"  Total load         : {total_load:.2f} kWh")
    print(f"  Total PV generated : {total_pv:.2f} kWh")
    print(f"  Unmet load         : {total_unmet:.2f} kWh  ({100*total_unmet/total_load:.1f}% of load)")
    print(f"  Curtailed PV       : {total_curt:.2f} kWh")
    print(f"  Load reliability   : {reliability:.1f}%")
    print(f"  Served-energy ratio: {self_suf:.1f}%  (simplified; useful PV incl. storage effects)")


# ─────────────────────────────────────────────────────────────────────────────
# PLOT
# ─────────────────────────────────────────────────────────────────────────────

def make_plot(summer_rows, winter_rows, out_path):
    fig = plt.figure(figsize=(14, 10))
    fig.suptitle(
        "Off-Grid Cabin — Solar + Battery Sizing Sandbox\n"
        "(Illustrative synthetic parameters, 72-hour simulation)",
        fontsize=13, fontweight="bold", y=0.98,
    )
    gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.55, wspace=0.35)

    scenarios = [
        ("Summer", summer_rows, "#e8a000"),
        ("Winter", winter_rows, "#3a7fc1"),
    ]

    for col, (label, rows, color) in enumerate(scenarios):
        hours      = [r["abs_hour"]    for r in rows]
        load       = [r["load_kw"]     for r in rows]
        pv         = [r["pv_gen_kw"]   for r in rows]
        soc        = [r["batt_soc_kwh"] for r in rows]
        unmet      = [r["unmet_kw"]    for r in rows]
        curtailed  = [r["curtailed_kw"] for r in rows]

        # Row 0: PV vs load
        ax0 = fig.add_subplot(gs[0, col])
        ax0.fill_between(hours, pv,   alpha=0.4, color=color,   label="PV gen")
        ax0.fill_between(hours, load, alpha=0.4, color="#666",  label="Load")
        ax0.plot(hours, pv,   color=color,  linewidth=1.2)
        ax0.plot(hours, load, color="#444", linewidth=1.2)
        ax0.set_title(f"{label} — PV Gen vs Load (kW)", fontsize=10)
        ax0.set_ylabel("kW")
        ax0.legend(fontsize=8, loc="upper right")
        ax0.set_xticks([0, 24, 48, 72])
        ax0.set_xticklabels(["Day 1", "Day 2", "Day 3", "End"])
        ax0.set_xlim(0, 72)

        # Row 1: Battery SOC
        ax1 = fig.add_subplot(gs[1, col])
        ax1.plot(hours, soc, color=color, linewidth=1.5, label="Battery SOC")
        ax1.axhline(BATT_MIN_SOC_KWH, color="red", linestyle="--", linewidth=0.9, label=f"Min SOC ({BATT_MIN_SOC_KWH} kWh)")
        ax1.axhline(BATT_CAPACITY_KWH, color="green", linestyle=":", linewidth=0.9, label=f"Capacity ({BATT_CAPACITY_KWH} kWh)")
        ax1.set_title(f"{label} — Battery State of Charge (kWh)", fontsize=10)
        ax1.set_ylabel("kWh")
        ax1.set_ylim(0, BATT_CAPACITY_KWH + 1)
        ax1.legend(fontsize=8, loc="upper right")
        ax1.set_xticks([0, 24, 48, 72])
        ax1.set_xticklabels(["Day 1", "Day 2", "Day 3", "End"])
        ax1.set_xlim(0, 72)

        # Row 2: Unmet load & curtailed PV
        ax2 = fig.add_subplot(gs[2, col])
        ax2.bar(hours, unmet,     width=0.9, color="#d9534f", alpha=0.8, label="Unmet load (kW)")
        ax2.bar(hours, curtailed, width=0.9, color="#5bc0de", alpha=0.6, label="Curtailed PV (kW)", bottom=[0]*len(hours))
        ax2.set_title(f"{label} — Unmet Load & Curtailed PV (kW)", fontsize=10)
        ax2.set_ylabel("kW")
        ax2.legend(fontsize=8, loc="upper right")
        ax2.set_xticks([0, 24, 48, 72])
        ax2.set_xticklabels(["Day 1", "Day 2", "Day 3", "End"])
        ax2.set_xlim(-0.5, 72.5)

    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    print(f"\nPNG saved → {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))

    summer = simulate("summer", LOAD_SUMMER, pv_cf_summer)
    winter = simulate("winter", LOAD_WINTER, pv_cf_winter)

    summarize(summer, "Summer")
    summarize(winter, "Winter")

    # Write CSV
    all_rows = summer + winter
    csv_path = os.path.join(out_dir, "solar_battery_sandbox.csv")
    fieldnames = ["scenario","day","hour_of_day","abs_hour","load_kw",
                  "pv_gen_kw","net_kw","batt_soc_kwh","unmet_kw","curtailed_kw"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nCSV saved → {csv_path}")

    # Write PNG
    if HAS_MPL:
        png_path = os.path.join(out_dir, "solar_battery_sandbox.png")
        make_plot(summer, winter, png_path)
    else:
        print("Skipping PNG (matplotlib unavailable).")


if __name__ == "__main__":
    main()
