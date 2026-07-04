# =============================================================================
# Saudi Arabia Extreme Event Indicators
# Based on: 气象数据变量合并整理_沙特极端事件指标.xlsx (Sheet 4)
# Requirements: pip install xarray netCDF4 numpy scipy
# =============================================================================

import os
import numpy as np
import xarray as xr

# Saudi Arabia bounding box
LAT_MIN, LAT_MAX = 16.0, 32.0
LON_MIN, LON_MAX = 34.0, 56.0

OUTPUT_DIR = "output_indicators"

# =============================================================================
# SECTION 1: Load extracted Saudi datasets
# =============================================================================

def load_datasets(data_dir="output_saudi"):
    """Load all available extracted Saudi NetCDF files."""
    ds = {}

    ds1_path = os.path.join(data_dir, "saudi_ds1_surface_avg_202506.nc")
    if os.path.exists(ds1_path):
        ds["ds1"] = xr.open_dataset(ds1_path)
        print(f"[OK] DS1 loaded: {list(ds['ds1'].data_vars)[:5]}...")

    ds2_path = os.path.join(data_dir, "saudi_ds2_surface_avg_20250601.nc")
    if os.path.exists(ds2_path):
        ds["ds2"] = xr.open_dataset(ds2_path)
        print(f"[OK] DS2 loaded")

    ds4_path = os.path.join(data_dir, "saudi_sst_20250601_0000.nc")
    if os.path.exists(ds4_path):
        ds["ds4"] = xr.open_dataset(ds4_path)
        print(f"[OK] DS4 (SST) loaded")

    return ds


# =============================================================================
# SECTION 2: Precipitation & Flash Flood Indicators
# =============================================================================

def indicator_arst_ratio(ds1):
    """
    ARST Activation Ratio = cpr / prate
    Active Red Sea Trough index: ratio > 0.7 means convective flash flood risk.
    Formula: ratio = Convective precipitation rate / Total precipitation rate
    """
    prate = ds1["prate"]  # kg/m2/s total precip rate
    cpr   = ds1["cpr"]    # kg/m2/s convective precip rate

    # Avoid division by zero
    ratio = xr.where(prate > 1e-10, cpr / prate, 0.0)
    ratio.attrs = {
        "long_name": "ARST Activation Ratio (convective fraction)",
        "units": "dimensionless",
        "threshold": "0.7 = flash flood risk",
        "formula": "cpr / prate"
    }
    return ratio


def indicator_precip_mmday(ds1):
    """
    Convert precipitation rate to mm/day.
    Formula: P [mm/day] = prate [kg/m2/s] * 86400
    """
    prate = ds1["prate"]
    p_mm = prate * 86400.0
    p_mm.attrs = {
        "long_name": "Precipitation rate",
        "units": "mm/day",
        "formula": "prate * 86400"
    }
    return p_mm


def indicator_flash_flood_risk(ds1):
    """
    Flash flood composite risk index (0-3 scale):
      +1 if precipitation > 10 mm/day
      +1 if ARST ratio > 0.7 (convective)
      +1 if surface wind stress magnitude > 0.1 N/m2
    Higher score = higher flash flood risk.
    """
    p_mm   = indicator_precip_mmday(ds1)
    ratio  = indicator_arst_ratio(ds1)
    wind_m = np.sqrt(ds1["avg_utaua"]**2 + ds1["avg_vtaua"]**2)

    risk = (
        xr.where(p_mm > 10.0, 1, 0) +
        xr.where(ratio > 0.7,  1, 0) +
        xr.where(wind_m > 0.1, 1, 0)
    )
    risk.attrs = {
        "long_name": "Flash Flood Composite Risk Index",
        "units": "0-3 (3=highest risk)",
        "formula": "sum of 3 threshold conditions"
    }
    return risk


# =============================================================================
# SECTION 3: Extreme Heat Indicators
# =============================================================================

def indicator_bowen_ratio(ds1):
    """
    Bowen Ratio = Sensible Heat Flux / Latent Heat Flux (H / LE)
    High Bowen ratio = hot, dry surface (desert conditions).
    Formula: B = avg_ishf / avg_slhtf
    """
    H  = ds1["avg_ishf"]   # W/m2 sensible heat flux
    LE = ds1["avg_slhtf"]  # W/m2 latent heat flux

    bowen = xr.where(np.abs(LE) > 1.0, H / LE, np.nan)
    bowen.attrs = {
        "long_name": "Bowen Ratio (H/LE)",
        "units": "dimensionless",
        "formula": "avg_ishf / avg_slhtf",
        "note": "High value (>5) = dry desert; Low value (<1) = moist surface"
    }
    return bowen


