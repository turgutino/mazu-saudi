# =============================================================================
# CMA Dataset Extraction — Saudi Arabia Region
# Lat: 16-32°N, Lon: 34-56°E
# Author: Turgut (MAZU Competition 2026)
# Requirements: pip install xarray cfgrib netCDF4 numpy
# =============================================================================

import os
import numpy as np
import xarray as xr

# Saudi Arabia bounding box
LAT_MIN, LAT_MAX = 16.0, 32.0
LON_MIN, LON_MAX = 34.0, 56.0

OUTPUT_DIR = "output_saudi"


def extract_grib2(grib_file_path, output_name, level_type="surface"):
    """
    Extract Saudi Arabia region from GRIB2 file (DS1, DS2, DS3).
    level_type options: 'surface', 'atmosphere', 'isobaricInhPa', etc.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Opening: {os.path.basename(grib_file_path)}")
    ds = xr.open_dataset(
        grib_file_path,
        engine="cfgrib",
        backend_kwargs={"filter_by_keys": {"typeOfLevel": level_type}}
    )

    print(f"  Variables: {list(ds.data_vars)}")
    print(f"  Full shape: {dict(ds.sizes)}")

    # Latitude is descending (90 to -90) in CMA GRIB2
    saudi = ds.sel(
        latitude=slice(LAT_MAX, LAT_MIN),
        longitude=slice(LON_MIN, LON_MAX)
    )

    print(f"  Saudi shape: {dict(saudi.sizes)}")

    out_file = os.path.join(OUTPUT_DIR, output_name)
    saudi.to_netcdf(out_file)
    size_mb = os.path.getsize(out_file) / 1024 / 1024
    print(f"  Saved: {out_file} ({size_mb:.1f} MB)")

    ds.close()
    return saudi


def extract_netcdf(nc_file_path, output_name):
    """
    Extract Saudi Arabia region from NetCDF file (DS4, DS5).
    Used for SST (Sea Surface Temperature) data.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Opening: {os.path.basename(nc_file_path)}")
    ds = xr.open_dataset(nc_file_path, engine="netcdf4")

    print(f"  Variables: {list(ds.data_vars)}")
    print(f"  Full shape: {dict(ds.sizes)}")

    # Auto-detect lat/lon coordinate names
    lat_name = next((c for c in ds.coords if c.lower() in ["lat", "latitude"]), "lat")
    lon_name = next((c for c in ds.coords if c.lower() in ["lon", "longitude"]), "lon")

    # Try ascending order first, then descending
    saudi = ds.sel({lat_name: slice(LAT_MIN, LAT_MAX), lon_name: slice(LON_MIN, LON_MAX)})
    if saudi.sizes[lat_name] == 0:
        saudi = ds.sel({lat_name: slice(LAT_MAX, LAT_MIN), lon_name: slice(LON_MIN, LON_MAX)})

    print(f"  Saudi shape: {dict(saudi.sizes)}")

    out_file = os.path.join(OUTPUT_DIR, output_name)
    saudi.to_netcdf(out_file)
    size_mb = os.path.getsize(out_file) / 1024 / 1024
    print(f"  Saved: {out_file} ({size_mb:.1f} MB)")

    ds.close()
    return saudi


def extract_all(data_root):
    """
    Extract all CMA datasets (DS1-DS4) for Saudi Arabia region.
    data_root: path to folder containing 1_NAFP_..., 2_NAFP_..., 3_NAFP_..., 4_OCEA_... folders
    """
    print("=" * 60)
    print("CMA Data Extraction -- Saudi Arabia Region")
    print(f"Lat: {LAT_MIN}-{LAT_MAX}N | Lon: {LON_MIN}-{LON_MAX}E")
    print("=" * 60)

    # DS1 - Monthly atmospheric GRIB2
    ds1_path = os.path.join(data_root, "1_NAFP_ART_ATM_GLB_MONTH_PROD", "202506",
                            "ART_SINGLE_GLB_0P10_MONTH_AVG_202506.grib2")
    if os.path.exists(ds1_path):
        print("\n[DS1] Monthly Atmospheric:")
        extract_grib2(ds1_path, "saudi_ds1_surface_avg_202506.nc", level_type="surface")

    # DS2 - Daily surface GRIB2
    ds2_path = os.path.join(data_root, "2_NAFP_ART_SFC_GLB_DAY_PROD", "20250601",
                            "ART_SINGLE_GLB_0P10_DAY_AVG_20250601.grib2")
    if os.path.exists(ds2_path):
        print("\n[DS2] Daily Surface:")
        extract_grib2(ds2_path, "saudi_ds2_surface_avg_20250601.nc", level_type="surface")

    # DS3 - Monthly surface GRIB2
    ds3_path = os.path.join(data_root, "3_NAFP_ART_SFC_GLB_MONTH_PROD", "202506",
                            "ART_SINGLE_GLB_0P10_MONTH_AVG_202506.grib2")
    if os.path.exists(ds3_path):
        print("\n[DS3] Monthly Surface:")
        extract_grib2(ds3_path, "saudi_ds3_surface_avg_202506.nc", level_type="surface")

    # DS4 - SST NetCDF
    ds4_path = os.path.join(data_root, "4_OCEA_FUS_DAY_PRO", "20250601",
                            "Z_OCEN_C_BABJ_20250601000000_P_CODAS_GLB_0P10_6HOR_SST.nc")
    if os.path.exists(ds4_path):
        print("\n[DS4] Sea Surface Temperature:")
        extract_netcdf(ds4_path, "saudi_sst_20250601_0000.nc")

    print("\nDone! All files saved to:", os.path.abspath(OUTPUT_DIR))


