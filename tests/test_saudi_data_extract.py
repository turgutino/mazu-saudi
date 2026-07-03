import unittest
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import h5py
import numpy as np

from saudi_data_extract import (
    SAUDI_BBOX,
    clip_xarray_to_bbox,
    discover_files,
    detect_lat_lon_names,
    extract_hdf5_grid_file,
    extract_track_file,
    find_hdf5_lat_lon_datasets,
    infer_dataset_id,
    is_metadata_path,
    safe_output_name,
    track_intersects_bbox,
)


class PathUtilityTests(unittest.TestCase):
    def test_saudi_bbox_matches_project_region(self):
        self.assertEqual(SAUDI_BBOX["lat_min"], 16.0)
        self.assertEqual(SAUDI_BBOX["lat_max"], 32.0)
        self.assertEqual(SAUDI_BBOX["lon_min"], 34.0)
        self.assertEqual(SAUDI_BBOX["lon_max"], 56.0)

    def test_is_metadata_path_skips_appledouble(self):
        self.assertTrue(is_metadata_path(Path("._file.nc")))
        self.assertTrue(is_metadata_path(Path("/data/._202501")))
        self.assertFalse(is_metadata_path(Path("/data/202501/file.nc")))

    def test_safe_output_name_keeps_dataset_and_stem(self):
        path = Path(
            "/root/10_SATE_PRECIPITATION_PRODUCT_2025/202509/"
            "FYMERG_S_202509010000_E202509010029.h5"
        )
        self.assertEqual(
            safe_output_name("ds10", path),
            "saudi_ds10_FYMERG_S_202509010000_E202509010029.nc",
        )

    def test_infer_dataset_id_from_top_level_dir(self):
        self.assertEqual(
            infer_dataset_id(Path("/x/1_NAFP_ART_ATM_GLB_MONTH_PROD/202506/a.grib2")),
            "ds1",
        )
        self.assertEqual(
            infer_dataset_id(
                Path("/x/11_TCGD_MON_GLB_PROD/20251001/t00z.20251001/track_1_0.txt")
            ),
            "ds11",
        )


