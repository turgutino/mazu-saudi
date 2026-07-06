# =============================================================================
# Saudi Arabia Extreme Event Indicators
# Based on: docs/气象数据变量合并整理_沙特极端事件指标.xlsx
# Requirements: xarray, netCDF4, numpy
# =============================================================================

import argparse
import calendar
import glob
import json
from pathlib import Path

import numpy as np
import xarray as xr


OUTPUT_DIR = "output_indicators"

MISSING_ADVANCED_INDICATORS = [
    "LCL/LFC/EL require vertical thermodynamic profiles",
    "500 hPa height anomaly and ridge strength require pressure-level geopotential height plus baseline",
    "SPI and precipitation anomaly require a multi-year climatological baseline",
    "PET/ET0 requires a validated pressure/radiation/wind/temperature workflow",
]

GRAVITY = 9.80665
EARTH_RADIUS_M = 6_371_000.0


def discover_periods(data_dir, start=None, end=None):
    """Discover daily periods from partitioned extracted Saudi outputs."""
    root = Path(data_dir)
    periods = set()
    for dataset_dir in (root / "ds2", root / "ds4"):
        if dataset_dir.exists():
            periods.update(
                child.name
                for child in dataset_dir.iterdir()
                if child.is_dir() and child.name.isdigit() and len(child.name) == 8
            )
    ds10_daily = root / "ds10_daily"
    if ds10_daily.exists():
        for path in ds10_daily.glob("*/saudi_ds10_daily_*.npz"):
            day = path.stem.removeprefix("saudi_ds10_daily_")
            if day.isdigit() and len(day) == 8:
                periods.add(day)

    selected = sorted(periods)
    if start:
        selected = [period for period in selected if period >= start]
    if end:
        selected = [period for period in selected if period <= end]
    return selected


def _first_existing(pattern):
    paths = sorted(Path(path) for path in glob.glob(pattern) if not Path(path).name.startswith("._"))
    return paths[0] if paths else None


def _open_first(root, patterns):
    for pattern in patterns:
        path = _first_existing(str(root / pattern))
        if path is not None:
            return xr.open_dataset(path)
    return None


def load_datasets(data_dir="output_saudi", period=None):
    """Load partitioned Saudi region outputs for one day or month.

    The extractor writes files under directories such as:
    ds1/202506/saudi_ds1_ART_SINGLE_GLB_0P10_MONTH_AVG_202506.nc
    ds2/20250601/saudi_ds2_ART_SINGLE_GLB_0P10_DAY_SFC_20250601.nc
    ds4/20250601/saudi_ds4_*.nc
    ds10_daily/202506/saudi_ds10_daily_20250601.npz
    """
    root = Path(data_dir)
    if period is None:
        periods = discover_periods(root)
        if not periods:
            return {}
        period = periods[-1]

    period = str(period)
    month = period[:6]
    datasets = {"period": period, "month": month}

    ds1_root = root / "ds1" / month
    datasets["ds1_avg"] = _open_first(
        ds1_root,
        [
            f"saudi_ds1_ART_SINGLE_GLB_0P10_MONTH_AVG_{month}.nc",
            f"*AVG*{month}.nc",
        ],
    )
    datasets["ds1_acc"] = _open_first(
        ds1_root,
        [
            f"saudi_ds1_ART_SINGLE_GLB_0P10_MONTH_ACC_{month}.nc",
            f"*ACC*{month}.nc",
        ],
    )
    datasets["ds1_sfc"] = _open_first(
        ds1_root,
        [
            f"saudi_ds1_ART_SINGLE_GLB_0P10_MONTH_SFC_{month}.nc",
            f"*SFC*{month}.nc",
        ],
    )

    if len(period) == 8:
        ds2_root = root / "ds2" / period
        datasets["ds2_avg"] = _open_first(ds2_root, [f"*DAY_AVG_{period}.nc"])
        datasets["ds2_sfc"] = _open_first(ds2_root, [f"*DAY_SFC_{period}.nc"])
        datasets["ds2_acc"] = _open_first(ds2_root, [f"*DAY_ACC_{period}.nc"])
        datasets["ds2_max"] = _open_first(ds2_root, [f"*DAY_MAX_{period}.nc"])
        datasets["ds2_min"] = _open_first(ds2_root, [f"*DAY_MIN_{period}.nc"])
        datasets["ds2_anal"] = _open_first(ds2_root, [f"*DAY_ANAL_{period}.nc"])
        datasets["ds4"] = load_sst_dataset(root / "ds4" / period)
        datasets["ds10_daily"] = load_ds10_daily_npz(
            root / "ds10_daily" / month / f"saudi_ds10_daily_{period}.npz"
        )

    return {key: value for key, value in datasets.items() if value is not None}


