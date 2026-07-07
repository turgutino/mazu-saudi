import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import xarray as xr

from compute_indicators import (
    add_daily_surface_indicators,
    add_flash_flood_risk,
    add_heatwave_duration_to_outputs,
    add_instability_indicators,
    compute_period,
    load_ds8_daily_normals,
    load_datasets,
)


class ComputeIndicatorsTests(unittest.TestCase):
    def test_load_datasets_reads_partitioned_saudi_outputs(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_partitioned_inputs(root, "20250601")

            datasets = load_datasets(root, "20250601")

        self.assertIn("ds1_avg", datasets)
        self.assertIn("ds1_acc", datasets)
        self.assertIn("ds1_sfc", datasets)
        self.assertIn("ds2_avg", datasets)
        self.assertIn("ds2_sfc", datasets)
        self.assertIn("ds2_anal", datasets)
        self.assertIn("ds2_acc", datasets)
        self.assertIn("ds2_max", datasets)
        self.assertIn("ds2_min", datasets)
        self.assertIn("ds4", datasets)
        self.assertIn("ds10_daily", datasets)

    def test_compute_period_writes_available_excel_indicators(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output = Path(tmp) / "indicators"
            self._write_partitioned_inputs(root, "20250601")

            result = compute_period(root, "20250601", output_dir=output)
            saved = xr.open_dataset(output / "saudi_indicators_20250601.nc")

            try:
                self.assertEqual(result["period"], "20250601")
                self.assertEqual(result["status"], "computed")
                self.assertIn("precip_mmday", saved)
                self.assertIn("monthly_precip_total", saved)
                self.assertIn("monthly_convective_precip", saved)
                self.assertIn("monthly_large_scale_precip", saved)
                self.assertIn("monthly_convective_precip_ratio", saved)
                self.assertIn("convective_precip_ratio", saved)
                self.assertIn("cape", saved)
                self.assertIn("cin", saved)
                self.assertIn("t2m_c", saved)
                self.assertIn("dewpoint_depression_c", saved)
                self.assertIn("vpd_kpa", saved)
                self.assertIn("heat_index_c", saved)
                self.assertIn("wind10_speed", saved)
                self.assertIn("bowen_ratio", saved)
                self.assertIn("net_radiation", saved)
                self.assertIn("sst_celsius", saved)
                self.assertIn("ds10_daily_total", saved)
                self.assertIn("ds10_max_1h", saved)
                self.assertIn("ivt", saved)
                self.assertIn("ivt_u", saved)
                self.assertIn("ivt_v", saved)
                self.assertIn("wind850_speed", saved)
                self.assertIn("moisture_transport850", saved)
                self.assertIn("omega500", saved)
                self.assertIn("geopotential_height500", saved)
                self.assertIn("jet200_speed", saved)
                self.assertIn("wind_shear_850_200", saved)
                self.assertIn("absolute_vorticity850", saved)
                self.assertIn("relative_vorticity850", saved)
                self.assertIn("divergence850", saved)

                self.assertAlmostEqual(float(saved["precip_mmday"].isel(latitude=0, longitude=0)), 8.64)
                self.assertAlmostEqual(float(saved["monthly_precip_total"].isel(latitude=0, longitude=0)), 60.0)
                self.assertAlmostEqual(float(saved["monthly_precip_mmday"].isel(latitude=0, longitude=0)), 2.0)
                self.assertAlmostEqual(float(saved["monthly_convective_precip"].isel(latitude=0, longitude=0)), 15.0)
                self.assertAlmostEqual(float(saved["monthly_large_scale_precip"].isel(latitude=0, longitude=0)), 45.0)
                self.assertAlmostEqual(float(saved["monthly_convective_precip_ratio"].isel(latitude=0, longitude=0)), 0.25)
                self.assertAlmostEqual(float(saved["convective_precip_ratio"].isel(latitude=0, longitude=0)), 0.25)
                self.assertAlmostEqual(float(saved["t2m_c"].isel(latitude=0, longitude=0)), 36.85)
                self.assertAlmostEqual(float(saved["wind10_speed"].isel(latitude=0, longitude=0)), 5.0)
                self.assertAlmostEqual(float(saved["ds10_max_1h"].isel(latitude=0, longitude=0)), 5.0)
                self.assertAlmostEqual(float(saved["ivt"].isel(latitude=0, longitude=0)), 917.74, places=2)
                self.assertAlmostEqual(float(saved["wind850_speed"].isel(latitude=0, longitude=0)), 10.0)
                self.assertAlmostEqual(float(saved["moisture_transport850"].isel(latitude=0, longitude=0)), 0.1)
                self.assertAlmostEqual(float(saved["omega500"].isel(latitude=0, longitude=0)), -0.2)
                self.assertAlmostEqual(float(saved["geopotential_height500"].isel(latitude=0, longitude=0)), 5880.0)
                self.assertAlmostEqual(float(saved["jet200_speed"].isel(latitude=0, longitude=0)), 30.0)
                self.assertAlmostEqual(float(saved["wind_shear_850_200"].isel(latitude=0, longitude=0)), 20.0)
            finally:
                saved.close()

    def test_load_ds8_daily_normals_reads_trailing_comma_station_table(self):
        with TemporaryDirectory() as tmp:
            climate_root = Path(tmp) / "8_SURF_CLI_GLB_1991_2020"
            self._write_ds8_daily_normals(climate_root, "PRE", [(20.0, 40.0, [1.2, 2.4, 3.6])])

            stations = load_ds8_daily_normals(climate_root, "PRE", 2)

        self.assertEqual(len(stations), 1)
        self.assertEqual(stations[0]["id"], "TEST000001")
        self.assertAlmostEqual(stations[0]["lat"], 20.0)
        self.assertAlmostEqual(stations[0]["lon"], 40.0)
        self.assertAlmostEqual(stations[0]["value"], 2.4)
        self.assertEqual(stations[0]["normals_number"], 365)

    def test_compute_period_adds_ds8_climatology_anomaly_and_heatwave_flag(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output = Path(tmp) / "indicators"
            climate_root = Path(tmp) / "8_SURF_CLI_GLB_1991_2020"
            period = "20250601"
            self._write_partitioned_inputs(root, period)
            self._write_ds8_daily_normals(climate_root, "PRE", [(20.0, 40.0, [5.0] * 365)])
            self._write_ds8_daily_normals(climate_root, "TMAX", [(20.0, 40.0, [36.0] * 365)])
            self._write_ds8_daily_normals(climate_root, "TAVG", [(20.0, 40.0, [32.0] * 365)])

            compute_period(root, period, output_dir=output, climatology_root=climate_root)
            saved = xr.open_dataset(output / f"saudi_indicators_{period}.nc")

            try:
                self.assertIn("daily_precip_climatology", saved)
                self.assertIn("daily_precip_anomaly", saved)
                self.assertIn("daily_precip_anomaly_ratio", saved)
                self.assertIn("tmax_climatology_c", saved)
                self.assertIn("tmax_anomaly_c", saved)
                self.assertIn("t2m_climatology_c", saved)
                self.assertIn("t2m_anomaly_c", saved)
                self.assertIn("heatwave_day_flag", saved)
                self.assertAlmostEqual(float(saved["daily_precip_climatology"].isel(latitude=0, longitude=0)), 5.0)
                self.assertAlmostEqual(float(saved["daily_precip_anomaly"].isel(latitude=0, longitude=0)), 7.0)
                self.assertAlmostEqual(float(saved["daily_precip_anomaly_ratio"].isel(latitude=0, longitude=0)), 1.4)
                self.assertAlmostEqual(float(saved["tmax_climatology_c"].isel(latitude=0, longitude=0)), 36.0)
                self.assertAlmostEqual(float(saved["tmax_anomaly_c"].isel(latitude=0, longitude=0)), 5.85)
                self.assertAlmostEqual(float(saved["t2m_anomaly_c"].isel(latitude=0, longitude=0)), 4.85)
                self.assertEqual(int(saved["heatwave_day_flag"].isel(latitude=0, longitude=0)), 1)
                self.assertEqual(saved.attrs["spi_status"].split(":")[0], "not_computed")
                self.assertEqual(saved.attrs["geopotential_height500_anomaly_status"].split(":")[0], "not_computed")
            finally:
                saved.close()

    def test_heatwave_duration_accumulates_consecutive_daily_flags(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "indicators"
            output.mkdir(parents=True)
            coords = {"latitude": np.array([20.0]), "longitude": np.array([40.0])}
            for period, flag in [("20250601", 1), ("20250602", 1), ("20250603", 0)]:
                xr.Dataset(
                    {"heatwave_day_flag": (("latitude", "longitude"), np.array([[flag]], dtype=np.int16))},
                    coords=coords,
                    attrs={"period": period},
                ).to_netcdf(output / f"saudi_indicators_{period}.nc")

            add_heatwave_duration_to_outputs(output, ["20250601", "20250602", "20250603"])

            durations = []
            for period in ["20250601", "20250602", "20250603"]:
                with xr.open_dataset(output / f"saudi_indicators_{period}.nc") as ds:
                    durations.append(int(ds["heatwave_duration_days"].isel(latitude=0, longitude=0)))

        self.assertEqual(durations, [1, 2, 0])

    def test_compute_period_aligns_ds10_daily_grid_and_cross_validates_precipitation(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output = Path(tmp) / "indicators"
            period = "20250601"
            self._write_partitioned_inputs(root, period)

            month = period[:6]
            ds10_dir = root / "ds10_daily" / month
            # Real DS10 daily NPZ files are on a half-grid offset and store
            # arrays as (longitude, latitude), unlike the DS2 NetCDF grid.
            np.savez_compressed(
                ds10_dir / f"saudi_ds10_daily_{period}.npz",
                date=np.asarray(period),
                lat=np.array([20.05, 21.05]),
                lon=np.array([40.05, 41.05]),
                daily_total=np.array([[18.0, 28.0], [38.0, 48.0]]),
                max_30min=np.array([[3.0, 4.0], [5.0, 6.0]]),
                max_1h=np.array([[11.0, 12.0], [13.0, 14.0]]),
                max_3h=np.array([[9.0, 10.0], [11.0, 12.0]]),
                max_6h=np.array([[12.0, 13.0], [14.0, 15.0]]),
                rainy_steps=np.array([[6, 7], [8, 9]], dtype=np.int16),
                time_count=np.asarray(48, dtype=np.int16),
            )

            compute_period(root, period, output_dir=output)
            saved = xr.open_dataset(output / f"saudi_indicators_{period}.nc")

            try:
                self.assertAlmostEqual(float(saved["ds10_daily_total"].isel(latitude=0, longitude=0)), 18.0)
                self.assertAlmostEqual(float(saved["ds10_daily_total"].isel(latitude=1, longitude=1)), 48.0)
                self.assertAlmostEqual(float(saved["ds10_max_1h"].isel(latitude=0, longitude=0)), 11.0)
                self.assertAlmostEqual(float(saved["ds10_ds2_precip_diff"].isel(latitude=0, longitude=0)), 6.0)
                self.assertAlmostEqual(float(saved["ds10_ds2_precip_ratio"].isel(latitude=0, longitude=0)), 1.5)
                self.assertEqual(int(saved["ds10_ds2_heavy_rain_overlap"].isel(latitude=0, longitude=0)), 1)
                self.assertEqual(int(np.isfinite(saved["ds10_daily_total"].values).sum()), 4)
            finally:
                saved.close()

    def test_flash_flood_risk_ignores_non_horizontal_terms(self):
        lat = np.array([20.0, 21.0])
        lon = np.array([40.0, 41.0])
        levels = np.array([1.0, 2.0])
        results = xr.Dataset(
            {
                "daily_precip_total": (("latitude", "longitude"), np.full((2, 2), 12.0)),
                "ds10_max_1h": (("latitude", "longitude"), np.full((2, 2), 11.0)),
                "convective_precip_ratio": (
                    ("latitude", "longitude", "pressureFromGroundLayer"),
                    np.ones((2, 2, 2)),
                ),
            },
            coords={"latitude": lat, "longitude": lon, "pressureFromGroundLayer": levels},
        )

        add_flash_flood_risk(results)

        self.assertEqual(results["flash_flood_risk"].dims, ("latitude", "longitude"))
        self.assertEqual(int(results["flash_flood_risk"].isel(latitude=0, longitude=0)), 2)

    def test_daily_surface_indicators_mask_fill_values_before_derived_metrics(self):
        lat = np.array([20.0, 21.0])
        lon = np.array([40.0, 41.0])
        coords = {"latitude": lat, "longitude": lon}
        sfc = xr.Dataset(
            {
                "t2m": (("latitude", "longitude"), np.array([[9.999e20, 310.0], [305.0, 300.0]])),
                "d2m": (("latitude", "longitude"), np.full((2, 2), 295.0)),
                "r2": (("latitude", "longitude"), np.full((2, 2), 40.0)),
                "aptmp": (("latitude", "longitude"), np.array([[9.999e20, 312.0], [306.0, 301.0]])),
            },
            coords=coords,
        )
        results = xr.Dataset()

        add_daily_surface_indicators(results, sfc, None, None)

        self.assertTrue(np.isnan(results["t2m_c"].isel(latitude=0, longitude=0)))
        self.assertTrue(np.isnan(results["vpd_kpa"].isel(latitude=0, longitude=0)))
        self.assertTrue(np.isnan(results["heat_index_c"].isel(latitude=0, longitude=0)))
        self.assertTrue(np.isnan(results["apparent_temp_c"].isel(latitude=0, longitude=0)))
        self.assertAlmostEqual(float(results["t2m_c"].isel(latitude=0, longitude=1)), 36.85)

    def test_instability_indicators_reduce_cape_to_horizontal_grid_for_risk(self):
        lat = np.array([20.0, 21.0])
        lon = np.array([40.0, 41.0])
        layers = np.array([0.0, 180.0])
        ds = xr.Dataset(
            {
                "cape": (
                    ("pressureFromGroundLayer", "latitude", "longitude"),
                    np.array(
                        [
                            [[900.0, 800.0], [700.0, 600.0]],
                            [[1200.0, 500.0], [1100.0, 400.0]],
                        ]
                    ),
                )
            },
            coords={"pressureFromGroundLayer": layers, "latitude": lat, "longitude": lon},
        )
        results = xr.Dataset(
            {
                "daily_precip_total": (("latitude", "longitude"), np.full((2, 2), 12.0)),
            },
            coords={"latitude": lat, "longitude": lon},
        )

        add_instability_indicators(results, ds)
        add_flash_flood_risk(results)

        self.assertEqual(results["cape"].dims, ("latitude", "longitude"))
        self.assertEqual(float(results["cape"].isel(latitude=0, longitude=0)), 1200.0)
        self.assertEqual(int(results["flash_flood_risk"].isel(latitude=0, longitude=0)), 2)
        self.assertEqual(int(results["flash_flood_risk"].isel(latitude=0, longitude=1)), 1)

    def _write_partitioned_inputs(self, root, period):
        month = period[:6]
        lat = np.array([20.0, 21.0])
        lon = np.array([40.0, 41.0])
        coords = {"latitude": lat, "longitude": lon}
        shape = (2, 2)

        ds1_dir = root / "ds1" / month
        self._write_nc(
            ds1_dir / f"saudi_ds1_ART_SINGLE_GLB_0P10_MONTH_AVG_{month}.nc",
            {
                "prate": np.full(shape, np.nan),
                "cpr": np.full(shape, np.nan),
                "avg_slhtf": np.full(shape, 50.0),
                "avg_ishf": np.full(shape, 150.0),
                "avg_utaua": np.full(shape, 0.08),
                "avg_vtaua": np.full(shape, 0.06),
                "iegwss": np.full(shape, 0.03),
                "ingwss": np.full(shape, 0.04),
                "sdswrf": np.full(shape, 500.0),
                "sdlwrf": np.full(shape, 330.0),
                "suswrf": np.full(shape, 100.0),
                "sulwrf": np.full(shape, 450.0),
                "duvb": np.full(shape, 8.0),
                "cduvb": np.full(shape, 10.0),
                "avg_al": np.full(shape, 30.0),
            },
            coords,
        )
        self._write_nc(
            ds1_dir / f"saudi_ds1_ART_SINGLE_GLB_0P10_MONTH_ACC_{month}.nc",
            {"tp": np.full(shape, 60.0), "acpcp": np.full(shape, 15.0), "ncpcp": np.full(shape, 45.0)},
            coords,
        )
        self._write_nc(
            ds1_dir / f"saudi_ds1_ART_SINGLE_GLB_0P10_MONTH_SFC_{month}.nc",
            {
                "tcc": np.full(shape, 20.0),
                "tcc_highCloudLayer_0_0": np.full(shape, 5.0),
                "tcc_middleCloudLayer_0_0": np.full(shape, 7.0),
                "tcc_lowCloudLayer_0_0": np.full(shape, 9.0),
            },
            coords,
        )

        ds2_dir = root / "ds2" / period
        self._write_nc(
            ds2_dir / f"saudi_ds2_ART_SINGLE_GLB_0P10_DAY_AVG_{period}.nc",
            {
                "prate": np.full(shape, 0.0001),
                "cpr": np.full(shape, 0.000025),
                "avg_slhtf": np.full(shape, 50.0),
                "avg_ishf": np.full(shape, 150.0),
                "sdswrf": np.full(shape, 500.0),
                "sdlwrf": np.full(shape, 330.0),
                "suswrf": np.full(shape, 100.0),
                "sulwrf": np.full(shape, 450.0),
                "avg_al": np.full(shape, 30.0),
            },
            coords,
        )
        self._write_nc(
            ds2_dir / f"saudi_ds2_ART_SINGLE_GLB_0P10_DAY_SFC_{period}.nc",
            {
                "t2m": np.full(shape, 310.0),
                "d2m": np.full(shape, 295.0),
                "r2": np.full(shape, 40.0),
                "sh2": np.full(shape, 0.012),
                "aptmp": np.full(shape, 312.0),
                "u10": np.full(shape, 3.0),
                "v10": np.full(shape, 4.0),
                "tcc": np.full(shape, 20.0),
                "tcc_highCloudLayer_0_0": np.full(shape, 5.0),
                "tcc_middleCloudLayer_0_0": np.full(shape, 7.0),
                "tcc_lowCloudLayer_0_0": np.full(shape, 9.0),
            },
            coords,
        )
        self._write_nc(
            ds2_dir / f"saudi_ds2_ART_SINGLE_GLB_0P10_DAY_ACC_{period}.nc",
            {"tp": np.full(shape, 12.0), "acpcp": np.full(shape, 3.0), "ncpcp": np.full(shape, 9.0)},
            coords,
        )
        self._write_nc(
            ds2_dir / f"saudi_ds2_ART_SINGLE_GLB_0P10_DAY_MAX_{period}.nc",
            {"tmax": np.full(shape, 315.0), "qmax": np.full(shape, 0.016)},
            coords,
        )
        self._write_nc(
            ds2_dir / f"saudi_ds2_ART_SINGLE_GLB_0P10_DAY_MIN_{period}.nc",
            {"tmin": np.full(shape, 300.0), "qmin": np.full(shape, 0.008)},
            coords,
        )
        self._write_analysis_nc(ds2_dir / f"saudi_ds2_ART_ATM_GLB_0P10_DAY_ANAL_{period}.nc", coords)

        ds4_dir = root / "ds4" / period
        self._write_nc(
            ds4_dir / f"saudi_ds4_Z_OCEN_C_BABJ_{period}000000_P_CODAS_GLB_0P10_6HOR_SST.nc",
            {"analysed_sst": np.full(shape, 303.15)},
            {"lat": lat, "lon": lon},
        )

        ds10_dir = root / "ds10_daily" / month
        ds10_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            ds10_dir / f"saudi_ds10_daily_{period}.npz",
            date=np.asarray(period),
            lat=lat,
            lon=lon,
            daily_total=np.full(shape, 18.0),
            max_30min=np.full(shape, 3.0),
            max_1h=np.full(shape, 5.0),
            max_3h=np.full(shape, 9.0),
            max_6h=np.full(shape, 12.0),
            rainy_steps=np.full(shape, 6, dtype=np.int16),
            time_count=np.asarray(48, dtype=np.int16),
        )

    def _write_ds8_daily_normals(self, root, variable, stations):
        day_columns = [f"{day:03d}d" for day in range(1, 366)]
        path = root / variable / "GLB" / "MDAY" / f"SURF_GLB_MUL_MMUT_19912020_MDAY_{variable}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = ["id,wmo_id,lat,lon,alt,normals_number," + ",".join(day_columns) + ","]
        for index, (lat, lon, values) in enumerate(stations, start=1):
            padded = list(values) + [values[-1]] * (365 - len(values))
            value_text = ",".join(f"{value:.1f}" for value in padded[:365])
            rows.append(f"TEST{index:06d},{index:05d},{lat:.3f},{lon:.3f},10.0,365,{value_text},")
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    def _write_nc(self, path, variables, coords):
        path.parent.mkdir(parents=True, exist_ok=True)
        dims = tuple(coords)
        data_vars = {
            name: (dims, np.asarray(values, dtype=float))
            for name, values in variables.items()
        }
        xr.Dataset(data_vars, coords=coords).to_netcdf(path)

    def _write_analysis_nc(self, path, coords):
        path.parent.mkdir(parents=True, exist_ok=True)
        shape = (len(coords["latitude"]), len(coords["longitude"]))
        levels = np.array([1000.0, 850.0, 500.0, 300.0, 200.0])
        level_shape = (len(levels), *shape)
        level_coords = {"isobaricInhPa": levels, **coords}
        q = np.full(level_shape, 0.01)
        u = np.full(level_shape, 10.0)
        v = np.zeros(level_shape)
        u[-1, :, :] = 30.0
        w = np.zeros(level_shape)
        w[2, :, :] = -0.2
        gh = np.zeros(level_shape)
        gh[2, :, :] = 5880.0
        absv = np.full(level_shape, 1.0e-4)

        data_vars = {
            "cape": (("latitude", "longitude"), np.full(shape, 1200.0)),
            "cin": (("latitude", "longitude"), np.full(shape, -25.0)),
            "sp": (("latitude", "longitude"), np.full(shape, 98000.0)),
            "orog": (("latitude", "longitude"), np.full(shape, 250.0)),
            "lftx": (("latitude", "longitude"), np.full(shape, -3.0)),
            "lftx4": (("latitude", "longitude"), np.full(shape, -4.0)),
            "pwat": (("latitude", "longitude"), np.full(shape, 42.0)),
            "q_isobaricInhPa": (("isobaricInhPa", "latitude", "longitude"), q),
            "u_isobaricInhPa": (("isobaricInhPa", "latitude", "longitude"), u),
            "v_isobaricInhPa": (("isobaricInhPa", "latitude", "longitude"), v),
            "w": (("isobaricInhPa", "latitude", "longitude"), w),
            "gh_isobaricInhPa": (("isobaricInhPa", "latitude", "longitude"), gh),
            "absv": (("isobaricInhPa", "latitude", "longitude"), absv),
        }
        xr.Dataset(data_vars, coords=level_coords).to_netcdf(path)


if __name__ == "__main__":
    unittest.main()