def indicator_net_radiation(ds1):
    """
    Net Radiation Rn = SWnet + LWnet
    SWnet = sdswrf - suswrf  (incoming - reflected shortwave)
    LWnet = sdlwrf - sulwrf  (downward - upward longwave)
    Units: W/m2
    """
    SWnet = ds1["sdswrf"] - ds1["suswrf"]
    LWnet = ds1["sdlwrf"] - ds1["sulwrf"]
    Rn    = SWnet + LWnet

    SWnet.attrs = {"long_name": "Net shortwave radiation", "units": "W/m2", "formula": "sdswrf - suswrf"}
    LWnet.attrs = {"long_name": "Net longwave radiation",  "units": "W/m2", "formula": "sdlwrf - sulwrf"}
    Rn.attrs    = {"long_name": "Net radiation",           "units": "W/m2", "formula": "SWnet + LWnet"}
    return SWnet, LWnet, Rn


def indicator_heat_stress(ds1):
    """
    Surface Heat Stress Index:
    ADHSI (Asymmetric Diurnal Heat Stress Index) proxy using:
      - avg_ishf: sensible heat flux (direct heat to atmosphere)
      - sdswrf:   solar radiation input
      - avg_al:   albedo (reflectivity)

    Heat stress = avg_ishf + (1 - avg_al) * sdswrf
    High values indicate dangerous heat stress conditions.
    Threshold: > 350 W/m2 = extreme heat risk
    """
    ishf = ds1["avg_ishf"]
    srad = ds1["sdswrf"]
    alb  = ds1["avg_al"]

    # Absorbed solar + sensible heat transferred to air
    heat_stress = ishf + (1.0 - alb / 100.0) * srad
    heat_stress.attrs = {
        "long_name": "Surface Heat Stress Index (ADHSI proxy)",
        "units": "W/m2",
        "formula": "avg_ishf + (1 - avg_al/100) * sdswrf",
        "threshold": "350 W/m2 = extreme heat risk"
    }
    return heat_stress


def indicator_albedo_class(ds1):
    """
    Albedo classification for Saudi Arabia land types:
      avg_al > 35%  -> Desert sand (high reflectivity)
      20-35%        -> Rock/gravel
      < 20%         -> Urban/vegetation
    """
    alb = ds1["avg_al"]
    cls = xr.where(alb > 35, 2, xr.where(alb > 20, 1, 0))
    cls.attrs = {
        "long_name": "Albedo Surface Class",
        "units": "0=urban/veg, 1=rock, 2=desert sand",
        "formula": "threshold classification of avg_al"
    }
    return cls


# =============================================================================
# SECTION 4: SST-Based Indicators (Red Sea / Arabian Sea)
# =============================================================================

def indicator_sst_regional(ds4):
    """
    Regional SST statistics for:
      - Red Sea:    32-44°E, 12-30°N
      - Persian Gulf: 48-57°E, 23-30°N
    SST anomaly requires a climatological baseline (not available yet).
    """
    sst = ds4["analysed_sst"]

    # Clip to 273.15 K (remove land fill values below freezing)
    sst_ocean = xr.where(sst > 273.15, sst - 273.15, np.nan)  # Convert K -> C

    lat_name = "lat" if "lat" in ds4.coords else "latitude"
    lon_name = "lon" if "lon" in ds4.coords else "longitude"

    # Red Sea region
    red_sea = sst_ocean.sel(
        {lat_name: slice(12, 30), lon_name: slice(32, 44)}
    )
    # Persian Gulf
    persian = sst_ocean.sel(
        {lat_name: slice(23, 30), lon_name: slice(48, 57)}
    )

    stats = {
        "red_sea_mean":   float(red_sea.mean()),
        "red_sea_max":    float(red_sea.max()),
        "persian_mean":   float(persian.mean()),
        "persian_max":    float(persian.max()),
    }
    return sst_ocean, stats


# =============================================================================
# SECTION 5: Wind & Circulation Indicators
# =============================================================================

def indicator_surface_wind_stress(ds1):
    """
    Surface wind stress magnitude and direction.
    tau = sqrt(tau_u^2 + tau_v^2)  [N/m2]
    Wind stress > 0.1 N/m2 indicates significant wind forcing.
    """
    tau_u = ds1["avg_utaua"]  # N/m2 east-west
    tau_v = ds1["avg_vtaua"]  # N/m2 north-south

    tau_mag = np.sqrt(tau_u**2 + tau_v**2)
    tau_dir = np.degrees(np.arctan2(tau_v, tau_u))  # degrees from East

    tau_mag.attrs = {
        "long_name": "Surface wind stress magnitude",
        "units": "N/m2",
        "formula": "sqrt(avg_utaua^2 + avg_vtaua^2)"
    }
    tau_dir.attrs = {
        "long_name": "Surface wind stress direction",
        "units": "degrees (0=East, 90=North)"
    }
    return tau_mag, tau_dir