def load_sst_dataset(day_dir):
    day_dir = Path(day_dir)
    if not day_dir.exists():
        return None
    paths = sorted(path for path in day_dir.glob("*.nc") if not path.name.startswith("._"))
    if not paths:
        return None

    arrays = []
    for index, path in enumerate(paths):
        with xr.open_dataset(path) as ds:
            sst = ds["analysed_sst"].load().expand_dims(time=[index])
        arrays.append(sst)
    return xr.Dataset({"analysed_sst": xr.concat(arrays, dim="time")})


def load_ds10_daily_npz(path):
    path = Path(path)
    if not path.exists():
        return None
    with np.load(path) as data:
        lat = np.asarray(data["lat"])
        lon = np.asarray(data["lon"])
        coords = {"latitude": lat, "longitude": lon}
        variables = {}
        for name in ["daily_total", "max_30min", "max_1h", "max_3h", "max_6h", "rainy_steps"]:
            if name in data.files:
                variables[name] = _grid_data_array(np.asarray(data[name]), coords, name)
        if "time_count" in data.files:
            variables["time_count"] = xr.DataArray(np.asarray(data["time_count"]))
    return xr.Dataset(variables, attrs={"source_file": str(path)})


def _grid_data_array(values, coords, name):
    lat_count = len(coords["latitude"])
    lon_count = len(coords["longitude"])
    arr = np.asarray(values)
    if arr.shape == (lat_count, lon_count):
        data = arr
    elif arr.shape == (lon_count, lat_count):
        data = arr.T
    else:
        raise ValueError(f"{name} shape {arr.shape} does not match lat/lon grid")
    return xr.DataArray(data, dims=("latitude", "longitude"), coords=coords)


def _k_to_c(value):
    return value - 273.15


def _ratio(numerator, denominator):
    return xr.where(np.abs(denominator) > 1e-12, numerator / denominator, np.nan)


def _with_attrs(array, long_name, units, formula=None):
    array.attrs["long_name"] = long_name
    array.attrs["units"] = units
    if formula:
        array.attrs["formula"] = formula
    return array


def days_in_month(month):
    return calendar.monthrange(int(str(month)[:4]), int(str(month)[4:6]))[1]