class DiscoveryTests(unittest.TestCase):
    def test_discover_files_finds_supported_layouts_and_skips_metadata(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._touch(root / "1_NAFP_ART_ATM_GLB_MONTH_PROD/202501/a.grib2")
            self._touch(root / "1_NAFP_ART_ATM_GLB_MONTH_PROD/202501/._a.grib2")
            self._touch(root / "2_NAFP_ART_SFC_GLB_DAY_PROD/20250101/b.grib2")
            self._touch(root / "3_NAFP_ART_SFC_GLB_MONTH_PROD/202501/c.grib2")
            self._touch(root / "4_OCEA_FUS_DAY_PRO/20250101/d.nc")
            self._touch(root / "10_SATE_PRECIPITATION_PRODUCT_2025/202501/e.h5")
            self._touch(
                root
                / "11_TCGD_MON_GLB_PROD/20251001/t00z.20251001/track_1_0.txt"
            )
            self._touch(
                root
                / "11_TCGD_MON_GLB_PROD/20251001/t00z.20251001/._track_2_0.txt"
            )

            records = discover_files(root)

        datasets = [record["dataset"] for record in records]
        paths = [record["path"].name for record in records]
        self.assertEqual(datasets, ["ds1", "ds2", "ds3", "ds4", "ds10", "ds11"])
        self.assertNotIn("._a.grib2", paths)
        self.assertNotIn("._track_2_0.txt", paths)

    def test_discover_files_filters_datasets_and_periods(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._touch(root / "10_SATE_PRECIPITATION_PRODUCT_2025/202501/jan.h5")
            self._touch(root / "10_SATE_PRECIPITATION_PRODUCT_2025/202502/feb.h5")
            self._touch(root / "2_NAFP_ART_SFC_GLB_DAY_PROD/20250101/day.grib2")

            records = discover_files(root, datasets={"ds10"}, start="202502", end="202502")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["dataset"], "ds10")
        self.assertEqual(records[0]["period"], "202502")
        self.assertEqual(records[0]["path"].name, "feb.h5")

    def _touch(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sample", encoding="utf-8")


class FakeDataset:
    def __init__(self, coords):
        self.coords = coords
        self.selector = None

    def sel(self, selector):
        self.selector = selector
        return self


class GridClippingTests(unittest.TestCase):
    def test_detect_lat_lon_names_accepts_common_coordinate_names(self):
        ds = FakeDataset({"latitude": [32, 16], "longitude": [34, 56]})

        self.assertEqual(detect_lat_lon_names(ds), ("latitude", "longitude"))

    def test_clip_xarray_to_bbox_uses_descending_latitude_slice(self):
        ds = FakeDataset({"latitude": [90.0, 32.0, 16.0, -90.0], "longitude": [0.0, 34.0, 56.0]})

        result = clip_xarray_to_bbox(ds)

        self.assertIs(result, ds)
        self.assertEqual(ds.selector["latitude"], slice(32.0, 16.0))
        self.assertEqual(ds.selector["longitude"], slice(34.0, 56.0))

    def test_clip_xarray_to_bbox_uses_ascending_latitude_slice(self):
        ds = FakeDataset({"lat": [-90.0, 16.0, 32.0, 90.0], "lon": [0.0, 34.0, 56.0]})

        result = clip_xarray_to_bbox(ds)

        self.assertIs(result, ds)
        self.assertEqual(ds.selector["lat"], slice(16.0, 32.0))
        self.assertEqual(ds.selector["lon"], slice(34.0, 56.0))


class Hdf5ExtractionTests(unittest.TestCase):
    def test_find_hdf5_lat_lon_datasets_finds_common_names(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.h5"
            with h5py.File(path, "w") as h5:
                h5.create_dataset("Latitude", data=np.array([10.0, 20.0]))
                h5.create_dataset("Longitude", data=np.array([30.0, 40.0]))

            with h5py.File(path, "r") as h5:
                lat_name, lon_name = find_hdf5_lat_lon_datasets(h5)

        self.assertEqual(lat_name, "Latitude")
        self.assertEqual(lon_name, "Longitude")

    def test_extract_hdf5_grid_file_writes_saudi_subset_npz(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.h5"
            output = Path(tmp) / "saudi_ds10_sample.npz"
            with h5py.File(source, "w") as h5:
                h5.create_dataset("lat", data=np.array([10.0, 20.0, 24.0, 40.0]))
                h5.create_dataset("lon", data=np.array([20.0, 35.0, 45.0, 70.0]))
                h5.create_dataset("precip", data=np.arange(16).reshape(4, 4))

            result = extract_hdf5_grid_file(source, output)
            data = np.load(output)

        self.assertEqual(result, output)
        np.testing.assert_array_equal(data["lat"], np.array([20.0, 24.0]))
        np.testing.assert_array_equal(data["lon"], np.array([35.0, 45.0]))
        np.testing.assert_array_equal(data["precip"], np.array([[5, 6], [9, 10]]))

    def test_extract_hdf5_grid_file_handles_fymerg_lon_lat_layout(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "fymerg.h5"
            output = Path(tmp) / "saudi_ds10_fymerg.npz"
            with h5py.File(source, "w") as h5:
                h5.create_dataset("lat", data=np.array([[10.0, 20.0, 24.0, 40.0]]))
                h5.create_dataset("lon", data=np.array([[20.0, 35.0, 45.0, 70.0]]))
                h5.create_dataset("Pre_cal", data=np.arange(16).reshape(1, 4, 4))

            result = extract_hdf5_grid_file(source, output)
            data = np.load(output)

        self.assertEqual(result, output)
        np.testing.assert_array_equal(data["lat"], np.array([20.0, 24.0]))
        np.testing.assert_array_equal(data["lon"], np.array([35.0, 45.0]))
        np.testing.assert_array_equal(data["Pre_cal"], np.array([[[5, 6], [9, 10]]]))


class TrackExtractionTests(unittest.TestCase):
    def test_track_intersects_bbox_detects_saudi_point(self):
        rows = [
            {"Lat": "45.1", "Lon": "100.2"},
            {"Lat": "24.5", "Lon": "45.8"},
        ]

        self.assertTrue(track_intersects_bbox(rows))

    def test_extract_track_file_writes_only_saudi_rows(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "track_1_0.txt"
            output = Path(tmp) / "track_1_0_saudi.csv"
            source.write_text(
                "Ini\tFcst\tLat\tLon\tVmax\tPmin\n"
                "2025100100\t60\t45.1\t100.2\t10.5\t1011.9\n"
                "2025100100\t63\t24.5\t45.8\t11.0\t1013.3\n",
                encoding="utf-8",
            )

            result = extract_track_file(source, output)
            lines = output.read_text(encoding="utf-8").splitlines()

        self.assertEqual(result, output)
        self.assertEqual(lines[0], "Ini,Fcst,Lat,Lon,Vmax,Pmin,source_file")
        self.assertEqual(lines[1], f"2025100100,63,24.5,45.8,11.0,1013.3,{source}")
        self.assertEqual(len(lines), 2)

    def test_extract_track_file_skips_when_no_saudi_rows(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "track_2_0.txt"
            output = Path(tmp) / "track_2_0_saudi.csv"
            source.write_text(
                "Ini\tFcst\tLat\tLon\tVmax\tPmin\n"
                "2025100100\t60\t45.1\t100.2\t10.5\t1011.9\n",
                encoding="utf-8",
            )

            result = extract_track_file(source, output)

        self.assertIsNone(result)
        self.assertFalse(output.exists())


class CliTests(unittest.TestCase):
    def test_discover_cli_dry_run_lists_files_without_outputs(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            source = root / "10_SATE_PRECIPITATION_PRODUCT_2025/202501/sample.h5"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("sample", encoding="utf-8")
            output_dir = Path(tmp) / "out"

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "saudi_data_extract.py"),
                    "discover",
                    str(root),
                    "--datasets",
                    "ds10",
                    "--limit",
                    "1",
                    "--dry-run",
                    "--output",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sample.h5", result.stdout)
        self.assertFalse(output_dir.exists())

    def test_batch_cli_extracts_ds11_and_writes_manifest(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            source = (
                root
                / "11_TCGD_MON_GLB_PROD/20251001/t00z.20251001/track_1_0.txt"
            )
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(
                "Ini\tFcst\tLat\tLon\tVmax\tPmin\n"
                "2025100100\t63\t24.5\t45.8\t11.0\t1013.3\n",
                encoding="utf-8",
            )
            output_dir = Path(tmp) / "out"

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "saudi_data_extract.py"),
                    "batch",
                    str(root),
                    "--datasets",
                    "ds11",
                    "--start",
                    "20251001",
                    "--end",
                    "20251001",
                    "--output",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            extracted = output_dir / "ds11/20251001/saudi_ds11_track_1_0.csv"
            manifest = output_dir / "manifest.jsonl"

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(extracted.exists())
            self.assertIn("24.5,45.8", extracted.read_text(encoding="utf-8"))
            self.assertTrue(manifest.exists())
            self.assertIn('"status": "extracted"', manifest.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
