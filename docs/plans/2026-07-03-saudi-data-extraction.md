# Saudi Data Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a robust batch extraction script for Saudi Arabia region data from datasets DS1-DS4, DS10, and DS11 under `/Volumes/E/气象数据`.

**Architecture:** Refactor the current single-file prototype into reusable dataset adapters. Raster/grid products use coordinate-aware clipping; text track products use row-level latitude/longitude filtering. File discovery, output naming, skip/resume behavior, dry-run, and manifest logging are shared across datasets.

**Tech Stack:** Python 3.10+, `argparse`, `pathlib`, `csv`, `json`, `logging`, `xarray`, `cfgrib`, `netCDF4`, `h5py`, `numpy`, `pytest`.

---

## Data Findings To Preserve

- Saudi bbox: latitude `16.0..32.0`, longitude `34.0..56.0`.
- DS1: `1_NAFP_ART_ATM_GLB_MONTH_PROD/YYYYMM/*.grib2`.
- DS2: `2_NAFP_ART_SFC_GLB_DAY_PROD/YYYYMMDD/*.grib2`.
- DS3: `3_NAFP_ART_SFC_GLB_MONTH_PROD/YYYYMM/*.grib2`.
- DS4: `4_OCEA_FUS_DAY_PRO/YYYYMMDD/*.nc`, HDF5-backed NetCDF.
- DS10: `10_SATE_PRECIPITATION_PRODUCT_2025/YYYYMM/*.h5`, files like `FYMERG_S_202509302330_E202509302359.h5`.
- DS11: `11_TCGD_MON_GLB_PROD/YYYYMMDD/t??z.YYYYMMDD/track_*.txt`; also has `2025/...` duplicate/aggregate layout and PNG maps.
- All discovery must skip AppleDouble paths whose basename starts with `._`.

## Recommended File Layout

```text
saudi_data_extract.py
tests/
|-- test_saudi_data_extract.py
docs/plans/2026-07-03-saudi-data-extraction.md
```

Keep the implementation in `saudi_data_extract.py` for now. The repository is small, so a package split would be unnecessary until the script grows further.

## Task 1: Extract Configuration And Path Utilities

**Files:**
- Modify: `saudi_data_extract.py`
- Create: `tests/test_saudi_data_extract.py`

**Step 1: Write failing tests**

Test expected behavior:

```python
from pathlib import Path

from saudi_data_extract import (
    SAUDI_BBOX,
    is_metadata_path,
    safe_output_name,
    infer_dataset_id,
)


def test_is_metadata_path_skips_appledouble():
    assert is_metadata_path(Path("._file.nc"))
    assert is_metadata_path(Path("/data/._202501"))
    assert not is_metadata_path(Path("/data/202501/file.nc"))


def test_safe_output_name_keeps_dataset_and_stem():
    path = Path("/root/10_SATE_PRECIPITATION_PRODUCT_2025/202509/FYMERG_S_202509010000_E202509010029.h5")
    assert safe_output_name("ds10", path).endswith("saudi_ds10_FYMERG_S_202509010000_E202509010029.nc")


def test_infer_dataset_id_from_top_level_dir():
    assert infer_dataset_id(Path("/x/1_NAFP_ART_ATM_GLB_MONTH_PROD/202506/a.grib2")) == "ds1"
    assert infer_dataset_id(Path("/x/11_TCGD_MON_GLB_PROD/20251001/t00z.20251001/track_1_0.txt")) == "ds11"
```

**Step 2: Verify failure**

Run:

```bash
pytest tests/test_saudi_data_extract.py -q
```

Expected: fails because functions do not exist.

**Step 3: Implement utilities**

Add:

- `SAUDI_BBOX = {"lat_min": 16.0, "lat_max": 32.0, "lon_min": 34.0, "lon_max": 56.0}`
- `is_metadata_path(path)`
- `infer_dataset_id(path)`
- `safe_output_name(dataset_id, source_path, suffix=".nc")`
- `ensure_output_dir(path)`

**Step 4: Verify pass**

Run:

```bash
pytest tests/test_saudi_data_extract.py -q
```

**Step 5: Commit**

```bash
git add saudi_data_extract.py tests/test_saudi_data_extract.py
git commit -m "Add extraction path utilities"
```

## Task 2: Add Dataset Discovery

**Files:**
- Modify: `saudi_data_extract.py`
- Modify: `tests/test_saudi_data_extract.py`