def indicator_orographic_stress(ds1):
    """
    Gravity wave surface stress magnitude from Hejaz mountains.
    tau_oro = sqrt(iegwss^2 + ingwss^2)
    Relevant for orographic precipitation enhancement near Jeddah.
    """
    eg = ds1["iegwss"]  # eastward gravity wave stress
    ng = ds1["ingwss"]  # northward gravity wave stress

    tau_oro = np.sqrt(eg**2 + ng**2)
    tau_oro.attrs = {
        "long_name": "Orographic gravity wave stress magnitude",
        "units": "N/m2",
        "formula": "sqrt(iegwss^2 + ingwss^2)",
        "note": "Hejaz mountains enhance precipitation on windward side"
    }
    return tau_oro


# =============================================================================
# SECTION 6: Radiation Budget
# =============================================================================

def indicator_uv_radiation(ds1):
    """
    UV-B radiation at surface.
    High UV-B + low cloud = intensified surface heating.
    Clear-sky UV-B ratio = cduvb / duvb (cloud transmittance)
    """
    uvb      = ds1["duvb"]   # UV-B downward solar flux  W/m2
    uvb_clr  = ds1["cduvb"]  # Clear-sky UV-B            W/m2

    # Cloud transmittance for UV-B
    clr_ratio = xr.where(uvb > 0.1, uvb_clr / uvb, 1.0)
    clr_ratio.attrs = {
        "long_name": "UV-B cloud transmittance ratio",
        "units": "dimensionless (1.0 = clear sky)",
        "formula": "cduvb / duvb"
    }
    return uvb, clr_ratio


# =============================================================================
# SECTION 7: Run all indicators and save
# =============================================================================

def compute_all(data_dir="output_saudi"):
    print("=" * 60)
    print("Saudi Arabia Extreme Event Indicators")
    print("Based on Xu Xiaoke's indicator list (Sheet 4)")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ds = load_datasets(data_dir)

    if "ds1" not in ds:
        print("[ERROR] DS1 not found. Run saudi_data_extract.py first.")
        return

    ds1 = ds["ds1"]
    results = xr.Dataset()

    print("\n--- Flash Flood Indicators ---")
    results["precip_mmday"]      = indicator_precip_mmday(ds1)
    results["arst_ratio"]        = indicator_arst_ratio(ds1)
    results["flash_flood_risk"]  = indicator_flash_flood_risk(ds1)
    tau_m, tau_d = indicator_surface_wind_stress(ds1)
    results["wind_stress_mag"]   = tau_m
    results["wind_stress_dir"]   = tau_d
    results["orographic_stress"] = indicator_orographic_stress(ds1)

    print("\n--- Extreme Heat Indicators ---")
    results["bowen_ratio"]       = indicator_bowen_ratio(ds1)
    SWnet, LWnet, Rn = indicator_net_radiation(ds1)
    results["sw_net"]            = SWnet
    results["lw_net"]            = LWnet
    results["net_radiation"]     = Rn
    results["heat_stress_index"] = indicator_heat_stress(ds1)
    results["albedo_class"]      = indicator_albedo_class(ds1)
    uvb, uvb_ratio = indicator_uv_radiation(ds1)
    results["uvb_flux"]          = uvb
    results["uvb_clear_ratio"]   = uvb_ratio

    print("\n--- SST Indicators ---")
    if "ds4" in ds:
        sst_c, sst_stats = indicator_sst_regional(ds["ds4"])
        results["sst_celsius"] = sst_c
        print(f"  Red Sea mean SST:     {sst_stats['red_sea_mean']:.2f} C")
        print(f"  Red Sea max SST:      {sst_stats['red_sea_max']:.2f} C")
        print(f"  Persian Gulf mean:    {sst_stats['persian_mean']:.2f} C")
        print(f"  Persian Gulf max:     {sst_stats['persian_max']:.2f} C")

    # Save
    out_file = os.path.join(OUTPUT_DIR, "saudi_indicators_202506.nc")
    results.to_netcdf(out_file)
    size_mb = os.path.getsize(out_file) / 1024 / 1024
    print(f"\n[SAVED] {out_file}  ({size_mb:.1f} MB)")
    print(f"Indicators: {list(results.data_vars)}")

    # Print summary statistics
    print("\n--- Summary (Saudi Arabia, June 2025) ---")
    for name in ["precip_mmday", "arst_ratio", "flash_flood_risk",
                  "heat_stress_index", "bowen_ratio", "net_radiation"]:
        if name in results:
            arr = results[name].values
            arr_valid = arr[~np.isnan(arr)]
            if len(arr_valid) > 0:
                print(f"  {name:25s}  mean={arr_valid.mean():.3f}  "
                      f"max={arr_valid.max():.3f}  "
                      f"min={arr_valid.min():.3f}")

    print("\nDone.")
    return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys

    data_dir = sys.argv[1] if len(sys.argv) > 1 else "output_saudi"

    if not os.path.isabs(data_dir):
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), data_dir)

    compute_all(data_dir)
