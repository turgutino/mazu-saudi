import os
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

# Saudi Arabia bounding box
LAT_MIN, LAT_MAX = 16.0, 32.0
LON_MIN, LON_MAX = 34.0, 56.0
SAUDI_BBOX = {
    "lat_min": LAT_MIN,
    "lat_max": LAT_MAX,
    "lon_min": LON_MIN,
    "lon_max": LON_MAX,
}

OUTPUT_DIR = "output_saudi"

DATASET_DIRS = {
    "1_NAFP_ART_ATM_GLB_MONTH_PROD": "ds1",
    "2_NAFP_ART_SFC_GLB_DAY_PROD": "ds2",
    "3_NAFP_ART_SFC_GLB_MONTH_PROD": "ds3",
    "4_OCEA_FUS_DAY_PRO": "ds4",
    "10_SATE_PRECIPITATION_PRODUCT_2025": "ds10",
    "11_TCGD_MON_GLB_PROD": "ds11",
}

DATASET_ROOTS = {dataset: dirname for dirname, dataset in DATASET_DIRS.items()}


def require_xarray():
    try:
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError(
            "xarray is required for GRIB2/NetCDF extraction. "
            "Install it in the conda ml environment with cfgrib and netCDF4."
        ) from exc
    return xr


def require_h5py():
    try:
        import h5py
    except ImportError as exc:
        raise RuntimeError(
            "h5py is required for DS10 HDF5 satellite precipitation extraction."
        ) from exc
    return h5py


def is_metadata_path(path):
    """Return True for macOS AppleDouble metadata paths."""
    return any(part.startswith("._") for part in Path(path).parts)


def infer_dataset_id(path):
    for part in Path(path).parts:
        if part in DATASET_DIRS:
            return DATASET_DIRS[part]
    return None


def safe_output_name(dataset_id, source_path, suffix=".nc"):
    stem = Path(source_path).stem
    return f"saudi_{dataset_id}_{stem}{suffix}"


def ensure_output_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
    return Path(path)


def normalize_datasets(datasets):
    if datasets is None:
        return {"ds1", "ds2", "ds3", "ds4", "ds10", "ds11"}
    if isinstance(datasets, str):
        return {item.strip() for item in datasets.split(",") if item.strip()}
    return set(datasets)


def period_in_range(period, start=None, end=None):
    if start is not None and period < start:
        return False
    if end is not None and period > end:
        return False
    return True


def iter_clean_children(path):
    path = Path(path)
    if not path.exists():
        return
    for child in sorted(path.iterdir()):
        if not is_metadata_path(child):
            yield child


def discover_files(data_root, datasets=None, start=None, end=None, limit=None):
    selected = normalize_datasets(datasets)
    root = Path(data_root)
    records = []

    if "ds1" in selected:
        records.extend(discover_monthly_files(root, "ds1", ".grib2", start, end, remaining_limit(limit, records)))
    if "ds2" in selected:
        records.extend(discover_daily_files(root, "ds2", ".grib2", start, end, remaining_limit(limit, records)))
    if "ds3" in selected:
        records.extend(discover_monthly_files(root, "ds3", ".grib2", start, end, remaining_limit(limit, records)))
    if "ds4" in selected:
        records.extend(discover_daily_files(root, "ds4", ".nc", start, end, remaining_limit(limit, records)))
    if "ds10" in selected:
        records.extend(discover_monthly_files(root, "ds10", ".h5", start, end, remaining_limit(limit, records)))
    if "ds11" in selected:
        records.extend(discover_track_files(root, start, end, remaining_limit(limit, records)))

    return records


def remaining_limit(limit, records):
    if limit is None:
        return None
    return max(limit - len(records), 0)


def limit_reached(records, limit):
    return limit is not None and len(records) >= limit