**Step 1: Write failing tests**

Use `tmp_path` to build synthetic directories for DS1, DS2, DS3, DS4, DS10, DS11. Include `._*` files and assert they are skipped.

Expected discovery patterns:

- DS1/DS3: `YYYYMM/*.grib2`
- DS2/DS4: `YYYYMMDD/*.grib2` or `*.nc`
- DS10: `YYYYMM/*.h5`
- DS11: `YYYYMMDD/t??z.YYYYMMDD/track_*.txt`

Expose function:

```python
discover_files(data_root, datasets=None, start=None, end=None)
```

Return records with:

```python
{
    "dataset": "ds10",
    "path": Path(...),
    "period": "202509",
}
```

**Step 2: Verify failure**

```bash
pytest tests/test_saudi_data_extract.py::test_discover_files -q
```

**Step 3: Implement discovery**

Use `pathlib.Path.iterdir()` instead of broad recursive `find` behavior. This keeps IO bounded and gives better control over DS-specific depth.

**Step 4: Verify pass**

```bash
pytest tests/test_saudi_data_extract.py -q
```

**Step 5: Commit**

```bash
git add saudi_data_extract.py tests/test_saudi_data_extract.py
git commit -m "Discover supported weather data files"
```

## Task 3: Refactor Grid Extraction For DS1-DS4

**Files:**
- Modify: `saudi_data_extract.py`
- Modify: `tests/test_saudi_data_extract.py`

**Step 1: Write tests for coordinate clipping**

Create small in-memory `xarray.Dataset` objects with ascending and descending latitude, then assert `clip_xarray_to_bbox(ds)` returns only Saudi bbox coordinates.

**Step 2: Implement shared clipping**

Add:

```python
detect_lat_lon_names(ds)
clip_xarray_to_bbox(ds, bbox=SAUDI_BBOX)
extract_grib2_file(path, output_path, level_type=None)
extract_netcdf_file(path, output_path)
```

Keep the old `extract_grib2()` and `extract_netcdf()` as compatibility wrappers, or update README examples after implementation.

**Step 3: Handle GRIB level filtering**

For GRIB2:

- Try no `filter_by_keys` first for simple files.
- If cfgrib raises multiple-field errors, retry known `typeOfLevel` options such as `surface`, `heightAboveGround`, `isobaricInhPa`.
- Write one output file per successfully opened group if needed.

**Step 4: Verify**

```bash
pytest tests/test_saudi_data_extract.py -q
python saudi_data_extract.py demo
```

**Step 5: Commit**

```bash
git add saudi_data_extract.py tests/test_saudi_data_extract.py
git commit -m "Refactor grid clipping for Saudi region"
```

## Task 4: Add DS10 HDF5 Extraction

**Files:**
- Modify: `saudi_data_extract.py`
- Modify: `tests/test_saudi_data_extract.py`

**Step 1: Write HDF5 tests**

Use `h5py` to create a tiny synthetic HDF5 file with:

- latitude coordinate dataset
- longitude coordinate dataset
- precipitation data array

Test that `extract_hdf5_grid_file()` writes only the Saudi subset.

**Step 2: Implement HDF5 metadata discovery**

Add:

```python
find_hdf5_lat_lon_datasets(h5)
extract_hdf5_grid_file(path, output_path)
```

Support common coordinate names:

- latitude: `lat`, `latitude`, `Lat`, `Latitude`, `LAT`
- longitude: `lon`, `longitude`, `Lon`, `Longitude`, `LON`

If FYMERG uses 2D coordinates or implicit global grid, detect shape and allow a config fallback. If coordinates cannot be found, record the failure in manifest and continue.

**Step 3: Output format**

Prefer NetCDF output using `xarray.Dataset.to_netcdf()` after reading the selected HDF5 subset. If the source structure is not mappable, write a compact `.npz` plus JSON metadata as fallback.

**Step 4: Verify**

```bash
pytest tests/test_saudi_data_extract.py -q
```

**Step 5: Commit**

```bash
git add saudi_data_extract.py tests/test_saudi_data_extract.py
git commit -m "Add HDF5 extraction for satellite precipitation"
```

## Task 5: Add DS11 Text Track Extraction

**Files:**
- Modify: `saudi_data_extract.py`
- Modify: `tests/test_saudi_data_extract.py`

**Step 1: Write text parsing tests**

Use sample-style content:

