import json
import warnings
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import xarray as xr

from analysis.analyze_saudi_region_output import (
    build_markdown_report,
    collect_analysis,
    normalize_grid,
    numeric_summary,
)


class SaudiDataAnalysisTests(unittest.TestCase):
    def test_numeric_summary_skips_non_numeric_arrays(self):
        self.assertIsNone(numeric_summary(np.asarray(["a", "b"])))

        summary = numeric_summary(np.asarray([[1.0, 2.0], [3.0, np.nan]]))

        self.assertEqual(summary["count"], 3)
        self.assertAlmostEqual(summary["mean"], 2.0)
        self.assertAlmostEqual(summary["max"], 3.0)

    def test_numeric_summary_ignores_large_fill_values(self):
        summary = numeric_summary(np.asarray([300.0, -3.4028235e38, 310.0]))

        self.assertEqual(summary["count"], 2)
        self.assertAlmostEqual(summary["mean"], 305.0)
        self.assertAlmostEqual(summary["min"], 300.0)

    def test_normalize_grid_transposes_lon_lat_arrays(self):
        lat = np.asarray([20.0, 21.0])
        lon = np.asarray([40.0, 41.0, 42.0])
        values = np.arange(6).reshape(3, 2)

        normalized = normalize_grid(values, lat, lon)

        self.assertEqual(normalized.shape, (2, 3))
        self.assertEqual(normalized[0, 1], values[1, 0])

    def test_collect_analysis_reads_partitioned_outputs(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "saudi_region_output"
            self._write_partitioned_inputs(root, "20250101")

            analysis = collect_analysis(root)

        self.assertEqual(analysis["availability"]["ds1_months"], 1)
        self.assertEqual(analysis["availability"]["ds2_days"], 1)
        self.assertEqual(analysis["availability"]["ds10_daily_days"], 1)
        self.assertEqual(analysis["monthly_records"][0]["period"], "202501")
        self.assertAlmostEqual(analysis["monthly_records"][0]["precip_mmday_mean"], 8.64)
        self.assertEqual(analysis["daily_records"][0]["period"], "20250101")
        self.assertAlmostEqual(analysis["daily_records"][0]["t2m_mean_c"], 36.85)
        self.assertAlmostEqual(analysis["daily_records"][0]["tp_mean_mm"], 12.0)
        self.assertAlmostEqual(analysis["daily_records"][0]["ds10_daily_total_mean_mm"], 18.0)
        self.assertEqual(analysis["daily_records"][0]["ds10_source_file_count"], 2)

    def test_collect_analysis_skips_all_nan_monthly_precipitation(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "saudi_region_output"
            month = "202501"
            coords = {"latitude": np.asarray([20.0]), "longitude": np.asarray([40.0])}
            self._write_nc(
                root / "ds1" / month / f"saudi_ds1_ART_SINGLE_GLB_0P10_MONTH_AVG_{month}.nc",
                {"prate": np.asarray([[np.nan]])},
                coords,
            )

            analysis = collect_analysis(root)

        self.assertEqual(analysis["monthly_records"][0]["period"], month)
        self.assertNotIn("precip_mmday_mean", analysis["monthly_records"][0])
        self.assertNotIn("precip_mmday_max", analysis["monthly_records"][0])

    def test_collect_analysis_does_not_warn_on_zero_precipitation_ratio(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "saudi_region_output"
            month = "202501"
            coords = {"latitude": np.asarray([20.0]), "longitude": np.asarray([40.0])}
            self._write_nc(
                root / "ds1" / month / f"saudi_ds1_ART_SINGLE_GLB_0P10_MONTH_AVG_{month}.nc",
                {"prate": np.asarray([[0.0]]), "cpr": np.asarray([[1.0]])},
                coords,
            )

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                analysis = collect_analysis(root)

        runtime_warnings = [warning for warning in caught if issubclass(warning.category, RuntimeWarning)]
        self.assertEqual(runtime_warnings, [])
        self.assertEqual(analysis["monthly_records"][0]["precip_mmday_mean"], 0.0)
        self.assertNotIn("convective_precip_ratio_mean", analysis["monthly_records"][0])

    def test_build_markdown_report_writes_figures_and_summary_json(self):
        analysis = {
            "data_root": "/tmp/saudi_region_output",
            "availability": {"ds1_months": 1, "ds2_days": 1, "ds4_days": 0, "ds10_daily_days": 1},
            "monthly_records": [{"period": "202501", "precip_mmday_mean": 8.64}, {"period": "202502"}],
            "daily_records": [{"period": "20250101", "t2m_mean_c": 36.85, "tp_mean_mm": 12.0}],
            "extremes": {
                "hottest_day": {"period": "20250101", "value": 36.85, "metric": "t2m_mean_c"},
                "wettest_day": {"period": "20250101", "value": 12.0, "metric": "tp_mean_mm"},
            },
        }

        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "analysis"
            report_path = build_markdown_report(
                analysis,
                output_dir,
                figure_paths=[output_dir / "figures" / "daily_timeseries.png"],
            )

            report_text = report_path.read_text(encoding="utf-8")
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))

        self.assertIn("# 沙特区域气象数据洞察分析报告", report_text)
        self.assertIn("figures/daily_timeseries.png", report_text)
        self.assertIn("DS1 月平均降水率共有 1/2 个月存在有效数值", report_text)
        self.assertEqual(summary["availability"]["ds1_months"], 1)

    def _write_partitioned_inputs(self, root, period):
        month = period[:6]
        lat = np.asarray([20.0, 21.0])
        lon = np.asarray([40.0, 41.0])
        coords = {"latitude": lat, "longitude": lon}
        shape = (2, 2)

        self._write_nc(
            root / "ds1" / month / f"saudi_ds1_ART_SINGLE_GLB_0P10_MONTH_AVG_{month}.nc",
            {"prate": np.full(shape, 0.0001), "cpr": np.full(shape, 0.000025)},
            coords,
        )
        self._write_nc(
            root / "ds2" / period / f"saudi_ds2_ART_SINGLE_GLB_0P10_DAY_SFC_{period}.nc",
            {
                "t2m": np.full(shape, 310.0),
                "d2m": np.full(shape, 295.0),
                "r2": np.full(shape, 40.0),
                "u10": np.full(shape, 3.0),
                "v10": np.full(shape, 4.0),
            },
            coords,
        )
        self._write_nc(
            root / "ds2" / period / f"saudi_ds2_ART_SINGLE_GLB_0P10_DAY_ACC_{period}.nc",
            {"tp": np.full(shape, 12.0), "acpcp": np.full(shape, 3.0)},
            coords,
        )

        ds10_dir = root / "ds10_daily" / month
        ds10_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            ds10_dir / f"saudi_ds10_daily_{period}.npz",
            date=np.asarray(period),
            lat=lat,
            lon=lon,
            daily_total=np.full((len(lon), len(lat)), 18.0),
            max_1h=np.full((len(lon), len(lat)), 5.0),
            source_files=np.asarray(["a.h5", "b.h5"]),
        )

    def _write_nc(self, path, variables, coords):
        path.parent.mkdir(parents=True, exist_ok=True)
        dims = tuple(coords)
        data_vars = {
            name: (dims, np.asarray(values, dtype=float))
            for name, values in variables.items()
        }
        xr.Dataset(data_vars, coords=coords).to_netcdf(path)


if __name__ == "__main__":
    unittest.main()
