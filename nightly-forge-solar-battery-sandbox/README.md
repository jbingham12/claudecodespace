# Off-Grid Solar + Battery Sizing Sandbox

A simple, transparent hourly energy-balance simulator for an off-grid cabin.
**All parameters are illustrative synthetic defaults** — not from any private, confidential, or proprietary source.

---

## Purpose

Quickly visualize how a small PV array + battery bank performs across seasons:
- Do you run out of charge in winter? By how much?
- How much summer PV goes to waste (curtailment)?
- What does the battery state-of-charge look like over 72 hours?

---

## How to Run

```bash
cd /home/josh/agent-lab/nightly-forge/2026-06-18/artifact
python3 solar_battery_sandbox.py
```

Requires: Python 3.8+, `matplotlib` (for PNG output).
Install matplotlib if needed: `pip install matplotlib`

Outputs written to the same directory:
- `solar_battery_sandbox.png` — 6-panel visual figure
- `solar_battery_sandbox.csv` — hour-by-hour data for both scenarios

---

## Scenarios

| Scenario | Description |
|----------|-------------|
| **Summer** | Long solar day (~14 h), high sun, lower load (no space heating) |
| **Winter** | Short solar day (~8 h), ~60% of summer PV peak, higher load (heating/lighting) |

Both scenarios simulate 72 hours (3 days) using the same synthetic load profiles and the same PV array + battery.

---

## Assumptions (Illustrative Defaults)

All values below are synthetic stand-ins for a "typical small off-grid cabin." They are chosen to be physically plausible, not to represent any specific real site.

| Parameter | Value | Notes |
|-----------|-------|-------|
| PV array peak | 3.0 kW | Illustrative nameplate |
| Battery usable capacity | 10.0 kWh | e.g. two 5 kWh LFP modules (illustrative) |
| Battery min SOC | 1.0 kWh | ~10% depth-of-discharge floor |
| Battery initial SOC | 5.0 kWh | 50% at simulation start |
| Battery round-trip efficiency | 95% | Applied on charge; mid-range for LFP |
| Summer solar day | 06:00–20:00 | Gaussian bell peak at 13:00, amplitude ~1.05 before clamp |
| Winter solar day | 08:00–16:00 | Gaussian bell peak at 12:00, amplitude ~0.60 (lower sun angle) |
| Summer load | 0.10–0.80 kW | Peaks in morning/evening; illustrative cabin profile |
| Winter load | 0.15–1.10 kW | Higher due to heating and longer dark hours |

The PV capacity factor is a Gaussian bell curve — a simplified clear-sky shape that approximates a cloud-free day. Real output varies with cloud cover, temperature, soiling, shading, and inverter losses (not modeled here).

---

## Model Logic (per hour)

```
pv_gen  = pv_peak_kw × cf(hour)
net     = pv_gen − load_kw

if net ≥ 0 (surplus):
    charge battery up to capacity  →  remainder is curtailed PV
else (deficit):
    discharge battery down to min_soc  →  remainder is unmet load
```

Battery charging applies round-trip efficiency (energy in × eff stored).
Discharging is lossless in this model for simplicity.

---

## Outputs Explained

| Column | Meaning |
|--------|---------|
| `load_kw` | Synthetic cabin load (kW) |
| `pv_gen_kw` | PV array output (kW) |
| `net_kw` | pv_gen − load (positive = surplus) |
| `batt_soc_kwh` | Battery state of charge at end of hour |
| `unmet_kw` | Load not served (battery depleted and no PV) |
| `curtailed_kw` | Excess PV that couldn't be stored or used |

---

## Results (72-hour run, 2026-06-19)

**Summer:**
- Total load: 27.00 kWh | PV generated: 79.70 kWh
- Unmet load: 0.00 kWh (100% reliability) | Curtailed: 48.19 kWh
- Served-energy ratio: 116.7% — summer PV far exceeds cabin needs; value can exceed 100% here because the simplified metric counts useful PV plus stored battery energy before all losses are allocated. The practical takeaway is “oversized for summer.”

**Winter:**
- Total load: 38.40 kWh | PV generated: 26.45 kWh
- Unmet load: 8.65 kWh (22.5% of load unserved) | Curtailed: 0.00 kWh
- Served-energy ratio: 68.9% — winter shortfall highlights need for backup or larger array/battery

---

## Limitations

1. **Clear-sky only.** No cloud cover or weather variation is modeled. Real systems have significant day-to-day variation.
2. **Single load profile.** The same 24-hour load repeats every day. Real consumption varies by day and week.
3. **No temperature effects.** PV output drops ~0.4%/°C above 25°C (NOCT); battery capacity also degrades in cold. Not modeled.
4. **No inverter losses.** DC-AC conversion efficiency (~92–96%) is not separately accounted for.
5. **Battery aging not modeled.** Usable capacity declines over cycles/years.
6. **No grid or generator backup.** Unmet load is simply logged; no fallback supply is modeled.
7. **Gaussian CF shape is approximate.** Real PV output follows a more complex irradiance curve; this is a teaching approximation.
8. **All numbers are illustrative.** Do not use these defaults for actual system design without site-specific data and professional review.

---

## References / Further Reading

- NREL PVWatts Calculator (real CF data by location): https://pvwatts.nrel.gov/
- Solar irradiance basics: https://www.energy.gov/eere/solar/solar-radiation-basics
- LFP battery characteristics: generally available in manufacturer datasheets (e.g. CATL, Eve Energy — no specific product endorsed here)
- Off-grid system sizing guides: https://www.wholesalesolar.com/solar-information/off-grid-calculator (illustrative third-party resource, not an endorsement)

---

*Generated by Nightly Forge run 2026-06-18. Artifact is for educational/sandbox use only.*