```text
Ini\tFcst\tLat\tLon\tVmax\tPmin
2025100100\t60\t45.1\t100.2\t10.5\t1011.9
2025100100\t63\t24.5\t45.8\t11.0\t1013.3
```

Assert only the Saudi row is retained.

**Step 2: Implement parser**

Add:

```python
extract_track_file(path, output_path, bbox=SAUDI_BBOX)
track_intersects_bbox(rows, bbox)
```

Behavior:

- Read tab/whitespace-delimited text.
- Require columns `Lat` and `Lon`.
- Write filtered rows to `.csv` or `.tsv`.
- If no point intersects Saudi bbox, skip output unless `--keep-empty` is set.

**Step 3: Preserve provenance**

For each kept track, include source path, init time, forecast hour, and original filename in a manifest JSONL.

**Step 4: Verify**

```bash
pytest tests/test_saudi_data_extract.py -q
```

**Step 5: Commit**

```bash
git add saudi_data_extract.py tests/test_saudi_data_extract.py
git commit -m "Extract Saudi-intersecting tropical cyclone tracks"
```

## Task 6: Add Batch CLI, Manifest, And Resume

**Files:**
- Modify: `saudi_data_extract.py`
- Modify: `README.md`
- Modify: `tests/test_saudi_data_extract.py`

**Step 1: Design CLI**

Recommended commands:

```bash
python saudi_data_extract.py discover /Volumes/E/气象数据 --datasets ds1,ds2,ds3,ds4,ds10,ds11
python saudi_data_extract.py batch /Volumes/E/气象数据 --datasets ds1,ds2,ds3,ds4 --start 202501 --end 202512 --output output_saudi
python saudi_data_extract.py batch /Volumes/E/气象数据 --datasets ds10 --start 202501 --end 202509 --output output_saudi
python saudi_data_extract.py batch /Volumes/E/气象数据 --datasets ds11 --start 20251001 --end 20251031 --output output_saudi
```

Options:

- `--dry-run`
- `--overwrite`
- `--skip-existing`
- `--limit N`
- `--level-type surface`
- `--manifest output_saudi/manifest.jsonl`
- `--errors output_saudi/errors.jsonl`

**Step 2: Write CLI tests**

Use `subprocess.run()` on synthetic directories. Assert dry-run prints discovered files without writing outputs.

**Step 3: Implement CLI**

Use `argparse` subcommands. Keep backward-compatible behavior for:

```bash
python saudi_data_extract.py demo
python saudi_data_extract.py file.grib2
python saudi_data_extract.py file.nc
```

**Step 4: Verify**

```bash
pytest tests/test_saudi_data_extract.py -q
python saudi_data_extract.py discover /Volumes/E/气象数据 --datasets ds1,ds4,ds10,ds11 --limit 2 --dry-run
```

The second command should only inspect paths and must not write output files.

**Step 5: Commit**

```bash
git add saudi_data_extract.py README.md tests/test_saudi_data_extract.py
git commit -m "Add batch extraction CLI"
```

## Task 7: Real Data Smoke Tests

**Files:**
- Modify: `progress.md` or a dedicated run log if desired

**Step 1: Run dry-run on real data**

```bash
python saudi_data_extract.py discover /Volumes/E/气象数据 --datasets ds1,ds2,ds3,ds4,ds10,ds11 --limit 3 --dry-run
```

**Step 2: Run one-file extraction per dataset**

Use `--limit 1` for each dataset and write to a temporary output directory:

```bash
python saudi_data_extract.py batch /Volumes/E/气象数据 --datasets ds11 --start 20251001 --end 20251001 --limit 1 --output output_saudi_smoke
```

For DS1-DS4/DS10, only run after dependencies are installed.

**Step 3: Check outputs**

Confirm:

- output file exists when the source intersects Saudi bbox
- manifest row exists
- skipped files are logged clearly
- no `._*` files are processed

**Step 4: Commit run-log/doc updates if any**

```bash
git add README.md
git commit -m "Document Saudi extraction smoke tests"
```

## Implementation Notes

- Do not scan the whole 2T tree recursively. Use per-dataset known directory depths.
- Do not write extracted data into git. Add `output_saudi*/` to `.gitignore` if not already ignored.
- DS11 should filter rows, not copy every global track file.
- DS10 may need one extra metadata probe after `h5py` is installed to identify actual FYMERG coordinate dataset names.
- Keep failures non-fatal in batch mode: log, continue, summarize at the end.