def discover_monthly_files(root, dataset_id, suffix, start=None, end=None, limit=None):
    dataset_root = root / DATASET_ROOTS[dataset_id]
    records = []
    if limit == 0:
        return records
    for month_dir in iter_clean_children(dataset_root):
        if not month_dir.is_dir():
            continue
        period = month_dir.name
        if len(period) != 6 or not period.isdigit() or not period_in_range(period, start, end):
            continue
        for file_path in iter_clean_children(month_dir):
            if file_path.is_file() and file_path.suffix.lower() == suffix:
                records.append({"dataset": dataset_id, "path": file_path, "period": period})
                if limit_reached(records, limit):
                    return records
    return records


def discover_daily_files(root, dataset_id, suffix, start=None, end=None, limit=None):
    dataset_root = root / DATASET_ROOTS[dataset_id]
    records = []
    if limit == 0:
        return records
    for day_dir in iter_clean_children(dataset_root):
        if not day_dir.is_dir():
            continue
        period = day_dir.name
        if len(period) != 8 or not period.isdigit() or not period_in_range(period, start, end):
            continue
        for file_path in iter_clean_children(day_dir):
            if file_path.is_file() and file_path.suffix.lower() == suffix:
                records.append({"dataset": dataset_id, "path": file_path, "period": period})
                if limit_reached(records, limit):
                    return records
    return records


def discover_track_files(root, start=None, end=None, limit=None):
    dataset_root = root / DATASET_ROOTS["ds11"]
    records = []
    if limit == 0:
        return records
    for day_dir in iter_clean_children(dataset_root):
        if not day_dir.is_dir():
            continue
        period = day_dir.name
        if len(period) != 8 or not period.isdigit() or not period_in_range(period, start, end):
            continue
        for run_dir in iter_clean_children(day_dir):
            if not run_dir.is_dir() or not run_dir.name.startswith("t"):
                continue
            for file_path in iter_clean_children(run_dir):
                if file_path.is_file() and file_path.name.startswith("track_") and file_path.suffix == ".txt":
                    records.append({"dataset": "ds11", "path": file_path, "period": period})
                    if limit_reached(records, limit):
                        return records
    return records


def detect_lat_lon_names(ds):
    coord_names = list(ds.coords)
    lat_name = next(
        (name for name in coord_names if name.lower() in {"lat", "latitude"}),
        None,
    )
    lon_name = next(
        (name for name in coord_names if name.lower() in {"lon", "longitude"}),
        None,
    )
    if lat_name is None or lon_name is None:
        raise ValueError(f"Could not detect latitude/longitude coordinates: {coord_names}")
    return lat_name, lon_name


def coord_values(coord):
    values = getattr(coord, "values", coord)
    if hasattr(values, "tolist"):
        values = values.tolist()
    return list(values)


def coord_descending(coord):
    values = coord_values(coord)
    return len(values) >= 2 and values[0] > values[-1]


def clip_xarray_to_bbox(ds, bbox=SAUDI_BBOX):
    lat_name, lon_name = detect_lat_lon_names(ds)
    lat_slice = (
        slice(bbox["lat_max"], bbox["lat_min"])
        if coord_descending(ds.coords[lat_name])
        else slice(bbox["lat_min"], bbox["lat_max"])
    )
    lon_slice = (
        slice(bbox["lon_max"], bbox["lon_min"])
        if coord_descending(ds.coords[lon_name])
        else slice(bbox["lon_min"], bbox["lon_max"])
    )
    return ds.sel({lat_name: lat_slice, lon_name: lon_slice})


def extract_grib2_file(grib_file_path, output_path, level_type=None):
    xr = require_xarray()
    backend_kwargs = {"indexpath": ""}
    if level_type:
        backend_kwargs["filter_by_keys"] = {"typeOfLevel": level_type}
    ds = xr.open_dataset(
        grib_file_path,
        engine="cfgrib",
        backend_kwargs=backend_kwargs,
    )
    try:
        saudi = clip_xarray_to_bbox(ds)
        ensure_output_dir(Path(output_path).parent)
        saudi.to_netcdf(output_path)
        return Path(output_path)
    finally:
        ds.close()


def extract_netcdf_file(nc_file_path, output_path):
    xr = require_xarray()
    ds = xr.open_dataset(nc_file_path, engine="netcdf4")
    try:
        saudi = clip_xarray_to_bbox(ds)
        ensure_output_dir(Path(output_path).parent)
        saudi.to_netcdf(output_path)
        return Path(output_path)
    finally:
        ds.close()