def add_monthly_surface_indicators(results, ds):
    if "prate" in ds:
        results["monthly_precip_mmday"] = _with_attrs(
            ds["prate"] * 86400.0,
            "Monthly mean precipitation rate converted to mm/day",
            "mm/day",
            "prate * 86400",
        )
    if {"cpr", "prate"}.issubset(ds):
        results["monthly_convective_precip_ratio"] = _with_attrs(
            _ratio(ds["cpr"], ds["prate"]),
            "Monthly convective precipitation fraction",
            "1",
            "cpr / prate",
        )
    if {"avg_slhtf", "avg_ishf"}.issubset(ds):
        results["monthly_bowen_ratio"] = _with_attrs(
            _ratio(ds["avg_ishf"], ds["avg_slhtf"]),
            "Monthly Bowen ratio",
            "1",
            "avg_ishf / avg_slhtf",
        )
    if {"sdswrf", "suswrf", "sdlwrf", "sulwrf"}.issubset(ds):
        sw_net = ds["sdswrf"] - ds["suswrf"]
        lw_net = ds["sdlwrf"] - ds["sulwrf"]
        results["monthly_sw_net"] = _with_attrs(sw_net, "Monthly net shortwave radiation", "W m-2", "sdswrf - suswrf")
        results["monthly_lw_net"] = _with_attrs(lw_net, "Monthly net longwave radiation", "W m-2", "sdlwrf - sulwrf")
        results["monthly_net_radiation"] = _with_attrs(sw_net + lw_net, "Monthly net radiation", "W m-2", "SWnet + LWnet")
    if {"avg_ishf", "sdswrf", "avg_al"}.issubset(ds):
        results["monthly_heat_stress_index"] = _with_attrs(
            ds["avg_ishf"] + (1.0 - ds["avg_al"] / 100.0) * ds["sdswrf"],
            "Monthly surface heat stress proxy",
            "W m-2",
            "avg_ishf + (1 - avg_al/100) * sdswrf",
        )
    if {"avg_utaua", "avg_vtaua"}.issubset(ds):
        results["monthly_wind_stress_mag"] = _with_attrs(
            np.sqrt(ds["avg_utaua"] ** 2 + ds["avg_vtaua"] ** 2),
            "Monthly surface wind stress magnitude",
            "N m-2",
            "sqrt(avg_utaua^2 + avg_vtaua^2)",
        )
    if {"iegwss", "ingwss"}.issubset(ds):
        results["monthly_orographic_stress"] = _with_attrs(
            np.sqrt(ds["iegwss"] ** 2 + ds["ingwss"] ** 2),
            "Monthly gravity-wave surface stress magnitude",
            "N m-2",
            "sqrt(iegwss^2 + ingwss^2)",
        )
    if {"duvb", "cduvb"}.issubset(ds):
        results["monthly_uvb_flux"] = _with_attrs(ds["duvb"], "Monthly UV-B downward solar flux", "W m-2")
        results["monthly_uvb_clear_ratio"] = _with_attrs(
            _ratio(ds["cduvb"], ds["duvb"]),
            "Monthly clear-sky to all-sky UV-B ratio",
            "1",
            "cduvb / duvb",
        )


def add_monthly_accumulation_indicators(results, ds, month):
    if ds is None:
        return
    if "tp" in ds:
        results["monthly_precip_total"] = _with_attrs(ds["tp"], "Monthly total precipitation", "mm", "tp")
        results["monthly_precip_mmday"] = _with_attrs(
            ds["tp"] / days_in_month(month),
            "Monthly total precipitation converted to daily mean",
            "mm/day",
            "tp / days_in_month",
        )
    if "acpcp" in ds:
        results["monthly_convective_precip"] = _with_attrs(ds["acpcp"], "Monthly convective precipitation", "mm", "acpcp")
    if "ncpcp" in ds:
        results["monthly_large_scale_precip"] = _with_attrs(ds["ncpcp"], "Monthly non-convective precipitation", "mm", "ncpcp")
    if {"acpcp", "tp"}.issubset(ds):
        results["monthly_convective_precip_ratio"] = _with_attrs(
            _ratio(ds["acpcp"], ds["tp"]),
            "Monthly convective precipitation fraction",
            "1",
            "acpcp / tp",
        )


