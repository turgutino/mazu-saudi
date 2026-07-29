from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
import xarray as xr

from mazu_saudi.knowledge_graph.global_indicators import (
    ALL_OUTPUT_VARIABLES,
    DailySource,
    GlobalIndicatorConfig,
    SaudiExclusion,
    TileGrid,
    audit_sources,
    derive_surface_indicators,
    discover_daily_sources,
    integrate_ivt,
    output_is_complete,
    read_satellite_precip_tiles,
    read_sst_tiles,
    write_daily_indicators,
)


def test_tile_aggregation_excludes_saudi_cells_before_computing_mean():
    grid = TileGrid.from_points(
        np.array([25.0, 25.0, 25.0]),
        np.array([45.0, 47.0, 55.0]),
        tile_degrees=10.0,
        exclusion=SaudiExclusion(lon_min=44.0, lon_max=48.0),
    )

    means, counts = grid.aggregate(np.array([100.0, 200.0, 10.0]))

    # The first two cells are inside the exclusion region. Only 55E contributes.
    tile_lat = int((25.0 + 90.0) // 10.0)
    tile_lon = int((55.0 + 180.0) // 10.0)
    assert means[tile_lat, tile_lon] == 10.0
    assert counts.sum() == 1


def test_ivt_uses_pressure_weighted_vector_integration():
    levels = (1000, 850, 700)
    q = {level: np.array([0.01, 0.02]) for level in levels}
    u = {level: np.array([10.0, 0.0]) for level in levels}
    v = {level: np.array([0.0, 5.0]) for level in levels}

    result = integrate_ivt(q, u, v, levels)

    np.testing.assert_allclose(
        result,
        np.array([0.01 * 10.0 * 30_000.0 / 9.80665, 0.02 * 5.0 * 30_000.0 / 9.80665]),
        rtol=1e-6,
    )


def test_surface_indicators_compute_wind_and_vpd():
    result = derive_surface_indicators(
        {
            "t2m": np.array([303.15]),
            "rh2m": np.array([50.0]),
            "u10": np.array([3.0]),
            "v10": np.array([4.0]),
        }
    )

    assert result["wind10_speed"][0] == 5.0
    assert 2.0 < result["vpd_kpa"][0] < 2.2


def test_source_audit_reports_known_product_gaps_without_inventing_files(tmp_path):
    config = GlobalIndicatorConfig(year=2025, max_days_with_missing_sources=5)
    day_root = tmp_path / "2_NAFP_ART_SFC_GLB_DAY_PROD" / "20250101"
    day_root.mkdir(parents=True)
    for template in (
        "ART_ATM_GLB_0P10_DAY_ANAL_20250101.grib2",
        "ART_SINGLE_GLB_0P10_DAY_ACC_20250101.grib2",
        "ART_SINGLE_GLB_0P10_DAY_MAX_20250101.grib2",
        "ART_SINGLE_GLB_0P10_DAY_SFC_20250101.grib2",
    ):
        (day_root / template).touch()
    sources = discover_daily_sources(tmp_path, config)

    audit = audit_sources(
        sources[:2],
        replace(config, max_days_with_missing_sources=1),
    )

    assert audit.day_count == 2
    assert audit.complete_day_count == 1
    assert audit.missing_source_days["20250102"] == (
        "analysis",
        "accumulation",
        "maximum",
        "surface",
    )
    assert audit.source_coverage_days == {
        "ds1_monthly_background": 0,
        "ds2_daily_atmosphere": 1,
        "ds4_sea_surface_temperature": 0,
        "ds10_satellite_precipitation": 0,
    }


def test_sst_and_satellite_precipitation_are_aggregated_as_independent_sources(tmp_path):
    config = GlobalIndicatorConfig(tile_degrees=10.0)
    sst_paths = []
    for index, kelvin in enumerate((300.0, 302.0)):
        path = tmp_path / f"sst-{index}.nc"
        xr.Dataset(
            {
                "analysed_sst": (
                    ("lat", "lon"),
                    np.full((2, 2), kelvin, dtype=np.float32),
                )
            },
            coords={"lat": [-5.0, 5.0], "lon": [-5.0, 5.0]},
        ).to_netcdf(path)
        sst_paths.append(path)

    import h5py

    satellite_paths = []
    for index in range(2):
        path = tmp_path / f"satellite-{index}.h5"
        with h5py.File(path, "w") as handle:
            handle.create_dataset("lat", data=np.array([[-5.0, 5.0]]))
            handle.create_dataset("lon", data=np.array([[-5.0, 5.0]]))
            # Real FYMERG arrays are longitude × latitude.
            handle.create_dataset(
                "Pre_cal",
                data=np.full((1, 2, 2), 2.0, dtype=np.float32),
            )
        satellite_paths.append(path)

    sst, _ = read_sst_tiles(tuple(sst_paths), config)
    satellite, _ = read_satellite_precip_tiles(tuple(satellite_paths), config)

    assert np.isclose(float(np.nanmean(sst)), 27.85, atol=1e-4)
    # Two half-hour frames at 2 mm/h produce 2 mm, not 4 mm.
    assert np.isclose(float(np.nanmean(satellite["satellite_precip_total"])), 2.0)
    assert np.isclose(
        float(np.nanmean(satellite["satellite_precip_coverage"])),
        2.0 / 48.0,
    )


def test_daily_output_is_atomic_resumable_and_records_missing_products(tmp_path):
    config = GlobalIndicatorConfig(tile_degrees=10.0)
    analysis = tmp_path / "analysis.grib2"
    maximum = tmp_path / "max.grib2"
    surface = tmp_path / "surface.grib2"
    for path in (analysis, maximum, surface):
        path.touch()
    source = DailySource(
        day="20250820",
        files={
            "analysis": analysis,
            "accumulation": None,
            "maximum": maximum,
            "surface": surface,
        },
    )
    grid = TileGrid.regular(config)
    values = {
        name: np.full(grid.shape, float(index), dtype=np.float32)
        for index, name in enumerate(ALL_OUTPUT_VARIABLES, start=1)
    }
    counts = {
        name: np.ones(grid.shape, dtype=np.int32)
        for name in ALL_OUTPUT_VARIABLES
    }

    with patch(
        "mazu_saudi.knowledge_graph.global_indicators.read_daily_raw_indicators",
        return_value=(values, counts, grid),
    ) as reader:
        first = write_daily_indicators(source, tmp_path, config)
        second = write_daily_indicators(source, tmp_path, config)

    assert first["status"] == "computed"
    assert second["status"] == "skipped_existing"
    assert reader.call_count == 1
    path = Path(first["output"])
    assert output_is_complete(path, config, source)
    assert not output_is_complete(
        path,
        replace(config, ivt_levels_hpa=(1000, 850, 500)),
    )
    accumulation = tmp_path / "accumulation.grib2"
    accumulation.touch()
    changed_source = replace(
        source,
        files={**source.files, "accumulation": accumulation},
    )
    assert not output_is_complete(path, config, changed_source)
    assert not path.with_name(f".{path.name}.tmp").exists()
    with xr.open_dataset(path) as dataset:
        assert dataset.attrs["pipeline_version"] == "3"
        assert dataset.attrs["indicator_formula_version"] == "1.0.0"
        assert dataset.attrs["missing_source_products"] == "accumulation"
        assert dataset.attrs["saudi_cells_excluded_before_aggregation"] == "true"
        assert set(ALL_OUTPUT_VARIABLES).issubset(dataset.data_vars)