def demo():
    """
    Generate synthetic sample data for Saudi Arabia region.
    Use this to test algorithms before real data is ready.
    """
    print("=" * 60)
    print("DEMO MODE -- Synthetic Saudi Arabia Data (30 days)")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    lats = np.arange(LAT_MIN, LAT_MAX + 0.1, 0.1)
    lons = np.arange(LON_MIN, LON_MAX + 0.1, 0.1)
    lat_grid, _ = np.meshgrid(lats, lons, indexing="ij")
    n_days, n_lat, n_lon = 30, len(lats), len(lons)

    # Temperature: 35-55C (Saudi summer)
    temp = (45.0
            + 5 * np.sin(np.linspace(0, 2 * np.pi, n_days))[:, None, None]
            - 0.006 * lat_grid[None, :, :]
            + np.random.normal(0, 2, (n_days, n_lat, n_lon)))

    # Precipitation: mostly 0, 2 flash flood events
    precip = np.random.exponential(0.5, (n_days, n_lat, n_lon))
    precip[precip < 2.0] = 0.0
    precip[7, 20:30, 15:25] = np.random.uniform(30, 80, (10, 10))
    precip[22, 15:25, 10:20] = np.random.uniform(20, 60, (10, 10))

    # SST: Red Sea 26-32C
    sst = (29.0
           - 0.003 * lat_grid[None, :, :]
           + 0.5 * np.sin(np.linspace(0, np.pi, n_days))[:, None, None]
           + np.random.normal(0, 0.5, (n_days, n_lat, n_lon)))

    # Wind
    wind_u = np.random.normal(-2, 3, (n_days, n_lat, n_lon))
    wind_v = np.random.normal(0, 2, (n_days, n_lat, n_lon))

    out_file = os.path.join(OUTPUT_DIR, "saudi_sample_30days.npz")
    np.savez_compressed(out_file,
                        lats=lats, lons=lons,
                        temperature=temp,
                        precipitation=precip,
                        sst=sst,
                        wind_u=wind_u,
                        wind_v=wind_v)

    print(f"Grid: {n_lat} x {n_lon} x {n_days} days")
    print(f"Temperature: [{temp.min():.1f}, {temp.max():.1f}] C")
    print(f"Precipitation: [{precip.min():.1f}, {precip.max():.1f}] mm/day")
    print(f"SST: [{sst.min():.1f}, {sst.max():.1f}] C")
    print(f"Flash flood events: Day 7 (Jeddah), Day 22")
    print(f"Saved: {out_file}")
    print(f"\nLoad with:")
    print(f"  import numpy as np")
    print(f"  d = np.load('{out_file}')")
    print(f"  temp = d['temperature']  # shape: ({n_days}, {n_lat}, {n_lon})")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2 or sys.argv[1] == "demo":
        demo()

    elif sys.argv[1] == "all":
        # Usage: python saudi_data_extract.py all E:\Data\Datas
        data_root = sys.argv[2] if len(sys.argv) > 2 else r"E:\Data\Datas"
        extract_all(data_root)

    elif sys.argv[1].endswith((".grib2", ".grb2", ".grb")):
        # Usage: python saudi_data_extract.py file.grib2
        name = "saudi_" + os.path.basename(sys.argv[1]).replace(".grib2", ".nc")
        level = sys.argv[2] if len(sys.argv) > 2 else "surface"
        extract_grib2(sys.argv[1], name, level_type=level)

    elif sys.argv[1].endswith(".nc"):
        # Usage: python saudi_data_extract.py file.nc
        name = "saudi_" + os.path.basename(sys.argv[1])
        extract_netcdf(sys.argv[1], name)

    else:
        print("Usage:")
        print("  python saudi_data_extract.py demo")
        print("  python saudi_data_extract.py all E:\\Data\\Datas")
        print("  python saudi_data_extract.py file.grib2 [level_type]")
        print("  python saudi_data_extract.py file.nc")
