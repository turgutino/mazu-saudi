# MAZU Saudi Arabia — CMA Data Extraction

Extract Saudi Arabia region (16-32°N, 34-56°E) from CMA global meteorological datasets.

## Requirements

```bash
pip install xarray cfgrib netCDF4 numpy
```

## Supported Datasets

| Dataset | Format | Description |
|---------|--------|-------------|
| DS1 | GRIB2 | Monthly atmospheric data |
| DS2 | GRIB2 | Daily surface data |
| DS3 | GRIB2 | Monthly surface data |
| DS4 | NetCDF | Sea surface temperature (SST) |

## Usage

### Extract all datasets at once

```bash
python saudi_data_extract.py all E:\Data\Datas
```

### Extract a single GRIB2 file

```bash
python saudi_data_extract.py yourfile.grib2
```

### Extract a single NetCDF file

```bash
python saudi_data_extract.py yourfile.nc
```

### Run demo (generates synthetic test data)

```bash
python saudi_data_extract.py demo
```

## Output

All extracted files are saved to `output_saudi/` folder:

```
output_saudi/
    saudi_ds1_surface_avg_202506.nc
    saudi_ds2_surface_avg_20250601.nc
    saudi_ds3_surface_avg_202506.nc
    saudi_sst_20250601_0000.nc
```

Original 4GB global data is reduced to ~15MB for the Saudi Arabia region.

## Load extracted data in Python

```python
import xarray as xr

ds = xr.open_dataset("output_saudi/saudi_ds1_surface_avg_202506.nc")
print(ds)
print(ds["prate"])  # precipitation rate
```

## Region

- Latitude: 16N to 32N
- Longitude: 34E to 56E
- Grid resolution: 0.1 degrees (~10 km)
