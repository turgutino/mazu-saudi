import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import xarray as xr

from compute_indicators import compute_period, load_datasets


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