def add_daily_precip_energy_indicators(results, avg_ds, acc_ds):
    if avg_ds is not None and "prate" in avg_ds:
        results["precip_mmday"] = _with_attrs(
            avg_ds["prate"] * 86400.0,
            "Daily mean precipitation rate converted to mm/day",
            "mm/day",
            "prate * 86400",
        )
    if avg_ds is not None and {"cpr", "prate"}.issubset(avg_ds):
        results["convective_precip_ratio"] = _with_attrs(
            _ratio(avg_ds["cpr"], avg_ds["prate"]),
            "Daily convective precipitation fraction",
            "1",
            "cpr / prate",
        )
    if acc_ds is not None:
        if "tp" in acc_ds:
            results["daily_precip_total"] = _with_attrs(acc_ds["tp"], "Daily total precipitation", "mm", "tp")
        if "acpcp" in acc_ds:
            results["daily_convective_precip"] = _with_attrs(acc_ds["acpcp"], "Daily convective precipitation", "mm", "acpcp")
        if "ncpcp" in acc_ds:
            results["daily_large_scale_precip"] = _with_attrs(acc_ds["ncpcp"], "Daily non-convective precipitation", "mm", "ncpcp")
    if avg_ds is not None and {"avg_slhtf", "avg_ishf"}.issubset(avg_ds):
        results["bowen_ratio"] = _with_attrs(_ratio(avg_ds["avg_ishf"], avg_ds["avg_slhtf"]), "Daily Bowen ratio", "1", "avg_ishf / avg_slhtf")
    if avg_ds is not None and {"sdswrf", "suswrf", "sdlwrf", "sulwrf"}.issubset(avg_ds):
        sw_net = avg_ds["sdswrf"] - avg_ds["suswrf"]
        lw_net = avg_ds["sdlwrf"] - avg_ds["sulwrf"]
        results["sw_net"] = _with_attrs(sw_net, "Daily net shortwave radiation", "W m-2", "sdswrf - suswrf")
        results["lw_net"] = _with_attrs(lw_net, "Daily net longwave radiation", "W m-2", "sdlwrf - sulwrf")
        results["net_radiation"] = _with_attrs(sw_net + lw_net, "Daily net radiation", "W m-2", "SWnet + LWnet")
    if avg_ds is not None and {"avg_ishf", "sdswrf", "avg_al"}.issubset(avg_ds):
        results["heat_stress_index"] = _with_attrs(
            avg_ds["avg_ishf"] + (1.0 - avg_ds["avg_al"] / 100.0) * avg_ds["sdswrf"],
            "Daily surface heat stress proxy",
            "W m-2",
            "avg_ishf + (1 - avg_al/100) * sdswrf",
        )


def add_daily_surface_indicators(results, sfc_ds, max_ds, min_ds):
    if sfc_ds is not None:
        if "t2m" in sfc_ds:
            t2m_c = _k_to_c(sfc_ds["t2m"])
            results["t2m_c"] = _with_attrs(t2m_c, "2 m air temperature", "degC", "t2m - 273.15")
        else:
            t2m_c = None
        if "d2m" in sfc_ds:
            d2m_c = _k_to_c(sfc_ds["d2m"])
            results["d2m_c"] = _with_attrs(d2m_c, "2 m dewpoint temperature", "degC", "d2m - 273.15")
        else:
            d2m_c = None
        if t2m_c is not None and d2m_c is not None:
            results["dewpoint_depression_c"] = _with_attrs(t2m_c - d2m_c, "2 m dewpoint depression", "degC", "T2m - Td2m")
        if "r2" in sfc_ds:
            rh = sfc_ds["r2"]
            results["rh2m"] = _with_attrs(rh, "2 m relative humidity", "%")
            if t2m_c is not None:
                results["vpd_kpa"] = _with_attrs(vapor_pressure_deficit(t2m_c, rh), "Vapor pressure deficit", "kPa", "es(T) * (1 - RH/100)")
                results["heat_index_c"] = _with_attrs(heat_index_celsius(t2m_c, rh), "Heat index", "degC", "Rothfusz regression")
        if "sh2" in sfc_ds:
            results["sh2m"] = _with_attrs(sfc_ds["sh2"], "2 m specific humidity", "kg kg-1")
        if "aptmp" in sfc_ds:
            results["apparent_temp_c"] = _with_attrs(_k_to_c(sfc_ds["aptmp"]), "Apparent temperature", "degC", "aptmp - 273.15")
        if {"u10", "v10"}.issubset(sfc_ds):
            results["wind10_speed"] = _with_attrs(np.sqrt(sfc_ds["u10"] ** 2 + sfc_ds["v10"] ** 2), "10 m wind speed", "m s-1", "sqrt(u10^2 + v10^2)")
        add_cloud_indicators(results, sfc_ds)

    if max_ds is not None and "tmax" in max_ds:
        results["tmax_c"] = _with_attrs(_k_to_c(max_ds["tmax"]), "Daily maximum 2 m temperature", "degC", "tmax - 273.15")
    if min_ds is not None and "tmin" in min_ds:
        results["tmin_c"] = _with_attrs(_k_to_c(min_ds["tmin"]), "Daily minimum 2 m temperature", "degC", "tmin - 273.15")
    if "tmax_c" in results and "tmin_c" in results:
        results["diurnal_temp_range_c"] = _with_attrs(results["tmax_c"] - results["tmin_c"], "Daily temperature range", "degC", "tmax - tmin")
    if max_ds is not None and "qmax" in max_ds:
        results["qmax_2m"] = _with_attrs(max_ds["qmax"], "Daily maximum 2 m specific humidity", "kg kg-1")
    if min_ds is not None and "qmin" in min_ds:
        results["qmin_2m"] = _with_attrs(min_ds["qmin"], "Daily minimum 2 m specific humidity", "kg kg-1")