def iter_hdf5_datasets(h5obj, prefix=""):
    for name, value in h5obj.items():
        full_name = f"{prefix}/{name}" if prefix else name
        if hasattr(value, "shape"):
            yield full_name, value
        else:
            yield from iter_hdf5_datasets(value, full_name)


def find_hdf5_lat_lon_datasets(h5):
    lat_aliases = {"lat", "latitude"}
    lon_aliases = {"lon", "longitude"}
    lat_name = None
    lon_name = None
    for name, dataset in iter_hdf5_datasets(h5):
        simple = name.split("/")[-1].lower()
        if simple in lat_aliases and is_coordinate_shape(dataset.shape) and lat_name is None:
            lat_name = name
        if simple in lon_aliases and is_coordinate_shape(dataset.shape) and lon_name is None:
            lon_name = name
    if lat_name is None or lon_name is None:
        raise ValueError("Could not find 1D latitude/longitude datasets in HDF5 file")
    return lat_name, lon_name


def is_coordinate_shape(shape):
    return len(shape) == 1 or (len(shape) == 2 and 1 in shape)


def read_hdf5_coord(dataset):
    return np.asarray(dataset[...]).reshape(-1)


def bbox_indices(values, min_value, max_value):
    values = np.asarray(values)
    matches = np.where((values >= min_value) & (values <= max_value))[0]
    if matches.size == 0:
        return matches, values[matches]
    return matches, values[matches]


def npz_key(name):
    return name.split("/")[-1].replace(" ", "_")


def crop_hdf5_data(data, lat_idx, lon_idx, lat_len, lon_len):
    if data.shape[-2:] == (lat_len, lon_len):
        data = np.take(data, lat_idx, axis=-2)
        data = np.take(data, lon_idx, axis=-1)
        return data
    if data.shape[-2:] == (lon_len, lat_len):
        data = np.take(data, lon_idx, axis=-2)
        data = np.take(data, lat_idx, axis=-1)
        return data
    return None


def extract_hdf5_grid_file(h5_file_path, output_path, bbox=SAUDI_BBOX):
    h5py = require_h5py()
    output_path = Path(output_path)
    with h5py.File(h5_file_path, "r") as h5:
        lat_name, lon_name = find_hdf5_lat_lon_datasets(h5)
        lats = read_hdf5_coord(h5[lat_name])
        lons = read_hdf5_coord(h5[lon_name])
        lat_idx, clipped_lats = bbox_indices(lats, bbox["lat_min"], bbox["lat_max"])
        lon_idx, clipped_lons = bbox_indices(lons, bbox["lon_min"], bbox["lon_max"])
        if lat_idx.size == 0 or lon_idx.size == 0:
            return None

        output = {
            "lat": clipped_lats,
            "lon": clipped_lons,
            "source_path": np.asarray(str(h5_file_path)),
        }
        for name, dataset in iter_hdf5_datasets(h5):
            if name in {lat_name, lon_name}:
                continue
            if len(dataset.shape) < 2:
                continue
            if dataset.shape[-2:] not in {
                (len(lats), len(lons)),
                (len(lons), len(lats)),
            }:
                continue
            data = np.asarray(dataset[...])
            data = crop_hdf5_data(data, lat_idx, lon_idx, len(lats), len(lons))
            if data is None:
                continue
            output[npz_key(name)] = data

    ensure_output_dir(output_path.parent)
    np.savez_compressed(output_path, **output)
    return output_path