def add_cloud_indicators(results, ds):
    mapping = {
        "tcc": "total_cloud_cover",
        "tcc_lowCloudLayer_0_0": "low_cloud_cover",
        "tcc_middleCloudLayer_0_0": "middle_cloud_cover",
        "tcc_highCloudLayer_0_0": "high_cloud_cover",
    }
    for source, target in mapping.items():
        if source in ds:
            results[target] = _with_attrs(ds[source], target.replace("_", " ").title(), "%")


def vapor_pressure_deficit(temp_c, rh_percent):
    saturation = 0.6108 * np.exp((17.27 * temp_c) / (temp_c + 237.3))
    return saturation * (1.0 - rh_percent / 100.0)


def heat_index_celsius(temp_c, rh_percent):
    temp_f = temp_c * 9.0 / 5.0 + 32.0
    hi_f = (
        -42.379
        + 2.04901523 * temp_f
        + 10.14333127 * rh_percent
        - 0.22475541 * temp_f * rh_percent
        - 0.00683783 * temp_f**2
        - 0.05481717 * rh_percent**2
        + 0.00122874 * temp_f**2 * rh_percent
        + 0.00085282 * temp_f * rh_percent**2
        - 0.00000199 * temp_f**2 * rh_percent**2
    )
    hi_c = (hi_f - 32.0) * 5.0 / 9.0
    return xr.where((temp_c >= 26.7) & (rh_percent >= 40.0), hi_c, temp_c)


def add_instability_indicators(results, ds):
    if ds is None:
        return
    mapping = {
        "cape": ("cape", "Convective available potential energy", "J kg-1"),
        "cin": ("cin", "Convective inhibition", "J kg-1"),
        "lftx": ("surface_lifted_index", "Surface lifted index", "K"),
        "lftx4": ("best_lifted_index", "Best four-layer lifted index", "K"),
        "sp": ("surface_pressure", "Surface pressure", "Pa"),
        "orog": ("orography", "Orography", "m"),
    }
    for source, (target, long_name, units) in mapping.items():
        if source in ds:
            results[target] = _with_attrs(ds[source], long_name, units)


def pressure_level_name(ds):
    return "isobaricInhPa" if "isobaricInhPa" in ds.coords or "isobaricInhPa" in ds.dims else None


def pressure_var(ds, preferred_name, fallback_name=None):
    if preferred_name in ds and "isobaricInhPa" in ds[preferred_name].dims:
        return ds[preferred_name]
    if fallback_name and fallback_name in ds and "isobaricInhPa" in ds[fallback_name].dims:
        return ds[fallback_name]
    return None


def select_level(data, level_hpa, tolerance_hpa=30.0):
    if data is None or "isobaricInhPa" not in data.dims:
        return None
    levels = np.asarray(data["isobaricInhPa"].values, dtype=float)
    if levels.size == 0:
        return None
    nearest = float(levels[np.abs(levels - level_hpa).argmin()])
    if abs(nearest - level_hpa) > tolerance_hpa:
        return None
    return data.sel(isobaricInhPa=nearest)