def read_track_rows(track_file_path):
    lines = [
        line.strip()
        for line in Path(track_file_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        return [], []
    fieldnames = lines[0].split()
    rows = []
    for line in lines[1:]:
        values = line.split()
        if len(values) != len(fieldnames):
            continue
        rows.append(dict(zip(fieldnames, values)))
    return fieldnames, rows


def row_in_bbox(row, bbox=SAUDI_BBOX):
    try:
        lat = float(row["Lat"])
        lon = float(row["Lon"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        bbox["lat_min"] <= lat <= bbox["lat_max"]
        and bbox["lon_min"] <= lon <= bbox["lon_max"]
    )


def track_intersects_bbox(rows, bbox=SAUDI_BBOX):
    return any(row_in_bbox(row, bbox) for row in rows)


def extract_track_file(track_file_path, output_path, bbox=SAUDI_BBOX, keep_empty=False):
    fieldnames, rows = read_track_rows(track_file_path)
    if "Lat" not in fieldnames or "Lon" not in fieldnames:
        raise ValueError(f"Track file lacks Lat/Lon columns: {track_file_path}")

    kept_rows = [row for row in rows if row_in_bbox(row, bbox)]
    if not kept_rows and not keep_empty:
        return None

    output_path = Path(output_path)
    ensure_output_dir(output_path.parent)
    output_fields = fieldnames + ["source_file"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields)
        writer.writeheader()
        for row in kept_rows:
            output_row = dict(row)
            output_row["source_file"] = str(track_file_path)
            writer.writerow(output_row)
    return output_path


def output_suffix_for_dataset(dataset_id):
    if dataset_id == "ds10":
        return ".npz"
    if dataset_id == "ds11":
        return ".csv"
    return ".nc"


def output_path_for_record(record, output_root):
    dataset_id = record["dataset"]
    suffix = output_suffix_for_dataset(dataset_id)
    name = safe_output_name(dataset_id, record["path"], suffix=suffix)
    return Path(output_root) / dataset_id / record["period"] / name


def append_jsonl(path, payload):
    path = Path(path)
    ensure_output_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def process_record(record, output_root, level_type=None, overwrite=False, manifest=None, errors=None):
    output_path = output_path_for_record(record, output_root)
    source_path = record["path"]
    if output_path.exists() and not overwrite:
        payload = {
            "dataset": record["dataset"],
            "period": record["period"],
            "source": str(source_path),
            "output": str(output_path),
            "status": "skipped_existing",
        }
        if manifest:
            append_jsonl(manifest, payload)
        return payload

    try:
        dataset_id = record["dataset"]
        if dataset_id in {"ds1", "ds2", "ds3"}:
            result = extract_grib2_file(source_path, output_path, level_type=level_type)
        elif dataset_id == "ds4":
            result = extract_netcdf_file(source_path, output_path)
        elif dataset_id == "ds10":
            result = extract_hdf5_grid_file(source_path, output_path)
        elif dataset_id == "ds11":
            result = extract_track_file(source_path, output_path)
        else:
            raise ValueError(f"Unsupported dataset: {dataset_id}")

        status = "extracted" if result is not None else "skipped_empty"
        payload = {
            "dataset": dataset_id,
            "period": record["period"],
            "source": str(source_path),
            "output": str(output_path) if result is not None else None,
            "status": status,
        }
        if manifest:
            append_jsonl(manifest, payload)
        return payload
    except Exception as exc:
        payload = {
            "dataset": record["dataset"],
            "period": record["period"],
            "source": str(source_path),
            "output": str(output_path),
            "status": "error",
            "error": str(exc),
        }
        if errors:
            append_jsonl(errors, payload)
        return payload


def limit_records(records, limit=None):
    if limit is None:
        return records
    return records[:limit]


def add_common_batch_args(parser):
    parser.add_argument("data_root")
    parser.add_argument("--datasets", default="ds1,ds2,ds3,ds4,ds10,ds11")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", default=OUTPUT_DIR)


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Extract Saudi Arabia region data from CMA/MAZU weather datasets."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="List supported source files")
    add_common_batch_args(discover_parser)
    discover_parser.add_argument("--dry-run", action="store_true")

    batch_parser = subparsers.add_parser("batch", help="Extract discovered source files")
    add_common_batch_args(batch_parser)
    batch_parser.add_argument("--dry-run", action="store_true")
    batch_parser.add_argument("--overwrite", action="store_true")
    batch_parser.add_argument("--skip-existing", action="store_true")
    batch_parser.add_argument("--level-type", default="surface")
    batch_parser.add_argument("--manifest")
    batch_parser.add_argument("--errors")

    return parser


def run_discover(args):
    records = discover_files(
        args.data_root,
        datasets=args.datasets,
        start=args.start,
        end=args.end,
        limit=args.limit,
    )
    for record in records:
        print(f"{record['dataset']}\t{record['period']}\t{record['path']}")
    print(f"Discovered {len(records)} file(s)")
    return 0


def run_batch(args):
    output_root = Path(args.output)
    manifest = Path(args.manifest) if args.manifest else output_root / "manifest.jsonl"
    errors = Path(args.errors) if args.errors else output_root / "errors.jsonl"
    records = discover_files(
        args.data_root,
        datasets=args.datasets,
        start=args.start,
        end=args.end,
        limit=args.limit,
    )

    if args.dry_run:
        for record in records:
            print(f"DRY-RUN\t{record['dataset']}\t{record['period']}\t{record['path']}")
        print(f"Would process {len(records)} file(s)")
        return 0

    counts = {}
    for record in records:
        payload = process_record(
            record,
            output_root,
            level_type=args.level_type,
            overwrite=args.overwrite,
            manifest=manifest,
            errors=errors,
        )
        counts[payload["status"]] = counts.get(payload["status"], 0) + 1
        print(f"{payload['status']}\t{record['dataset']}\t{record['path']}")
    print(f"Processed {len(records)} file(s): {counts}")
    return 0


def print_usage():
    print("Usage:")
    print("  python saudi_data_extract.py demo")
    print("  python saudi_data_extract.py discover /Volumes/E/气象数据 --datasets ds1,ds4,ds10,ds11 --limit 3 --dry-run")
    print("  python saudi_data_extract.py batch /Volumes/E/气象数据 --datasets ds11 --start 20251001 --end 20251031")
    print("  python saudi_data_extract.py all E:\\Data\\Datas")
    print("  python saudi_data_extract.py file.grib2 [level_type]")
    print("  python saudi_data_extract.py file.nc")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 1 or argv[0] == "demo":
        demo()
        return 0
    if argv[0] == "all":
        data_root = argv[1] if len(argv) > 1 else r"E:\Data\Datas"
        extract_all(data_root)
        return 0
    if argv[0].endswith((".grib2", ".grb2", ".grb")):
        name = "saudi_" + os.path.basename(argv[0]).replace(".grib2", ".nc")
        level = argv[1] if len(argv) > 1 else "surface"
        extract_grib2(argv[0], name, level_type=level)
        return 0
    if argv[0].endswith(".nc"):
        name = "saudi_" + os.path.basename(argv[0])
        extract_netcdf(argv[0], name)
        return 0
    if argv[0] in {"discover", "batch"}:
        parser = build_arg_parser()
        args = parser.parse_args(argv)
        if args.command == "discover":
            return run_discover(args)
        if args.command == "batch":
            return run_batch(args)
    print_usage()
    return 2


def extract_grib2(grib_file_path, output_name, level_type="surface"):
    """
    Extract Saudi Arabia region from GRIB2 file (DS1, DS2, DS3).
    level_type options: 'surface', 'atmosphere', 'isobaricInhPa', etc.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Opening: {os.path.basename(grib_file_path)}")
    out_file = os.path.join(OUTPUT_DIR, output_name)
    extract_grib2_file(grib_file_path, out_file, level_type=level_type)
    size_mb = os.path.getsize(out_file) / 1024 / 1024
    print(f"  Saved: {out_file} ({size_mb:.1f} MB)")

    return out_file


def extract_netcdf(nc_file_path, output_name):
    """
    Extract Saudi Arabia region from NetCDF file (DS4, DS5).
    Used for SST (Sea Surface Temperature) data.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Opening: {os.path.basename(nc_file_path)}")
    out_file = os.path.join(OUTPUT_DIR, output_name)
    extract_netcdf_file(nc_file_path, out_file)
    size_mb = os.path.getsize(out_file) / 1024 / 1024
    print(f"  Saved: {out_file} ({size_mb:.1f} MB)")

    return out_file


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
    raise SystemExit(main())