def pressure_integral(data):
    sorted_data = data.sortby("isobaricInhPa")
    return sorted_data.integrate("isobaricInhPa") * 100.0


def horizontal_gradients(data):
    if "latitude" not in data.dims or "longitude" not in data.dims:
        return None, None
    lat = np.asarray(data["latitude"].values, dtype=float)
    lon = np.asarray(data["longitude"].values, dtype=float)
    values = np.asarray(data.values, dtype=float)
    if lat.size < 2 or lon.size < 2:
        return None, None

    d_dlat_deg = np.gradient(values, lat, axis=data.get_axis_num("latitude"))
    d_dlon_deg = np.gradient(values, lon, axis=data.get_axis_num("longitude"))
    dy_per_degree = np.pi * EARTH_RADIUS_M / 180.0
    dx_per_degree = dy_per_degree * np.cos(np.deg2rad(lat))
    dx_per_degree = np.where(np.abs(dx_per_degree) > 1e-6, dx_per_degree, np.nan)

    reshape = [1] * values.ndim
    reshape[data.get_axis_num("latitude")] = lat.size
    d_dx = d_dlon_deg / dx_per_degree.reshape(reshape)
    d_dy = d_dlat_deg / dy_per_degree
    return (
        xr.DataArray(d_dx, dims=data.dims, coords=data.coords),
        xr.DataArray(d_dy, dims=data.dims, coords=data.coords),
    )


def add_multilevel_indicators(results, ds):
    if ds is None or pressure_level_name(ds) is None:
        return

    q = pressure_var(ds, "q_isobaricInhPa", "q")
    u = pressure_var(ds, "u_isobaricInhPa", "u")
    v = pressure_var(ds, "v_isobaricInhPa", "v")
    gh = pressure_var(ds, "gh_isobaricInhPa", "gh")
    omega = pressure_var(ds, "w")
    absv = pressure_var(ds, "absv")

    if "pwat" in ds:
        results["pwat"] = _with_attrs(ds["pwat"], "Precipitable water", "kg m-2")

    if q is not None and u is not None and v is not None:
        ivt_u = pressure_integral(q * u) / GRAVITY
        ivt_v = pressure_integral(q * v) / GRAVITY
        results["ivt_u"] = _with_attrs(ivt_u, "Integrated vapor transport zonal component", "kg m-1 s-1", "1/g integral(q*u dp)")
        results["ivt_v"] = _with_attrs(ivt_v, "Integrated vapor transport meridional component", "kg m-1 s-1", "1/g integral(q*v dp)")
        results["ivt"] = _with_attrs(np.sqrt(ivt_u**2 + ivt_v**2), "Integrated vapor transport magnitude", "kg m-1 s-1", "sqrt(IVT_u^2 + IVT_v^2)")
        div_x, _ = horizontal_gradients(ivt_u)
        _, div_y = horizontal_gradients(ivt_v)
        if div_x is not None and div_y is not None:
            divergence = div_x + div_y
            results["ivt_divergence"] = _with_attrs(divergence, "Integrated vapor transport divergence", "kg m-2 s-1", "d(IVT_u)/dx + d(IVT_v)/dy")
            results["ivt_convergence"] = _with_attrs(-divergence, "Integrated vapor transport convergence", "kg m-2 s-1", "-IVT divergence")

        for level in (925, 850):
            q_level = select_level(q, level)
            u_level = select_level(u, level)
            v_level = select_level(v, level)
            if q_level is None or u_level is None or v_level is None:
                continue
            speed = np.sqrt(u_level**2 + v_level**2)
            results[f"wind{level}_speed"] = _with_attrs(speed, f"{level} hPa wind speed", "m s-1", f"sqrt(u{level}^2 + v{level}^2)")
            results[f"moisture_transport{level}"] = _with_attrs(q_level * speed, f"{level} hPa moisture transport magnitude", "m s-1", f"q{level} * wind_speed{level}")

    if u is not None and v is not None:
        for level in (300, 200):
            u_level = select_level(u, level)
            v_level = select_level(v, level)
            if u_level is not None and v_level is not None:
                results[f"jet{level}_speed"] = _with_attrs(np.sqrt(u_level**2 + v_level**2), f"{level} hPa wind speed", "m s-1", f"sqrt(u{level}^2 + v{level}^2)")

        for top_level in (300, 200):
            u850 = select_level(u, 850)
            v850 = select_level(v, 850)
            u_top = select_level(u, top_level)
            v_top = select_level(v, top_level)
            if u850 is not None and v850 is not None and u_top is not None and v_top is not None:
                results[f"wind_shear_850_{top_level}"] = _with_attrs(
                    np.sqrt((u_top - u850) ** 2 + (v_top - v850) ** 2),
                    f"850-{top_level} hPa vector wind shear",
                    "m s-1",
                    f"sqrt((u{top_level}-u850)^2 + (v{top_level}-v850)^2)",
                )

        u850 = select_level(u, 850)
        v850 = select_level(v, 850)
        if u850 is not None and v850 is not None:
            du_dx, du_dy = horizontal_gradients(u850)
            dv_dx, dv_dy = horizontal_gradients(v850)
            if du_dx is not None and du_dy is not None and dv_dx is not None and dv_dy is not None:
                results["relative_vorticity850"] = _with_attrs(dv_dx - du_dy, "850 hPa relative vorticity", "s-1", "dv/dx - du/dy")
                results["divergence850"] = _with_attrs(du_dx + dv_dy, "850 hPa horizontal divergence", "s-1", "du/dx + dv/dy")

    if absv is not None:
        absv850 = select_level(absv, 850)
        if absv850 is not None:
            results["absolute_vorticity850"] = _with_attrs(absv850, "850 hPa absolute vorticity", "s-1")

    if omega is not None:
        for level in (700, 500):
            omega_level = select_level(omega, level)
            if omega_level is not None:
                results[f"omega{level}"] = _with_attrs(omega_level, f"{level} hPa vertical velocity", "Pa s-1", f"omega at {level} hPa; negative is upward motion")

    if gh is not None:
        gh500 = select_level(gh, 500)
        if gh500 is not None:
            results["geopotential_height500"] = _with_attrs(gh500, "500 hPa geopotential height", "gpm")


def add_sst_indicators(results, ds):
    if ds is None or "analysed_sst" not in ds:
        return
    sst = ds["analysed_sst"]
    sst_c = xr.where(sst > 200.0, sst - 273.15, sst)
    results["sst_celsius"] = _with_attrs(sst_c, "Analysed sea surface temperature", "degC", "K to degC when source values exceed 200")
    lat_name = "lat" if "lat" in sst_c.coords else "latitude"
    lon_name = "lon" if "lon" in sst_c.coords else "longitude"
    regional_stats = {}
    for name, lat_slice, lon_slice in [
        ("red_sea", slice(12, 30), slice(32, 44)),
        ("persian_gulf", slice(23, 30), slice(48, 57)),
    ]:
        region = sst_c.sel({lat_name: lat_slice, lon_name: lon_slice})
        if region.size:
            regional_stats[f"{name}_mean_sst_c"] = float(region.mean(skipna=True))
            regional_stats[f"{name}_max_sst_c"] = float(region.max(skipna=True))
    results.attrs["sst_regional_stats"] = json.dumps(regional_stats, sort_keys=True)


def add_ds10_daily_indicators(results, ds):
    if ds is None:
        return
    mapping = {
        "daily_total": "ds10_daily_total",
        "max_30min": "ds10_max_30min",
        "max_1h": "ds10_max_1h",
        "max_3h": "ds10_max_3h",
        "max_6h": "ds10_max_6h",
        "rainy_steps": "ds10_rainy_steps",
    }
    for source, target in mapping.items():
        if source in ds:
            units = "steps" if source == "rainy_steps" else "mm"
            results[target] = _with_attrs(ds[source], target.replace("_", " ").title(), units)


def add_flash_flood_risk(results):
    terms = []
    if "daily_precip_total" in results:
        terms.append(xr.where(results["daily_precip_total"] >= 10.0, 1, 0))
    elif "precip_mmday" in results:
        terms.append(xr.where(results["precip_mmday"] >= 10.0, 1, 0))
    if "convective_precip_ratio" in results:
        terms.append(xr.where(results["convective_precip_ratio"] >= 0.5, 1, 0))
    if "cape" in results:
        terms.append(xr.where(results["cape"] >= 1000.0, 1, 0))
    if "wind10_speed" in results:
        terms.append(xr.where(results["wind10_speed"] >= 10.0, 1, 0))
    if "ds10_max_1h" in results:
        terms.append(xr.where(results["ds10_max_1h"] >= 10.0, 1, 0))
    if terms:
        risk = terms[0]
        for term in terms[1:]:
            risk = risk + term
        results["flash_flood_risk"] = _with_attrs(
            risk,
            "Flash flood screening score from available daily indicators",
            "score",
            "sum(threshold exceedance flags)",
        )


def compute_period(data_dir, period, output_dir=OUTPUT_DIR):
    datasets = load_datasets(data_dir, period)
    if not any(key.startswith("ds1_") or key.startswith("ds2_") or key == "ds10_daily" for key in datasets):
        return {"period": str(period), "status": "missing_inputs"}

    results = xr.Dataset(
        attrs={
            "period": str(period),
            "month": str(period)[:6],
            "source_root": str(Path(data_dir)),
            "missing_advanced_indicators": "; ".join(MISSING_ADVANCED_INDICATORS),
        }
    )

    if "ds1_avg" in datasets:
        add_monthly_surface_indicators(results, datasets["ds1_avg"])
    add_monthly_accumulation_indicators(results, datasets.get("ds1_acc"), datasets["month"])
    add_cloud_indicators(results, datasets["ds1_sfc"]) if "ds1_sfc" in datasets else None
    add_daily_precip_energy_indicators(results, datasets.get("ds2_avg"), datasets.get("ds2_acc"))
    add_daily_surface_indicators(results, datasets.get("ds2_sfc"), datasets.get("ds2_max"), datasets.get("ds2_min"))
    add_instability_indicators(results, datasets.get("ds2_anal"))
    add_multilevel_indicators(results, datasets.get("ds2_anal"))
    add_sst_indicators(results, datasets.get("ds4"))
    add_ds10_daily_indicators(results, datasets.get("ds10_daily"))
    add_flash_flood_risk(results)

    output_path = Path(output_dir) / f"saudi_indicators_{period}.nc"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_netcdf(output_path)
    return {
        "period": str(period),
        "status": "computed",
        "output": str(output_path),
        "indicator_count": len(results.data_vars),
    }


def compute_all(data_dir="output_saudi", output_dir=OUTPUT_DIR, period=None, start=None, end=None, all_periods=False, limit=None):
    if period:
        periods = [str(period)]
    else:
        periods = discover_periods(data_dir, start=start, end=end)
        if not all_periods and periods:
            periods = [periods[-1]]
    if limit is not None:
        periods = periods[:limit]

    if not periods:
        print("[ERROR] No extracted Saudi periods found.")
        return []

    results = []
    for selected_period in periods:
        payload = compute_period(data_dir, selected_period, output_dir=output_dir)
        results.append(payload)
        print(f"{payload['status']}\t{selected_period}\t{payload.get('output', '')}")
    return results


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Compute Saudi extreme event indicators from extracted region data.")
    parser.add_argument("data_dir", nargs="?", default="output_saudi")
    parser.add_argument("--output", default=OUTPUT_DIR)
    parser.add_argument("--period", help="Daily period such as 20250601. Defaults to latest discovered day.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--all", action="store_true", help="Compute all discovered periods instead of only the latest.")
    parser.add_argument("--limit", type=int)
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    compute_all(
        args.data_dir,
        output_dir=args.output,
        period=args.period,
        start=args.start,
        end=args.end,
        all_periods=args.all,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
